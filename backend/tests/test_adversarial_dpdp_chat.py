import asyncio
import hashlib
import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import httpx
from httpx import ASGITransport
import jwt
import pytest
from sqlalchemy import select
from starlette.websockets import WebSocketDisconnect

from backend.app.api.deps import get_current_user, get_db
from backend.app.api.v1.endpoints.chat_ws import _verify_active_match
from backend.app.core.config import settings
from backend.app.core.limiter import limiter
from backend.app.core.security import create_access_token
from backend.app.core.ws_manager import connection_manager
from backend.app.core.ws_ticket_store import ws_ticket_store
from backend.app.main import app
from backend.app.models.domain.legal import (
    ConsentAuditLog,
    DataNominee,
    GrievanceDossier,
    WebDeletionToken,
)
from backend.app.models.domain.match_and_chat import Match, Message
from backend.app.models.domain.user import User
from backend.app.services.account_incineration_service import (
    AccountIncinerationService,
    account_incineration_service,
)
from backend.app.services.storage_service import storage_service
from backend.tests.test_chat_ws_relay import AsyncWsClient


@pytest.fixture(autouse=True)
def clean_test_state():
    """Flushes tickets, active connections, and rate limiter storage before and after each test."""
    ws_ticket_store._tickets.clear()
    connection_manager._active_connections.clear()
    try:
        limiter._storage.reset()
    except Exception:
        pass
    yield
    ws_ticket_store._tickets.clear()
    connection_manager._active_connections.clear()
    try:
        limiter._storage.reset()
    except Exception:
        pass


# ============================================================================
# 1. VULN-DPDP-01: Statutory Evidence Tampering via Malicious Account Incineration
# ============================================================================

@pytest.mark.asyncio
async def test_account_incineration_preserves_reported_grievance_evidence(db_session, make_user, monkeypatch):
    """VULN-DPDP-01: Verifies that when a reported perpetrator incinerates their account,
    the victim's statutory grievance narrative (evidence_text) is strictly preserved for law enforcement.
    """
    victim = make_user(full_name="Victim Seeker")
    perpetrator = make_user(full_name="Perpetrator Seeker")
    db_session.add_all([victim, perpetrator])
    await db_session.commit()

    victim_statement = "Perpetrator distributed non-consensual private imagery on external forum."
    dossier = GrievanceDossier(
        dossier_reference_id="URH-GRV-20261017-TEST01",
        reporter_id=victim.id,
        reported_user_id=perpetrator.id,
        violation_category="ncii",
        evidence_text=victim_statement,
        statutory_notes=victim_statement,
        status="acknowledged",
    )
    db_session.add(dossier)
    await db_session.commit()

    monkeypatch.setattr(storage_service, "delete_objects_by_prefix", MagicMock(return_value=0))

    # Perpetrator executes account incineration
    result = await account_incineration_service.execute_account_incineration(perpetrator.id, db_session)
    assert result["success"] is True

    # Check GrievanceDossier in database
    stmt = select(GrievanceDossier).where(GrievanceDossier.dossier_reference_id == "URH-GRV-20261017-TEST01")
    updated_dossier = (await db_session.execute(stmt)).scalar_one()

    # Invariant: reported_user_id decoupled to satisfy FK cascade, but victim evidence_text preserved intact
    assert updated_dossier.reported_user_id is None
    assert updated_dossier.evidence_text == victim_statement
    assert updated_dossier.evidence_text != "[INCINERATED_PURSUANT_TO_DPDP_SECTION_12]"
    assert "[RESPONDENT_INCINERATED]" in (updated_dossier.statutory_notes or "")


# ============================================================================
# 2. VULN-WS-01: Banned Seeker WebSocket Connection and Frame Relay
# ============================================================================

@pytest.mark.asyncio
async def test_banned_user_ws_handshake_rejected(db_session, make_user):
    """VULN-WS-01 (Part A): Banned/soft-deleted seeker cannot complete WebSocket handshake with valid ticket."""
    user = make_user(full_name="Banned Seeker")
    db_session.add(user)
    await db_session.commit()

    # Ticket generated while active
    ticket = await ws_ticket_store.create_ticket(user.id, ttl_seconds=60)

    # Superadmin bans seeker
    user.deleted_at = datetime.now(timezone.utc)
    await db_session.commit()

    app.dependency_overrides[get_db] = lambda: db_session

    try:
        # Handshake must fail with close code 4403
        with pytest.raises(WebSocketDisconnect) as exc_info:
            async with AsyncWsClient(app, f"/ws/chat?ticket={ticket}") as client:
                await client.receive_json()
        assert exc_info.value.code == 4403
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_banned_user_mid_session_frame_rejected(db_session, make_user):
    """VULN-WS-01 (Part B): If a seeker is banned during an active WebSocket session,
    the server terminates the connection and refuses to persist or relay messages.
    """
    u1 = make_user(full_name="Seeker A")
    u2 = make_user(full_name="Seeker B")
    if u1.id > u2.id:
        u1, u2 = u2, u1
    db_session.add_all([u1, u2])
    await db_session.commit()

    match = Match(user1_id=u1.id, user2_id=u2.id, is_active=True, closure_status="active")
    db_session.add(match)
    await db_session.commit()

    ticket_a = await ws_ticket_store.create_ticket(u1.id, ttl_seconds=60)
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        async with AsyncWsClient(app, f"/ws/chat?ticket={ticket_a}") as client_a:
            # User A is connected. Superadmin bans User A mid-session.
            u1.deleted_at = datetime.now(timezone.utc)
            await db_session.commit()

            # User A attempts to send a chat message
            await client_a.send_json({
                "type": "message",
                "match_id": str(match.id),
                "recipient_id": str(u2.id),
                "encrypted_text": "cipher_post_ban_harassment",
                "client_id": "client_msg_01",
            })

            # Server must return SEEKER_BANNED error and disconnect
            resp = await client_a.receive_json()
            assert resp["type"] == "error"
            assert resp["error_code"] == "SEEKER_BANNED"

            # Verify message was NOT saved in database
            stmt = select(Message).where(Message.encrypted_text == "cipher_post_ban_harassment")
            saved = (await db_session.execute(stmt)).scalar_one_or_none()
            assert saved is None
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_active_match_verification_blocks_banned_participants(db_session, make_user):
    """VULN-WS-01 (Part C): _verify_active_match returns None if either participant is soft-deleted/banned."""
    u1 = make_user()
    u2 = make_user()
    if u1.id > u2.id:
        u1, u2 = u2, u1
    db_session.add_all([u1, u2])
    await db_session.commit()

    match = Match(user1_id=u1.id, user2_id=u2.id, is_active=True, closure_status="active")
    db_session.add(match)
    await db_session.commit()

    # Active match returns match record
    res = await _verify_active_match(db_session, match.id, u1.id, u2.id)
    assert res is not None

    # Ban participant u2
    u2.deleted_at = datetime.now(timezone.utc)
    await db_session.commit()

    # Must return None even though Match.is_active is True
    res_banned = await _verify_active_match(db_session, match.id, u1.id, u2.id)
    assert res_banned is None


# ============================================================================
# 3. VULN-DPDP-02: Step-Up Re-Authentication on Account Incineration
# ============================================================================

@pytest.mark.asyncio
async def test_account_incineration_requires_reauth_credentials(db_session, make_user, monkeypatch):
    """VULN-DPDP-02: Account incineration with a stale access token requires step-up re-authentication."""
    user = make_user()
    db_session.add(user)
    await db_session.commit()

    monkeypatch.setattr(storage_service, "delete_objects_by_prefix", MagicMock(return_value=0))
    app.dependency_overrides[get_db] = lambda: db_session

    # 1. Stale access token (issued 10 minutes ago, i.e. > 300s TTL)
    now = datetime.now(timezone.utc)
    stale_payload = {
        "sub": str(user.id),
        "iat": int((now - timedelta(minutes=10)).timestamp()),
        "exp": int((now + timedelta(minutes=50)).timestamp()),
        "type": "access",
        "token_version": 1,
    }
    stale_token = jwt.encode(stale_payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # Attempt incineration with stale token and NO re-auth header -> 403 STEP_UP_REAUTH_REQUIRED
            resp_stale = await client.request(
                "DELETE",
                "/api/v1/legal/account",
                headers={"Authorization": f"Bearer {stale_token}"},
                json={"confirmation_phrase": "PERMANENTLY INCINERATE", "reason": "Departure"},
            )
            assert resp_stale.status_code == 403
            assert resp_stale.json()["error_code"] == "STEP_UP_REAUTH_REQUIRED"

            # 2. Fresh token (< 300s old) succeeds without extra header
            fresh_token = create_access_token(user.id)
            resp_fresh = await client.request(
                "DELETE",
                "/api/v1/legal/account",
                headers={"Authorization": f"Bearer {fresh_token}"},
                json={"confirmation_phrase": "PERMANENTLY INCINERATE", "reason": "Departure"},
            )
            assert resp_fresh.status_code == 200
            assert resp_fresh.json()["data"]["status"] == "incinerated"
    finally:
        app.dependency_overrides.pop(get_db, None)


# ============================================================================
# 4. VULN-DPDP-03: Banned Account Deletion Bypass via Web Magic Link
# ============================================================================

@pytest.mark.asyncio
async def test_banned_user_cannot_trigger_web_account_deletion(db_session, make_user, monkeypatch):
    """VULN-DPDP-03: Banned seeker cannot request or confirm account incineration via public web portal."""
    banned_user = make_user(deleted_at=datetime.now(timezone.utc))
    db_session.add(banned_user)
    await db_session.commit()

    monkeypatch.setattr(storage_service, "delete_objects_by_prefix", MagicMock(return_value=0))
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Request web deletion: returns 200 (anti-enumeration) but does NOT create WebDeletionToken
            resp_req = await client.post(
                "/api/v1/legal/web-account-deletion",
                json={"email": banned_user.email, "reason": "Banned user evasion"},
            )
            assert resp_req.status_code == 200
            stmt = select(WebDeletionToken).where(WebDeletionToken.user_id == banned_user.id)
            tokens = (await db_session.execute(stmt)).scalars().all()
            assert len(tokens) == 0

            # 2. If a token previously existed, confirm endpoint refuses incineration with 403
            raw_token = "pre_ban_magic_token_123"
            token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
            old_token = WebDeletionToken(
                token=token_hash,
                email=banned_user.email,
                user_id=banned_user.id,
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            )
            db_session.add(old_token)
            await db_session.commit()

            resp_confirm = await client.post(
                "/api/v1/legal/web-account-deletion/confirm",
                json={"token": raw_token},
            )
            assert resp_confirm.status_code == 403
            assert resp_confirm.json()["error_code"] == "ACCOUNT_SUSPENDED_OR_BANNED"

            # Assert banned user was NOT deleted
            user_check = await db_session.get(User, banned_user.id)
            assert user_check is not None
    finally:
        app.dependency_overrides.pop(get_db, None)


# ============================================================================
# 5. VULN-WS-02: Global Presence Broadcast PII Leakage Scoped to Peers
# ============================================================================

@pytest.mark.asyncio
async def test_presence_not_broadcast_to_unrelated_strangers(db_session, make_user):
    """VULN-WS-02: broadcast_presence is strictly scoped to mutual active match peers and never leaks to strangers."""
    user_a = make_user(full_name="User A")
    user_b = make_user(full_name="User B (Match of A)")
    user_c = make_user(full_name="User C (Stranger)")
    db_session.add_all([user_a, user_b, user_c])
    await db_session.commit()

    # Create mock WebSockets
    class MockWs:
        def __init__(self):
            self.frames = []
        async def send_json(self, data):
            self.frames.append(data)

    ws_a = MockWs()
    ws_b = MockWs()
    ws_c = MockWs()

    # Register in connection manager
    async with connection_manager._lock:
        connection_manager._active_connections[user_a.id].add(ws_a)
        connection_manager._active_connections[user_b.id].add(ws_b)
        connection_manager._active_connections[user_c.id].add(ws_c)

    # Broadcast presence scoped strictly to User B (active match of User A)
    await connection_manager.broadcast_presence(user_a.id, "online", peer_ids={user_b.id})

    # Assert User B received the presence event
    assert len(ws_b.frames) == 1
    assert ws_b.frames[0]["type"] == "presence"
    assert ws_b.frames[0]["user_id"] == str(user_a.id)
    assert ws_b.frames[0]["status"] == "online"

    # Assert Stranger User C received NOTHING
    assert len(ws_c.frames) == 0

    # Assert calling broadcast_presence with empty peer_ids or None sends to no one
    await connection_manager.broadcast_presence(user_a.id, "online", peer_ids=None)
    assert len(ws_b.frames) == 1  # Unchanged
    assert len(ws_c.frames) == 0


# ============================================================================
# 6. VULN-DPDP-04: Data Export Rate Limiting (2/minute)
# ============================================================================

@pytest.mark.asyncio
async def test_data_export_rate_limiting_enforced(db_session, make_user):
    """VULN-DPDP-04: Subject Access Request (SAR) data export endpoint enforces strict rate limiting."""
    user = make_user()
    db_session.add(user)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # Request 1: 200 OK
            r1 = await client.post("/api/v1/legal/data-export")
            assert r1.status_code == 200

            # Request 2: 200 OK
            r2 = await client.post("/api/v1/legal/data-export")
            assert r2.status_code == 200

            # Request 3: Exceeds 2/minute -> 429 Too Many Requests
            r3 = await client.post("/api/v1/legal/data-export")
            assert r3.status_code == 429
            assert r3.json()["error_code"] == "RATE_LIMIT_EXCEEDED"
    finally:
        app.dependency_overrides.clear()


# ============================================================================
# 7. VULN-WS-03: Oversized client_id Payload Handled Without Crash
# ============================================================================

@pytest.mark.asyncio
async def test_ws_oversized_client_id_returns_error_without_crash(db_session, make_user):
    """VULN-WS-03: Oversized client_id (> 64 chars) is rejected with INVALID_CLIENT_ID without terminating the connection."""
    u1 = make_user()
    u2 = make_user()
    if u1.id > u2.id:
        u1, u2 = u2, u1
    db_session.add_all([u1, u2])
    await db_session.commit()

    match = Match(user1_id=u1.id, user2_id=u2.id, is_active=True, closure_status="active")
    db_session.add(match)
    await db_session.commit()

    ticket = await ws_ticket_store.create_ticket(u1.id, ttl_seconds=60)
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        async with AsyncWsClient(app, f"/ws/chat?ticket={ticket}") as client:
            # Send message with 128-char client_id
            await client.send_json({
                "type": "message",
                "match_id": str(match.id),
                "recipient_id": str(u2.id),
                "encrypted_text": "valid_message_cipher",
                "client_id": "A" * 128,
            })

            # Must receive INVALID_CLIENT_ID error frame
            err_frame = await client.receive_json()
            assert err_frame["type"] == "error"
            assert err_frame["error_code"] == "INVALID_CLIENT_ID"

            # Verify connection remains open and functional by sending a valid message
            await client.send_json({
                "type": "message",
                "match_id": str(match.id),
                "recipient_id": str(u2.id),
                "encrypted_text": "second_valid_message_cipher",
                "client_id": "valid_client_id_01",
            })
            ack_frame = await client.receive_json()
            assert ack_frame["type"] == "ack"
            assert ack_frame["client_id"] == "valid_client_id_01"
    finally:
        app.dependency_overrides.pop(get_db, None)


# ============================================================================
# 8. VULN-WS-04: Ephemeral WebSocket Ticket Rate Limiting (20/minute)
# ============================================================================

@pytest.mark.asyncio
async def test_ws_ticket_rate_limiting(db_session, make_user):
    """VULN-WS-04: Rapid flooding of /api/v1/chat/ws-ticket triggers rate limit (429)."""
    user = make_user()
    db_session.add(user)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            statuses = []
            for _ in range(25):
                resp = await client.post("/api/v1/chat/ws-ticket")
                statuses.append(resp.status_code)

            # First 20 requests succeed (200), subsequent requests throttled (429)
            assert 429 in statuses
            assert statuses[0] == 200
            assert statuses[-1] == 429
    finally:
        app.dependency_overrides.clear()


# ============================================================================
# 9. VULN-DPDP-05: Non-Existent Target User in Grievance Returns 404 (Not 500)
# ============================================================================

@pytest.mark.asyncio
async def test_grievance_with_invalid_target_uuid_returns_404_not_500(db_session, make_user):
    """VULN-DPDP-05: Grievance and emergency takedown endpoints return 404 TARGET_USER_NOT_FOUND
    instead of unhandled ForeignKey constraint 500 when reported user does not exist.
    """
    reporter = make_user()
    db_session.add(reporter)
    await db_session.commit()

    non_existent_uuid = str(uuid.uuid4())
    app.dependency_overrides[get_current_user] = lambda: reporter
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. POST /api/v1/legal/grievance
            grv_resp = await client.post(
                "/api/v1/legal/grievance",
                json={
                    "reported_user_id": non_existent_uuid,
                    "violation_category": "harassment",
                    "evidence_text": "Reporting non-existent entity",
                },
            )
            assert grv_resp.status_code == 404
            assert grv_resp.json()["error_code"] == "TARGET_USER_NOT_FOUND"

            # 2. POST /api/v1/legal/emergency-takedown
            takedown_resp = await client.post(
                "/api/v1/legal/emergency-takedown",
                json={
                    "complainant_name": "Sita Devi",
                    "complainant_email": "sita@urheart.app",
                    "violation_category": "ncii",
                    "reported_user_id": non_existent_uuid,
                    "evidence_text": "Non-existent user takedown",
                    "good_faith_affirmation": True,
                },
            )
            assert takedown_resp.status_code == 404
            assert takedown_resp.json()["error_code"] == "TARGET_USER_NOT_FOUND"
    finally:
        app.dependency_overrides.clear()


# ============================================================================
# 10. VULN-DPDP-06: Digital Nominee Designation Writes Consent Audit Log
# ============================================================================

@pytest.mark.asyncio
async def test_nominee_registration_creates_immutable_consent_audit_log(db_session, make_user):
    """VULN-DPDP-06: Registering/updating a digital nominee writes an immutable entry
    to consent_audit_logs with purpose limitation 'dpdp_section14_nominee_designation'.
    """
    user = make_user(full_name="Nominee Delegator")
    db_session.add(user)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            nominee_payload = {
                "nominee_name": "Lakshman Sharma",
                "nominee_contact": "+919988776655",
                "relationship": "Brother",
            }
            resp = await client.post("/api/v1/legal/nominee", json=nominee_payload)
            assert resp.status_code == 200

            # Verify DataNominee created
            stmt_nom = select(DataNominee).where(DataNominee.user_id == user.id)
            nominee = (await db_session.execute(stmt_nom)).scalar_one_or_none()
            assert nominee is not None
            assert nominee.nominee_name == "Lakshman Sharma"

            # Verify ConsentAuditLog created with statutory purpose
            stmt_log = select(ConsentAuditLog).where(
                ConsentAuditLog.user_id == user.id,
                ConsentAuditLog.consent_purpose_id == "dpdp_section14_nominee_designation",
            )
            logs = (await db_session.execute(stmt_log)).scalars().all()
            assert len(logs) >= 1
            assert logs[0].ip_hash is not None
            assert len(logs[0].ip_hash) == 64  # SHA-256 hash
    finally:
        app.dependency_overrides.clear()
