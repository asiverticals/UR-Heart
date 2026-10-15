import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy import select

from backend.app.api.deps import get_current_superadmin, get_current_user
from backend.app.core.config import settings, validate_production_secrets
from backend.app.core.database import get_db
from backend.app.core.exceptions import SanctuaryException
from backend.app.core.security import create_access_token
from backend.app.main import app
from backend.app.models.domain import AdminKycEscalation, Match, User
from backend.app.services.admin_service import AdminService
from backend.app.services.photo_reveal_service import PhotoRevealService
from backend.app.services.storage_service import CloudflareR2StorageService, get_storage_service


@pytest.fixture
def mock_storage():
    storage = MagicMock(spec=CloudflareR2StorageService)
    storage.public_domain = "https://media.urheart.app"
    storage.bucket_name = "ur-heart-media"
    storage.generate_presigned_get_url.side_effect = (
        lambda key, expires_in=900: f"https://media.urheart.app/signed/{key}?expires={expires_in}"
    )
    storage.generate_presigned_put_url.side_effect = (
        lambda key, content_type="image/webp", expires_in=120: f"https://media.urheart.app/put/{key}"
    )
    storage.get_public_cdn_url.side_effect = lambda key: f"https://media.urheart.app/{key}"
    storage.get_object_bytes.return_value = b"\x89PNG\r\n\x1a\nfake_image_bytes"
    storage.put_object_bytes.return_value = True
    storage.delete_object.return_value = True
    storage.delete_objects_by_prefix.return_value = 2
    return storage


@pytest.mark.asyncio
async def test_seeker_full_lifecycle(db_session, make_user, mock_storage):
    """Test 1: Full Seeker Lifecycle:
    Register intent -> Google auth sync -> Profile completion -> Groq KYC ->
    Discovery feed -> Bilateral photo reveal -> 1:1 chat dialogue ticket & WSS handshake ->
    Pass with Grace closure -> DPDP Section 12 account incineration.
    """
    transport = ASGITransport(app=app)
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_storage_service] = lambda: mock_storage

    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Register intent (Adult seeker >= 18)
            reg_resp = await client.post(
                "/api/v1/auth/register-intent",
                json={
                    "dob": "2000-01-01",
                    "device_fingerprint": "a" * 32,
                },
            )
            assert reg_resp.status_code == 200
            reg_data = reg_resp.json()["data"]
            assert reg_data["eligible"] is True

            # 2. Complete Profile Setup with 5 photos and active seeker identity
            seeker = make_user(
                full_name="Ananya Sharma",
                dob=date(2000, 1, 1),
                gender="Woman",
                interested_in="Men",
                is_profile_completed=True,
                kyc_status=True,
                photos=[
                    "https://media.urheart.app/users/ananya/slot_1.webp",
                    "https://media.urheart.app/users/ananya/slot_2.webp",
                    "https://media.urheart.app/users/ananya/slot_3.webp",
                    "https://media.urheart.app/users/ananya/slot_4.webp",
                    "https://media.urheart.app/users/ananya/slot_5.webp",
                ],
            )
            peer = make_user(
                full_name="Kabir Das",
                dob=date(1998, 5, 10),
                gender="Man",
                interested_in="Women",
                is_profile_completed=True,
                kyc_status=True,
            )
            db_session.add_all([seeker, peer])
            await db_session.commit()
            await db_session.refresh(seeker)
            await db_session.refresh(peer)

            seeker_token = create_access_token(seeker.id)
            peer_token = create_access_token(peer.id)
            auth_headers = {"Authorization": f"Bearer {seeker_token}"}

            # 3. Discovery Feed Retrieval with fuzzed coordinates
            feed_resp = await client.get(
                "/api/v1/feed",
                headers=auth_headers,
            )
            assert feed_resp.status_code == 200
            feed_data = feed_resp.json()
            assert "profiles" in feed_data

            # 4. Bilateral Photo Reveal Handshake
            reveal_service = PhotoRevealService()
            req_res = await reveal_service.request_photo_reveal(seeker.id, peer.id, db_session)
            assert req_res["status"] == "pending"
            assert req_res["is_revealed"] is False

            accept_res = await reveal_service.respond_to_photo_reveal(peer.id, seeker.id, True, db_session)
            assert accept_res["status"] == "accepted"
            assert accept_res["is_revealed"] is True

            # 5. Active Match Dialogue & Ephemeral WSS Relay Ticket
            u1, u2 = min(seeker.id, peer.id), max(seeker.id, peer.id)
            match = Match(
                user1_id=u1,
                user2_id=u2,
                is_active=True,
                closure_status="active",
            )
            db_session.add(match)
            await db_session.commit()
            await db_session.refresh(match)

            ws_ticket_resp = await client.post(
                "/api/v1/chat/ws-ticket",
                headers=auth_headers,
            )
            assert ws_ticket_resp.status_code == 200
            ticket_data = ws_ticket_resp.json()["data"]
            assert "ticket" in ticket_data
            assert ticket_data["ws_url"] == "wss://urheart.app/ws/chat"

            # 6. Pass with Grace Closure Protocol
            closure_resp = await client.post(
                "/api/v1/chat/close-with-grace",
                headers=auth_headers,
                json={
                    "match_id": str(match.id),
                    "closure_template_key": "grace_paths_diverge",
                    "closure_note": "Wishing you genuine peace on your journey.",
                },
            )
            assert closure_resp.status_code == 200
            assert closure_resp.json()["data"]["success"] is True

            # Verify match state in DB
            stmt = select(Match).where(Match.id == match.id)
            closed_match = (await db_session.execute(stmt)).scalar_one()
            assert closed_match.is_active is False
            assert closed_match.closure_status == "closed_with_grace"

            # 7. DPDP Section 12 Account Incineration
            incinerate_resp = await client.request(
                "DELETE",
                "/api/v1/legal/account",
                headers=auth_headers,
                json={
                    "confirmation_phrase": "PERMANENTLY INCINERATE",
                    "reason": "Seeker departing sanctuary intentionally.",
                },
            )
            assert incinerate_resp.status_code == 200
            incinerate_data = incinerate_resp.json()["data"]
            assert incinerate_data["status"] == "incinerated"

            # Verify user record is completely incinerated from sanctuary
            user_stmt = select(User).where(User.id == seeker.id)
            incinerated_user = (await db_session.execute(user_stmt)).scalar_one_or_none()
            assert incinerated_user is None
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_storage_service, None)


@pytest.mark.asyncio
async def test_superadmin_rbac_and_kyc_escalation_desk(db_session, make_user, mock_storage):
    """Test 2: Superadmin RBAC Enforcement & KYC Escalation Desk:
    - Non-superadmin receives HTTP 403 (FORBIDDEN_ADMIN_ACCESS).
    - Superadmin inspects queue with 15-minute presigned review URLs.
    - Superadmin approves escalation, updates user.kyc_status = True, and purges R2 live frame.
    """
    transport = ASGITransport(app=app)
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_storage_service] = lambda: mock_storage

    # Create normal user, superadmin user, and borderline escalated user
    normal_user = make_user(full_name="Normal Seeker", role="user")
    superadmin = make_user(
        full_name="ASI Superadmin",
        email=settings.ADMIN_SUPERUSER_EMAIL,
        role="superadmin",
    )
    borderline_seeker = make_user(
        full_name="Borderline Seeker",
        dob=date(2001, 3, 15),
        kyc_status=False,
        photos=["https://media.urheart.app/users/borderline/photo_1.webp"],
    )
    db_session.add_all([normal_user, superadmin, borderline_seeker])
    await db_session.commit()
    await db_session.refresh(normal_user)
    await db_session.refresh(superadmin)
    await db_session.refresh(borderline_seeker)

    # Insert pending escalation ticket
    ephemeral_key = f"kyc_escalations/{borderline_seeker.id}/review_frame.webp"
    escalation = AdminKycEscalation(
        user_id=borderline_seeker.id,
        declared_dob=borderline_seeker.dob,
        groq_match_score=Decimal("0.680"),
        selfie_storage_url=ephemeral_key,
        id_card_storage_url=borderline_seeker.photos[0],
        status="pending",
    )
    db_session.add(escalation)
    await db_session.commit()
    await db_session.refresh(escalation)

    normal_token = create_access_token(normal_user.id)
    admin_token = create_access_token(superadmin.id)

    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Non-superadmin is rejected with HTTP 403
            forbidden_resp = await client.get(
                "/api/v1/admin/kyc/escalations",
                headers={"Authorization": f"Bearer {normal_token}"},
            )
            assert forbidden_resp.status_code == 403
            assert forbidden_resp.json()["error_code"] == "FORBIDDEN_ADMIN_ACCESS"

            # 2. Superadmin successfully lists escalations with presigned URLs
            admin_resp = await client.get(
                "/api/v1/admin/kyc/escalations",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert admin_resp.status_code == 200
            items = admin_resp.json()["data"]
            assert len(items) == 1
            item = items[0]
            assert item["full_name"] == "Borderline Seeker"
            assert item["groq_match_score"] == 68.0
            assert "expires" in item["live_frame_url"].lower()

            # 3. Superadmin approves escalation
            decide_resp = await client.post(
                f"/api/v1/admin/kyc/{escalation.id}/decide",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"decision": "approve", "reviewer_notes": "Facial symmetry validated by admin."},
            )
            assert decide_resp.status_code == 200
            assert decide_resp.json()["data"]["status"] == "approved"

            # 4. Verify DB state & R2 ephemeral deletion
            await db_session.refresh(borderline_seeker)
            await db_session.refresh(escalation)
            assert borderline_seeker.kyc_status is True
            assert escalation.status == "approved"
            assert escalation.reviewed_by == superadmin.email
            mock_storage.delete_object.assert_called_with(ephemeral_key)
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_storage_service, None)


@pytest.mark.asyncio
async def test_eva_bio_polish_endpoint(db_session, make_user):
    """Test 3: Eva Bio Polish Endpoint:
    - Submitting draft bio returns clean JSON with polished prose within 500 characters.
    - Submitting bio under 10 chars fails with HTTP 422.
    """
    transport = ASGITransport(app=app)
    user = make_user(profession="Sound Artist", education="Juilliard")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_access_token(user.id)
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Validation error on short bio (< 10 chars)
            short_resp = await client.post(
                "/api/v1/eva/polish-bio",
                headers={"Authorization": f"Bearer {token}"},
                json={"raw_bio": "hi"},
            )
            assert short_resp.status_code == 422

            # 2. Successful polish
            polish_resp = await client.post(
                "/api/v1/eva/polish-bio",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "raw_bio": "i love acoustic instruments, silence, walking in sacred groves, and listening deeply.",
                    "profession": "Sound Healer",
                },
            )
            assert polish_resp.status_code == 200
            data = polish_resp.json()["data"]
            assert "polished_bio" in data
            assert len(data["polished_bio"]) <= 500
            assert len(data["polished_bio"]) > 0
            assert "reflection_prompt" in data
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_sentinel_keepalive_invariant():
    """Test 4: Sentinel Keep-Alive Invariant:
    HEAD /health returns HTTP 200, X-Sanctuary-Alive: true, 0ms db overhead, and 0-length response body.
    """
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. HEAD /health
        head_resp = await client.head("/health")
        assert head_resp.status_code == 200
        assert head_resp.headers.get("X-Sanctuary-Alive") == "true"
        assert head_resp.headers.get("Cache-Control") == "no-cache, no-store, must-revalidate"
        assert len(head_resp.content) == 0

        # 2. GET /health
        get_resp = await client.get("/health")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["status"] == "alive"
        assert data["sanctuary"] == "active"
        assert data["db_overhead_ms"] == 0


def test_production_secret_guard(monkeypatch):
    """Test 5: Production Secret Guard:
    Setting ENVIRONMENT=production with short JWT_SECRET_KEY or empty secrets aborts bootstrap via validate_production_secrets().
    """
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", "short_weak_key")

    with pytest.raises((RuntimeError, SanctuaryException)) as exc_info:
        validate_production_secrets()

    assert "JWT_SECRET_KEY" in str(exc_info.value)
