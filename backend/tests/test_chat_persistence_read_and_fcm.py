import asyncio
import json
import uuid
from unittest.mock import AsyncMock, patch
import httpx
from httpx import ASGITransport
import pytest
from sqlalchemy import select
from starlette.websockets import WebSocketDisconnect

from backend.app.api.deps import get_current_user
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.ws_manager import connection_manager
from backend.app.core.ws_ticket_store import ws_ticket_store
from backend.app.main import app
from backend.app.models.domain.admin_telemetry import DeviceFcmToken
from backend.app.models.domain.match_and_chat import Match, Message
from backend.app.models.domain.user import User
from backend.app.services.fcm_service import fcm_service

class AsyncWsClient:
    """Native ASGI async WebSocket client running in the test event loop."""

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
    """Flushes tickets and in-memory connection registry before and after tests."""
    ws_ticket_store._tickets.clear()
    connection_manager._active_connections.clear()
    yield
    ws_ticket_store._tickets.clear()
    connection_manager._active_connections.clear()

@pytest.mark.asyncio
async def test_active_ws_skips_fcm_push(db_session, make_user):
    """Test 1: Active WebSocket connection skips FCM push dispatch (recipient is online)."""
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

    ticket_a = await ws_ticket_store.create_ticket(user_a.id)
    ticket_b = await ws_ticket_store.create_ticket(user_b.id)
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        with patch.object(fcm_service, "send_multicast_push", new_callable=AsyncMock) as mock_push:
            async with AsyncWsClient(app, f"/ws/chat?ticket={ticket_a}") as ws_a, \
                       AsyncWsClient(app, f"/ws/chat?ticket={ticket_b}") as ws_b:

                # User A sends a message to User B
                await ws_a.send_json({
                    "type": "message",
                    "match_id": str(match.id),
                    "recipient_id": str(user_b.id),
                    "encrypted_text": "ciphertext:online_stream",
                    "client_id": "client_msg_online_1",
                })

                # Peer receives frame
                b_frame = await ws_b.receive_json()
                assert b_frame["type"] == "message"
                assert b_frame["encrypted_text"] == "ciphertext:online_stream"

                # Sender receives delivered ack
                a_ack = await ws_a.receive_json()
                assert a_ack["type"] == "ack"
                assert a_ack["status"] == "delivered"

                # FCM push was NOT dispatched because recipient is online
                assert mock_push.call_count == 0
    finally:
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_offline_recipient_triggers_fcm_push_with_dpdp_privacy_copy(db_session, make_user):
    """Test 2: Offline recipient triggers FCM dispatch with privacy-preserving body copy (no PII or decrypted text leaked)."""
    user_a = make_user(full_name="Sender Alpha", is_profile_completed=True)
    user_b = make_user(full_name="Receiver Beta", is_profile_completed=True, push_notifications_enabled=True)
    db_session.add_all([user_a, user_b])
    await db_session.commit()

    # Add active token for offline user B
    token_b = DeviceFcmToken(
        user_id=user_b.id,
        token="device_fcm_token_receiver_beta_123",
        platform="android",
        is_active=True,
    )
    db_session.add(token_b)

    u1_id, u2_id = sorted([user_a.id, user_b.id])
    match = Match(
        id=uuid.uuid4(),
        user1_id=u1_id,
        user2_id=u2_id,
        is_active=True,
    )
    db_session.add(match)
    await db_session.commit()

    ticket_a = await ws_ticket_store.create_ticket(user_a.id)
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        with patch.object(fcm_service, "send_multicast_push", new_callable=AsyncMock) as mock_push:
            async with AsyncWsClient(app, f"/ws/chat?ticket={ticket_a}") as ws_a:
                # User A sends message while User B is offline
                await ws_a.send_json({
                    "type": "message",
                    "match_id": str(match.id),
                    "recipient_id": str(user_b.id),
                    "encrypted_text": "secret_confidential_confession_content",
                    "client_id": "client_msg_offline_1",
                })

                # Sender receives ack with status 'sent'
                ack = await ws_a.receive_json()
                assert ack["type"] == "ack"
                assert ack["status"] == "sent"

                # Await background tasks deterministically
                from backend.app.api.v1.endpoints import chat_ws as chat_ws_mod
                if chat_ws_mod._background_tasks:
                    await asyncio.wait_for(
                        asyncio.gather(*list(chat_ws_mod._background_tasks)),
                        timeout=2.0,
                    )

                assert mock_push.call_count == 1
                call_kwargs = mock_push.call_args.kwargs
                assert call_kwargs["user_id"] == user_b.id
                assert call_kwargs["channel_id"] == "channel_kinship_dialogue"
                assert call_kwargs["title"] == "UR-Heart Sanctuary"

                # DPDP Act Privacy Invariant: raw unencrypted text is NEVER leaked
                assert "secret_confidential_confession_content" not in call_kwargs["body"]
                assert call_kwargs["body"] == "A thoughtful reflection has arrived in your dialogue."
                assert call_kwargs["data_payload"]["match_id"] == str(match.id)
                assert call_kwargs["data_payload"]["type"] == "chat_message"
    finally:
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_fcm_unregistered_deactivates_token(db_session, make_user):
    """Test 3: If FCM returns UNREGISTERED, the token is deactivated in public.device_fcm_tokens."""
    user = make_user(full_name="Seeker Stale", is_profile_completed=True)
    db_session.add(user)
    await db_session.commit()

    token_record = DeviceFcmToken(
        user_id=user.id,
        token="stale_dead_token_404",
        platform="android",
        is_active=True,
    )
    db_session.add(token_record)
    await db_session.commit()

    # Mock HTTP 404 UNREGISTERED response from FCM
    mock_response = httpx.Response(
        status_code=404,
        json={"error": {"code": 404, "message": "Requested entity was not found.", "status": "UNREGISTERED"}},
    )

    with patch.object(settings, "FIREBASE_PROJECT_ID", "test-sanctuary-project"), \
         patch.object(fcm_service, "_get_access_token", new_callable=AsyncMock, return_value="mock_access_token_123"), \
         patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
        deliveries = await fcm_service.send_multicast_push(
            user_id=user.id,
            title="Sanctuary Test",
            body="Reflection",
            data_payload={"match_id": "123"},
            channel_id="channel_kinship_dialogue",
            session=db_session,
        )
        assert deliveries == 0

    # Token must now be deactivated (is_active == False)
    res = await db_session.execute(
        select(DeviceFcmToken.is_active).where(DeviceFcmToken.token == "stale_dead_token_404")
    )
    is_active = res.scalar_one()
    assert is_active is False

@pytest.mark.asyncio
async def test_fcm_generic_invalid_argument_preserves_token(db_session, make_user):
    """Test 3b: Generic INVALID_ARGUMENT (malformed payload) preserves active token; only explicit token error deactivates."""
    user = make_user(full_name="Valid Seeker", is_profile_completed=True)
    db_session.add(user)
    await db_session.commit()

    token_record = DeviceFcmToken(
        user_id=user.id,
        token="valid_active_token_555",
        platform="android",
        is_active=True,
    )
    db_session.add(token_record)
    await db_session.commit()

    # Generic bad payload field error from FCM
    mock_response = httpx.Response(
        status_code=400,
        json={"error": {"code": 400, "message": "Invalid field in notification.", "status": "INVALID_ARGUMENT"}},
    )

    with patch.object(settings, "FIREBASE_PROJECT_ID", "test-sanctuary-project"), \
         patch.object(fcm_service, "_get_access_token", new_callable=AsyncMock, return_value="mock_access_token_123"), \
         patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
        deliveries = await fcm_service.send_multicast_push(
            user_id=user.id,
            title="Sanctuary Test",
            body="Reflection",
            data_payload={"match_id": "123"},
            session=db_session,
        )
        assert deliveries == 0

    # Token must NOT be deactivated by generic INVALID_ARGUMENT
    res = await db_session.execute(
        select(DeviceFcmToken.is_active).where(DeviceFcmToken.token == "valid_active_token_555")
    )
    assert res.scalar_one() is True

@pytest.mark.asyncio
async def test_fcm_missing_credentials_or_project_returns_zero_early(db_session, make_user):
    """Test 3c: Missing FIREBASE_PROJECT_ID or access token returns 0 immediately without calling HTTP."""
    user = make_user(full_name="Unconfigured Seeker", is_profile_completed=True)
    db_session.add(user)
    await db_session.commit()

    token_record = DeviceFcmToken(
        user_id=user.id,
        token="unconfigured_token_777",
        platform="android",
        is_active=True,
    )
    db_session.add(token_record)
    await db_session.commit()

    with patch.object(settings, "FIREBASE_PROJECT_ID", ""), \
         patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_http:
        deliveries = await fcm_service.send_multicast_push(
            user_id=user.id,
            title="Sanctuary Test",
            body="Reflection",
            data_payload={},
            session=db_session,
        )
        assert deliveries == 0
        assert mock_http.call_count == 0

@pytest.mark.asyncio
async def test_notifications_device_token_lifecycle_api(db_session, make_user):
    """Test 4: Registering and unregistering device tokens via /notifications/device-token updates database state correctly."""
    user = make_user(full_name="Token Seeker", is_profile_completed=True)
    db_session.add(user)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Register device token
            reg_res = await client.post(
                "/api/v1/notifications/device-token",
                json={
                    "token": "fresh_fcm_device_token_999",
                    "platform": "android",
                    "installation_id": "hardware_inst_uuid_123",
                },
            )
            assert reg_res.status_code == 200
            assert reg_res.json()["data"]["registered"] is True

            # Verify database state
            token_res = await db_session.execute(
                select(DeviceFcmToken).where(DeviceFcmToken.token == "fresh_fcm_device_token_999")
            )
            token_row = token_res.scalar_one_or_none()
            assert token_row is not None
            assert token_row.user_id == user.id
            assert token_row.platform == "android"
            assert token_row.is_active is True
            assert user.fcm_token == "fresh_fcm_device_token_999"
            assert user.last_installation_uuid == "hardware_inst_uuid_123"

            # 2. Unregister device token
            unreg_res = await client.request(
                "DELETE",
                "/api/v1/notifications/device-token",
                json={"token": "fresh_fcm_device_token_999"},
            )
            assert unreg_res.status_code == 200
            assert unreg_res.json()["data"]["unregistered"] is True

            # Verify token deactivated
            await db_session.refresh(token_row)
            assert token_row.is_active is False
            assert user.fcm_token is None
    finally:
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_toggling_push_preferences_halts_dispatches(db_session, make_user):
    """Test 5: Toggling push preferences off halts all push dispatches for that user."""
    user = make_user(full_name="Quiet Seeker", is_profile_completed=True, push_notifications_enabled=True)
    db_session.add(user)
    await db_session.commit()

    token = DeviceFcmToken(
        user_id=user.id,
        token="quiet_user_fcm_token_777",
        platform="android",
        is_active=True,
    )
    db_session.add(token)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Disable push notifications
            pref_res = await client.put(
                "/api/v1/notifications/preferences",
                json={"push_enabled": False},
            )
            assert pref_res.status_code == 200
            assert pref_res.json()["data"]["push_notifications_enabled"] is False

            # Refresh user in session
            await db_session.refresh(user)
            assert user.push_notifications_enabled is False

            # 2. Attempt push dispatch while disabled
            with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_http:
                deliveries = await fcm_service.send_multicast_push(
                    user_id=user.id,
                    title="Reflection",
                    body="New reflection",
                    data_payload={},
                    session=db_session,
                )
                assert deliveries == 0
                assert mock_http.call_count == 0
    finally:
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_token_reassignment_clears_previous_user_fcm_token(db_session, make_user):
    """Test 6: When a device token is registered to a new user, the previous owner's fcm_token is cleared."""
    user1 = make_user(full_name="User Alpha", is_profile_completed=True)
    user2 = make_user(full_name="User Beta", is_profile_completed=True)
    db_session.add_all([user1, user2])
    await db_session.commit()

    shared_device_token = "fcm_token_shared_device_999"

    # User 1 registers device token
    app.dependency_overrides[get_current_user] = lambda: user1
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            res1 = await client.post(
                "/api/v1/notifications/device-token",
                json={"token": shared_device_token, "platform": "android"},
            )
            assert res1.status_code == 200
            await db_session.refresh(user1)
            assert user1.fcm_token == shared_device_token

        # User 2 now registers the SAME device token on the same physical phone
        app.dependency_overrides[get_current_user] = lambda: user2
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            res2 = await client.post(
                "/api/v1/notifications/device-token",
                json={"token": shared_device_token, "platform": "android"},
            )
            assert res2.status_code == 200
            await db_session.refresh(user1)
            await db_session.refresh(user2)

            # Previous user's fcm_token must be cleared to prevent cross-account push leakage
            assert user1.fcm_token is None
            # Current user now owns the token
            assert user2.fcm_token == shared_device_token

            # DeviceFcmToken row updated to User 2
            row = (await db_session.execute(
                select(DeviceFcmToken).where(DeviceFcmToken.token == shared_device_token)
            )).scalar_one()
            assert row.user_id == user2.id
            assert row.is_active is True
    finally:
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_fcm_project_not_found_404_does_not_deactivate_token(db_session, make_user):
    """Test 7: Generic 404 (e.g., misconfigured FIREBASE_PROJECT_ID) does not deactivate user tokens."""
    user = make_user(full_name="Survivor Token Seeker", is_profile_completed=True)
    db_session.add(user)
    await db_session.commit()

    token_record = DeviceFcmToken(
        user_id=user.id,
        token="valid_token_wrong_project_404",
        platform="android",
        is_active=True,
    )
    db_session.add(token_record)
    await db_session.commit()

    # FCM returns HTTP 404 with status NOT_FOUND and NO UNREGISTERED errorCode
    mock_response = httpx.Response(
        status_code=404,
        json={"error": {"code": 404, "message": "Project test-invalid-project not found.", "status": "NOT_FOUND"}},
    )

    with patch.object(settings, "FIREBASE_PROJECT_ID", "test-invalid-project"), \
         patch.object(fcm_service, "_get_access_token", new_callable=AsyncMock, return_value="mock_access_token_123"), \
         patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
        deliveries = await fcm_service.send_multicast_push(
            user_id=user.id,
            title="Sanctuary Test",
            body="Reflection",
            data_payload={"match_id": "123"},
            channel_id="channel_kinship_dialogue",
            session=db_session,
        )
        assert deliveries == 0

    # Token must remain active! Not wiped by generic 404!
    res = await db_session.execute(
        select(DeviceFcmToken.is_active).where(DeviceFcmToken.token == "valid_token_wrong_project_404")
    )
    assert res.scalar_one() is True

@pytest.mark.asyncio
async def test_chat_ws_background_task_exception_handled(db_session, make_user):
    """Test 8: Background task exception is logged cleanly without unhandled errors."""
    user_a = make_user(full_name="Sender Seeker", is_profile_completed=True)
    user_b = make_user(full_name="Offline Seeker", is_profile_completed=True)
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

    ticket_a = await ws_ticket_store.create_ticket(user_a.id)
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        with patch.object(fcm_service, "send_multicast_push", side_effect=RuntimeError("FCM network boom")):
            async with AsyncWsClient(app, f"/ws/chat?ticket={ticket_a}") as ws_a:
                await ws_a.send_json({
                    "type": "message",
                    "match_id": str(match.id),
                    "recipient_id": str(user_b.id),
                    "encrypted_text": "hello_world_text",
                    "client_id": "client_err_1",
                })
                ack = await ws_a.receive_json()
                assert ack["type"] == "ack"

                from backend.app.api.v1.endpoints import chat_ws as chat_ws_mod
                if chat_ws_mod._background_tasks:
                    await asyncio.wait_for(
                        asyncio.gather(*list(chat_ws_mod._background_tasks), return_exceptions=True),
                        timeout=2.0,
                    )
                await asyncio.sleep(0)
                # Task completed and removed from strong reference set
                assert len(chat_ws_mod._background_tasks) == 0
    finally:
        app.dependency_overrides.clear()
