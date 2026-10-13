import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
import httpx
import pytest
from sqlalchemy import select

from backend.app.api.deps import get_current_user
from backend.app.core.database import get_db
from backend.app.core.security import create_access_token, create_magic_link_token, resolve_auth_uuid
from backend.app.main import app
from backend.app.models.domain.legal import UnderageQuarantineRegistry
from backend.app.models.domain.user import User

def safe_years_ago(years: int, from_date: date | None = None) -> date:
    d = from_date or date.today()
    try:
        return d.replace(year=d.year - years)
    except ValueError:
        return date(d.year - years, 2, 28)

@pytest.fixture
def override_db(db_session):
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    yield db_session
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_register_intent_adult_success(override_db):
    """Test 1: Adult DOB satisfies 18+ gate and returns eligible=True."""
    valid_dob = safe_years_ago(22)
    device_fp = "a" * 64

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/auth/register-intent",
            json={
                "dob": valid_dob.isoformat(),
                "device_fingerprint": device_fp,
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["eligible"] is True

@pytest.mark.asyncio
async def test_register_intent_underage_rejected_and_quarantined(override_db):
    """Test 2: Underage registration attempt triggers 403 and records quarantine."""
    underage_dob = safe_years_ago(16)
    device_fp = "b" * 64

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/auth/register-intent",
            json={
                "dob": underage_dob.isoformat(),
                "device_fingerprint": device_fp,
            },
        )
    assert resp.status_code == 403
    data = resp.json()
    assert data["success"] is False
    assert data["error_code"] == "UNDERAGE_QUARANTINE_TRIGGERED"

    # Verify database persistence in quarantine registry
    stmt = select(UnderageQuarantineRegistry).where(UnderageQuarantineRegistry.device_hash == device_fp)
    result = await override_db.execute(stmt)
    quarantine = result.scalar_one_or_none()
    assert quarantine is not None
    assert quarantine.attempted_dob == underage_dob

@pytest.mark.asyncio
async def test_register_intent_quarantined_device_blocked(override_db):
    """Test 3: Previously quarantined hardware fingerprint cannot register even with adult DOB."""
    device_fp = "c" * 64
    now = datetime.now(timezone.utc)

    # Insert existing active quarantine
    quarantine = UnderageQuarantineRegistry(
        device_hash=device_fp,
        attempted_dob=safe_years_ago(15),
        quarantine_until=now + timedelta(days=180),
        attempt_metadata={"attempted_age": 15},
    )
    override_db.add(quarantine)
    await override_db.commit()

    # Attempt with adult DOB
    adult_dob = safe_years_ago(25)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/auth/register-intent",
            json={
                "dob": adult_dob.isoformat(),
                "device_fingerprint": device_fp,
            },
        )
    assert resp.status_code == 403
    data = resp.json()
    assert data["error_code"] == "UNDERAGE_QUARANTINE_TRIGGERED"

@pytest.mark.asyncio
async def test_google_sync_provision_new_user(override_db):
    """Test 4: Google OAuth sync provisions new user and returns valid TokenResponse."""
    mock_claims = {
        "sub": "google_uid_987654321",
        "email": "aarav.sharma@gmail.com",
        "email_verified": True,
        "name": "Aarav Sharma",
        "picture": "https://lh3.googleusercontent.com/avatar_aarav.jpg",
    }

    with patch("backend.app.services.auth_service.verify_google_id_token", new_callable=AsyncMock, return_value=mock_claims):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/google-sync",
                json={
                    "id_token": "mocked.valid.rs256.id_token.payload." + "x" * 30,
                    "installation_uuid": "install_hw_uuid_101",
                },
            )
        assert resp.status_code == 200
        token_data = resp.json()
        assert "access_token" in token_data
        assert "refresh_token" in token_data
        assert token_data["token_type"] == "Bearer"
        assert token_data["is_profile_completed"] is False

        # Verify created in DB
        expected_auth_id = resolve_auth_uuid(mock_claims["sub"])
        stmt = select(User).where(User.auth_id == expected_auth_id)
        res = await override_db.execute(stmt)
        user = res.scalar_one_or_none()
        assert user is not None
        assert user.email == "aarav.sharma@gmail.com"
        assert user.full_name == "Aarav Sharma"
        assert user.last_installation_uuid == "install_hw_uuid_101"

@pytest.mark.asyncio
async def test_google_sync_existing_user(override_db, make_user):
    """Test 5: Google OAuth sync recognizes existing user and issues refreshed session."""
    sub_str = "google_existing_112233"
    auth_id = resolve_auth_uuid(sub_str)
    existing_user = make_user(auth_id=auth_id, email="existing_seeker@urheart.app", full_name="Diya Patel")
    override_db.add(existing_user)
    await override_db.commit()

    mock_claims = {
        "sub": sub_str,
        "email": "existing_seeker@urheart.app",
        "email_verified": True,
        "name": "Diya Patel",
        "picture": None,
    }

    with patch("backend.app.services.auth_service.verify_google_id_token", new_callable=AsyncMock, return_value=mock_claims):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/google-sync",
                json={
                    "id_token": "mocked.valid.rs256.id_token.payload." + "x" * 30,
                    "installation_uuid": "updated_install_uuid_202",
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == str(existing_user.id)

    # Verify updated installation UUID
    await override_db.refresh(existing_user)
    assert existing_user.last_installation_uuid == "updated_install_uuid_202"

@pytest.mark.asyncio
async def test_magic_link_dispatch_and_verify(override_db):
    """Test 6: Magic link token dispatch and verification lifecycle."""
    email = "magic_traveler@urheart.app"

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Step 1: Send magic link
        send_resp = await client.post(
            "/api/v1/auth/send-magic-link",
            json={"email": email},
        )
        assert send_resp.status_code == 200
        assert send_resp.json()["data"]["dispatched"] is True

        # Step 2: Generate valid magic token and verify
        token = create_magic_link_token(email)
        verify_resp = await client.post(
            "/api/v1/auth/verify-magic-link",
            json={"token": token},
        )
        assert verify_resp.status_code == 200
        token_data = verify_resp.json()
        assert "access_token" in token_data
        assert "refresh_token" in token_data

        # Step 3: Reusing the same token must fail with 401 (single-use enforcement)
        replay_resp = await client.post(
            "/api/v1/auth/verify-magic-link",
            json={"token": token},
        )
        assert replay_resp.status_code == 401
        assert replay_resp.json()["error_code"] == "TOKEN_ALREADY_USED"

        # Step 3b: Verify ConsumedMagicToken record is physically persisted in the database
        from backend.app.models.domain.legal import ConsumedMagicToken
        stmt_cm = select(ConsumedMagicToken).where(ConsumedMagicToken.email == email)
        res_cm = await override_db.execute(stmt_cm)
        persisted_token = res_cm.scalars().first()
        assert persisted_token is not None
        assert persisted_token.email == email

        # Step 4: Invalid token fails with 401
        invalid_resp = await client.post(
            "/api/v1/auth/verify-magic-link",
            json={"token": "tampered_or_invalid_token"},
        )
        assert invalid_resp.status_code == 401

@pytest.mark.asyncio
async def test_auth_me_endpoint(override_db, make_user):
    """Test 7: /auth/me returns authentic user profile with Bearer access token."""
    user = make_user(full_name="Meera Bai", email="meera@urheart.app")
    override_db.add(user)
    await override_db.commit()

    token = create_access_token(user.id)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Without auth header -> 401
        unauth_resp = await client.get("/api/v1/auth/me")
        assert unauth_resp.status_code == 401

        # With Bearer token -> 200
        auth_resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert auth_resp.status_code == 200
        res_data = auth_resp.json()["data"]
        assert res_data["id"] == str(user.id)
        assert res_data["full_name"] == "Meera Bai"
        assert res_data["email"] == "meera@urheart.app"

@pytest.mark.asyncio
async def test_auth_sync_endpoint(override_db, make_user):
    """Test 8: /auth/sync returns session active state and updates installation UUID."""
    user = make_user()
    override_db.add(user)
    await override_db.commit()

    token = create_access_token(user.id)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/auth/sync?installation_uuid=hw_client_uuid_777",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["active"] is True
        assert data["user_id"] == str(user.id)

    await override_db.refresh(user)
    assert user.last_installation_uuid == "hw_client_uuid_777"

@pytest.mark.asyncio
async def test_register_intent_repeat_underage_updates_quarantine(override_db):
    """Test 9: Repeat underage registration attempts update quarantine idempotently without crash."""
    underage_dob = safe_years_ago(15)
    device_fp = "d" * 64

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # First attempt
        resp1 = await client.post(
            "/api/v1/auth/register-intent",
            json={"dob": underage_dob.isoformat(), "device_fingerprint": device_fp},
        )
        assert resp1.status_code == 403
        assert resp1.json()["error_code"] == "UNDERAGE_QUARANTINE_TRIGGERED"

        # Second attempt with same device fingerprint updates record instead of failing unique constraint
        resp2 = await client.post(
            "/api/v1/auth/register-intent",
            json={"dob": underage_dob.isoformat(), "device_fingerprint": device_fp},
        )
        assert resp2.status_code == 403
        assert resp2.json()["error_code"] == "UNDERAGE_QUARANTINE_TRIGGERED"

@pytest.mark.asyncio
async def test_google_sync_unverified_email_rejected_and_safe(override_db, make_user):
    """Test 10: Google token with unverified email returns 400 and preserves existing accounts."""
    existing_user = make_user(email="victim@urheart.app", full_name="Victim Seeker")
    override_db.add(existing_user)
    await override_db.commit()

    attacker_sub = "google_attacker_9999"
    attacker_auth_id = resolve_auth_uuid(attacker_sub)
    mock_claims = {
        "sub": attacker_sub,
        "email": "victim@urheart.app",
        "email_verified": False,  # Unverified email
        "name": "Attacker",
        "picture": None,
    }

    with patch("backend.app.services.auth_service.verify_google_id_token", new_callable=AsyncMock, return_value=mock_claims):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/google-sync",
                json={"id_token": "mocked.valid.rs256.id_token.payload." + "x" * 30},
            )
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "GOOGLE_EMAIL_UNVERIFIED"

    # Verify existing victim user's auth_id was NOT overwritten
    await override_db.refresh(existing_user)
    assert existing_user.auth_id != attacker_auth_id



