import asyncio
import json
import uuid
import pytest
import httpx
from httpx import ASGITransport
from starlette.websockets import WebSocketDisconnect
from sqlalchemy import select

from backend.app.api.deps import get_current_user
from backend.app.core.database import get_db
from backend.app.core.ws_ticket_store import ws_ticket_store
from backend.app.core.ws_manager import connection_manager
from backend.app.main import app
from backend.app.models.domain.match_and_chat import Match, Message

class AsyncWsClient:
    """Native ASGI async WebSocket client running in the same event loop as the test suite.
    
    Prevents cross-thread deadlocks between TestClient worker threads and async database sessions.
    """

    def __init__(self, asgi_app, path: str):
        self.app = asgi_app
        self.path = path
        self.in_q: asyncio.Queue = asyncio.Queue()
        self.out_q: asyncio.Queue = asyncio.Queue()
        self.task: asyncio.Task = None

    async def __aenter__(self):
        url_parts = self.path.split("?", 1)
        path = url_parts[0]
        query_string = url_parts[1].encode() if len(url_parts) > 1 else b""

        scope = {
            "type": "websocket",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "scheme": "ws",
            "path": path,
            "raw_path": path.encode(),
            "query_string": query_string,
            "headers": [],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
            "subprotocols": [],
            "state": {},
            "app": self.app,
        }

        async def receive():
            return await self.in_q.get()

        async def send(message):
            await self.out_q.put(message)

        self.task = asyncio.create_task(self.app(scope, receive, send))

        # Send initial connect frame
        await self.in_q.put({"type": "websocket.connect"})
        msg = await self.out_q.get()
        if msg["type"] == "websocket.close":
            raise WebSocketDisconnect(code=msg.get("code", 1000), reason=msg.get("reason", ""))
        assert msg["type"] == "websocket.accept"
        return self

    async def __aexit__(self, *args):
        try:
            await self.in_q.put({"type": "websocket.disconnect", "code": 1000})
            if self.task and not self.task.done():
                await asyncio.wait_for(self.task, timeout=1.0)
        except Exception:
            pass

    async def send_json(self, data: dict):
        await self.in_q.put({"type": "websocket.receive", "text": json.dumps(data)})

    async def receive_json(self) -> dict:
        msg = await self.out_q.get()
        if msg["type"] == "websocket.close":
            raise WebSocketDisconnect(code=msg.get("code", 1000), reason=msg.get("reason", ""))
        return json.loads(msg["text"])

@pytest.fixture(autouse=True)
def clean_ws_state():
    """Flushes tickets and in-memory connection registry before and after every test."""
    ws_ticket_store._tickets.clear()
    connection_manager._active_connections.clear()
    yield
    ws_ticket_store._tickets.clear()
    connection_manager._active_connections.clear()

@pytest.mark.asyncio
async def test_ws_ticket_generation(db_session, make_user):
    """Test 1: POST /api/v1/chat/ws-ticket generates a valid 60s single-use ticket."""
    user = make_user(full_name="Seeker Alpha", is_profile_completed=True)
    db_session.add(user)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post("/api/v1/chat/ws-ticket")
            assert res.status_code == 200
            data = res.json()["data"]

            assert "ticket" in data
            assert len(data["ticket"]) >= 32
            assert data["expires_in"] == 60
            assert "ws/chat" in data["ws_url"]
    finally:
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_ws_ticket_replay_prevention(db_session, make_user):
    """Test 2: Ephemeral ticket is single-use; subsequent connection fails with close code 4401."""
    user = make_user(full_name="Seeker Bravo", is_profile_completed=True)
    db_session.add(user)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post("/api/v1/chat/ws-ticket")
            assert res.status_code == 200
            ticket = res.json()["data"]["ticket"]

        # 1. First connection succeeds and consumes ticket
        async with AsyncWsClient(app, f"/ws/chat?ticket={ticket}") as ws:
            await ws.send_json({"type": "heartbeat"})
            pong = await ws.receive_json()
            assert pong["type"] == "pong"

        # 2. Second connection with same ticket must be rejected with 4401
        with pytest.raises(WebSocketDisconnect) as exc:
            async with AsyncWsClient(app, f"/ws/chat?ticket={ticket}"):
                pass
        assert exc.value.code == 4401
    finally:
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_ws_ticket_expiration(db_session, make_user):
    """Test 3: Connecting with an expired ticket closes connection with code 4401."""
    user = make_user(full_name="Seeker Charlie", is_profile_completed=True)
    db_session.add(user)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        # Create ticket with TTL = -1 (immediately expired)
        ticket = await ws_ticket_store.create_ticket(user.id, ttl_seconds=-1)

        with pytest.raises(WebSocketDisconnect) as exc:
            async with AsyncWsClient(app, f"/ws/chat?ticket={ticket}"):
                pass
        assert exc.value.code == 4401
    finally:
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_ws_heartbeat_ping_pong(db_session, make_user):
    """Test 4: Client heartbeat frame returns immediate pong with timestamp."""
    user = make_user(full_name="Seeker Delta", is_profile_completed=True)
    db_session.add(user)
    await db_session.commit()

    ticket = await ws_ticket_store.create_ticket(user.id, ttl_seconds=60)
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        async with AsyncWsClient(app, f"/ws/chat?ticket={ticket}") as ws:
            await ws.send_json({"type": "heartbeat"})
            frame = await ws.receive_json()
            assert frame["type"] == "pong"
            assert "timestamp" in frame
    finally:
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_ws_message_realtime_relay_and_ack(db_session, make_user):
    """Test 5: Two active seekers connected via WebSocket exchange message frame with delivery ack."""
    user_a = make_user(full_name="User Alpha", is_profile_completed=True)
    user_b = make_user(full_name="User Beta", is_profile_completed=True)
    db_session.add_all([user_a, user_b])
    await db_session.commit()

    # Create ordered match pair (user1_id < user2_id)
    u1_id, u2_id = sorted([user_a.id, user_b.id])
    match = Match(
        id=uuid.uuid4(),
        user1_id=u1_id,
        user2_id=u2_id,
        is_active=True,
    )
    db_session.add(match)
    await db_session.commit()

    ticket_a = await ws_ticket_store.create_ticket(user_a.id, ttl_seconds=60)
    ticket_b = await ws_ticket_store.create_ticket(user_b.id, ttl_seconds=60)

    app.dependency_overrides[get_db] = lambda: db_session

    try:
        async with AsyncWsClient(app, f"/ws/chat?ticket={ticket_a}") as ws_a:
            async with AsyncWsClient(app, f"/ws/chat?ticket={ticket_b}") as ws_b:
                # User A sends message to User B
                client_msg_id = "client-uuid-101"
                await ws_a.send_json({
                    "type": "message",
                    "match_id": str(match.id),
                    "recipient_id": str(user_b.id),
                    "encrypted_text": "SanctuaryCiphertextPayload#99",
                    "client_id": client_msg_id,
                })

                # User B receives direct message frame
                incoming = await ws_b.receive_json()
                assert incoming["type"] == "message"
                assert incoming["match_id"] == str(match.id)
                assert incoming["sender_id"] == str(user_a.id)
                assert incoming["encrypted_text"] == "SanctuaryCiphertextPayload#99"
                assert incoming["client_id"] == client_msg_id

                # User A receives delivery ack
                ack = await ws_a.receive_json()
                assert ack["type"] == "ack"
                assert ack["client_id"] == client_msg_id
                assert ack["status"] == "delivered"

        # Verify message persisted in database with delivered status
        msg_stmt = select(Message).where(Message.match_id == match.id)
        res = await db_session.execute(msg_stmt)
        saved_msg = res.scalar_one_or_none()
        assert saved_msg is not None
        assert saved_msg.sender_id == user_a.id
        assert saved_msg.encrypted_text == "SanctuaryCiphertextPayload#99"
        assert saved_msg.status == "delivered"
    finally:
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_ws_authorization_non_participant_rejection(db_session, make_user):
    """Test 6: Outsider attempting to send message into a match they do not belong to is rejected."""
    user_a = make_user(full_name="User Alpha", is_profile_completed=True)
    user_b = make_user(full_name="User Beta", is_profile_completed=True)
    outsider = make_user(full_name="User Outsider", is_profile_completed=True)
    db_session.add_all([user_a, user_b, outsider])
    await db_session.commit()

    u1_id, u2_id = sorted([user_a.id, user_b.id])
    match = Match(
        id=uuid.uuid4(),
        user1_id=u1_id,
        user2_id=u2_id,
        is_active=True,
    )
    db_session.add(match)
    await db_session.commit()

    ticket_outsider = await ws_ticket_store.create_ticket(outsider.id, ttl_seconds=60)
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        async with AsyncWsClient(app, f"/ws/chat?ticket={ticket_outsider}") as ws_out:
            await ws_out.send_json({
                "type": "message",
                "match_id": str(match.id),
                "recipient_id": str(user_b.id),
                "encrypted_text": "IntrusionAttempt",
                "client_id": "c-intrude",
            })
            err_frame = await ws_out.receive_json()
            assert err_frame["type"] == "error"
            assert err_frame["error_code"] == "MATCH_NOT_FOUND_OR_INACTIVE"

        # Verify no message persisted
        msg_stmt = select(Message).where(Message.match_id == match.id)
        res = await db_session.execute(msg_stmt)
        assert res.scalar_one_or_none() is None
    finally:
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_ws_read_receipt_and_typing_relay(db_session, make_user):
    """Test 7: Typing indicator and read receipt frames are relayed directly between active peers."""
    user_a = make_user(full_name="User Alpha", is_profile_completed=True)
    user_b = make_user(full_name="User Beta", is_profile_completed=True)
    db_session.add_all([user_a, user_b])
    await db_session.commit()

    u1_id, u2_id = sorted([user_a.id, user_b.id])
    match = Match(
        id=uuid.uuid4(),
        user1_id=u1_id,
        user2_id=u2_id,
        is_active=True,
    )
    db_session.add(match)
    await db_session.commit()

    # Pre-populate an unread message from User A to User B
    msg = Message(
        match_id=match.id,
        sender_id=user_a.id,
        encrypted_text="Hello friend",
        status="delivered",
    )
    db_session.add(msg)
    await db_session.commit()

    ticket_a = await ws_ticket_store.create_ticket(user_a.id, ttl_seconds=60)
    ticket_b = await ws_ticket_store.create_ticket(user_b.id, ttl_seconds=60)

    app.dependency_overrides[get_db] = lambda: db_session

    try:
        async with AsyncWsClient(app, f"/ws/chat?ticket={ticket_a}") as ws_a:
            async with AsyncWsClient(app, f"/ws/chat?ticket={ticket_b}") as ws_b:
                # 1. User B sends typing indicator to User A
                await ws_b.send_json({
                    "type": "typing",
                    "match_id": str(match.id),
                    "recipient_id": str(user_a.id),
                    "is_typing": True,
                })
                typing_frame = await ws_a.receive_json()
                assert typing_frame["type"] == "typing"
                assert typing_frame["sender_id"] == str(user_b.id)
                assert typing_frame["is_typing"] is True

                # 2. User B marks messages as read
                await ws_b.send_json({
                    "type": "read_receipt",
                    "match_id": str(match.id),
                    "recipient_id": str(user_a.id),
                })

                # User A receives read receipt
                read_frame = await ws_a.receive_json()
                assert read_frame["type"] == "read_receipt"
                assert read_frame["reader_id"] == str(user_b.id)

        # Verify message status in DB is now 'read'
        await db_session.refresh(msg)
        assert msg.status == "read"
    finally:
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_ws_non_dict_frame_handling(db_session, make_user):
    """Test 8: Non-object JSON frames (lists, numbers) return INVALID_FRAME error without crashing connection."""
    user = make_user(full_name="User NonDict", is_profile_completed=True)
    db_session.add(user)
    await db_session.commit()

    ticket = await ws_ticket_store.create_ticket(user.id, ttl_seconds=60)
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        async with AsyncWsClient(app, f"/ws/chat?ticket={ticket}") as ws:
            # Send a JSON list instead of an object
            await ws.send_json(["item1", "item2"])
            err = await ws.receive_json()
            assert err["type"] == "error"
            assert err["error_code"] == "INVALID_FRAME"
            assert "must be a JSON object" in err["message"]

            # Connection remains alive: subsequent valid heartbeat succeeds
            await ws.send_json({"type": "heartbeat"})
            pong = await ws.receive_json()
            assert pong["type"] == "pong"
    finally:
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_ws_typing_and_read_receipt_authorization(db_session, make_user):
    """Test 9: Typing and read receipt frames verify active match and reject unmatched seekers."""
    user_a = make_user(full_name="User A", is_profile_completed=True)
    user_b = make_user(full_name="User B", is_profile_completed=True)
    outsider = make_user(full_name="User C", is_profile_completed=True)
    db_session.add_all([user_a, user_b, outsider])
    await db_session.commit()

    fake_match_id = uuid.uuid4()
    ticket_outsider = await ws_ticket_store.create_ticket(outsider.id, ttl_seconds=60)
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        async with AsyncWsClient(app, f"/ws/chat?ticket={ticket_outsider}") as ws_out:
            # Typing to non-matched user
            await ws_out.send_json({
                "type": "typing",
                "match_id": str(fake_match_id),
                "recipient_id": str(user_a.id),
                "is_typing": True,
            })
            err_typing = await ws_out.receive_json()
            assert err_typing["type"] == "error"
            assert err_typing["error_code"] == "MATCH_NOT_FOUND_OR_INACTIVE"

            # Read receipt to non-matched user
            await ws_out.send_json({
                "type": "read_receipt",
                "match_id": str(fake_match_id),
                "recipient_id": str(user_a.id),
            })
            err_read = await ws_out.receive_json()
            assert err_read["type"] == "error"
            assert err_read["error_code"] == "MATCH_NOT_FOUND_OR_INACTIVE"
    finally:
        app.dependency_overrides.clear()

