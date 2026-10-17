import hmac
import time
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import httpx
import jwt
import pytest
from sqlalchemy import select

from backend.app.api.deps import get_current_superadmin, get_superadmin
from backend.app.core.config import settings, validate_production_secrets
from backend.app.core.database import get_db
from backend.app.core.exceptions import SanctuaryException
from backend.app.core.security import create_access_token, create_magic_link_token, create_refresh_token
from backend.app.main import app
from backend.app.models.domain.user import User


@pytest.fixture
def override_db(db_session):
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    yield db_session
    app.dependency_overrides.clear()


# ==============================================================================
# SECTION 1: REVOCATION GUARANTEES & STALE TOKEN INVALIDATION
# ==============================================================================


@pytest.mark.asyncio
async def test_stale_access_token_rejected_on_multiple_endpoints_after_logout(override_db, make_user):
    """Stress-test 1.1: Verify that after logout, stale access token is rejected
    across auth, profile, and logout endpoints with HTTP 401 TOKEN_REVOKED."""
    user = make_user(is_profile_completed=True)
    user.token_version = 1
    override_db.add(user)
    await override_db.commit()

    stale_access_token = create_access_token(user.id, token_version=1)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Pre-condition: endpoint succeeds before logout
        pre_resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {stale_access_token}"})
        assert pre_resp.status_code == 200

        # Perform logout
        logout_resp = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {stale_access_token}"},
        )
        assert logout_resp.status_code == 200
        assert logout_resp.json()["data"]["token_version"] == 2

        # Post-condition: Attempting to use the stale token on GET /api/v1/auth/me
        resp_me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {stale_access_token}"})
        assert resp_me.status_code == 401
        assert resp_me.json()["error_code"] == "TOKEN_REVOKED"

        # Attempting to use stale token on GET /api/v1/feed
        resp_feed_get = await client.get(
            "/api/v1/feed", headers={"Authorization": f"Bearer {stale_access_token}"}
        )
        assert resp_feed_get.status_code == 401
        assert resp_feed_get.json()["error_code"] == "TOKEN_REVOKED"

        # Attempting to use stale token on PUT /api/v1/profile
        resp_profile_put = await client.put(
            "/api/v1/profile",
            headers={"Authorization": f"Bearer {stale_access_token}"},
            json={"bio": "Adversarial update attempt"},
        )
        assert resp_profile_put.status_code == 401
        assert resp_profile_put.json()["error_code"] == "TOKEN_REVOKED"

        # Attempting to call POST /api/v1/auth/logout AGAIN with stale token must fail
        resp_logout_replay = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {stale_access_token}"},
        )
        assert resp_logout_replay.status_code == 401
        assert resp_logout_replay.json()["error_code"] == "TOKEN_REVOKED"


@pytest.mark.asyncio
async def test_stale_refresh_token_rejected_after_logout(override_db, make_user):
    """Stress-test 1.2: Verify that after logout, stale refresh token cannot refresh sessions."""
    user = make_user()
    user.token_version = 1
    override_db.add(user)
    await override_db.commit()

    access_token = create_access_token(user.id, token_version=1)
    stale_refresh_token = create_refresh_token(user.id, token_version=1)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Perform logout
        logout_resp = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert logout_resp.status_code == 200

        # Attempt token refresh with pre-logout refresh token
        refresh_resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": stale_refresh_token},
        )
        assert refresh_resp.status_code == 401
        assert refresh_resp.json()["error_code"] == "INVALID_REFRESH_TOKEN"
        assert "revoked" in refresh_resp.json()["message"].lower()


@pytest.mark.asyncio
async def test_token_version_tampering_and_type_confusion(override_db, make_user):
    """Stress-test 1.3: Verify that crafted tokens with anomalous or non-integer
    token_version types are strictly rejected with HTTP 401."""
    user = make_user()
    user.token_version = 2
    override_db.add(user)
    await override_db.commit()

    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=30)

    # Malicious token payloads to test
    anomalous_payloads = [
        {"token_version": 1},  # Obsolete version (< user.token_version)
        {"token_version": 0},  # Zero
        {"token_version": -1},  # Negative int
        {"token_version": True},  # Boolean True
        {"token_version": False},  # Boolean False
        {"token_version": "2"},  # String representation
        {"token_version": 2.0},  # Float
        {"token_version": None},  # Null
        {},  # Completely missing token_version (defaults to 1, user is 2)
    ]

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        for payload_extra in anomalous_payloads:
            # Craft access token
            acc_payload = {
                "sub": str(user.id),
                "iat": int(now.timestamp()),
                "exp": int(expire.timestamp()),
                "type": "access",
            }
            acc_payload.update(payload_extra)
            forged_access = jwt.encode(acc_payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

            resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {forged_access}"})
            assert resp.status_code == 401, f"Failed on access payload: {payload_extra}"
            assert resp.json()["error_code"] == "TOKEN_REVOKED"

            # Craft refresh token
            ref_payload = {
                "sub": str(user.id),
                "iat": int(now.timestamp()),
                "exp": int(expire.timestamp()),
                "type": "refresh",
            }
            ref_payload.update(payload_extra)
            forged_refresh = jwt.encode(ref_payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

            ref_resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": forged_refresh})
            assert ref_resp.status_code == 401, f"Failed on refresh payload: {payload_extra}"
            assert ref_resp.json()["error_code"] == "INVALID_REFRESH_TOKEN"


@pytest.mark.asyncio
async def test_soft_deleted_user_revocation_guarantees(override_db, make_user):
    """Stress-test 1.4: Verify that soft-deleted seekers are locked out immediately,
    regardless of token_version validity."""
    user = make_user()
    user.token_version = 1
    user.deleted_at = datetime.now(timezone.utc)
    override_db.add(user)
    await override_db.commit()

    access_token = create_access_token(user.id, token_version=1)
    refresh_token = create_refresh_token(user.id, token_version=1)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Access token fails with USER_NOT_FOUND
        me_resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
        assert me_resp.status_code == 401
        assert me_resp.json()["error_code"] == "USER_NOT_FOUND"

        # Refresh token fails with SEEKER_NOT_FOUND
        ref_resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert ref_resp.status_code == 404
        assert ref_resp.json()["error_code"] == "SEEKER_NOT_FOUND"

        # Logout fails with USER_NOT_FOUND
        logout_resp = await client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {access_token}"})
        assert logout_resp.status_code == 401
        assert logout_resp.json()["error_code"] == "USER_NOT_FOUND"


@pytest.mark.asyncio
async def test_sequential_multi_session_revocation(override_db, make_user):
    """Stress-test 1.5: Simulate 3 devices with active sessions for the same user.
    Verify that logout from device 1 instantly revokes device 2 and 3."""
    user = make_user()
    user.token_version = 1
    override_db.add(user)
    await override_db.commit()

    device1_token = create_access_token(user.id, token_version=1)
    device2_token = create_access_token(user.id, token_version=1)
    device3_token = create_access_token(user.id, token_version=1)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # All 3 devices are initially authorized
        for tok in (device1_token, device2_token, device3_token):
            r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tok}"})
            assert r.status_code == 200

        # Device 1 logs out
        logout_r = await client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {device1_token}"})
        assert logout_r.status_code == 200

        # Devices 1, 2, and 3 are now all revoked
        for tok in (device1_token, device2_token, device3_token):
            r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tok}"})
            assert r.status_code == 401
            assert r.json()["error_code"] == "TOKEN_REVOKED"


# ==============================================================================
# SECTION 2: TOKEN ROTATION & REPLAY ATTACK MITIGATION
# ==============================================================================


@pytest.mark.asyncio
async def test_token_type_confusion_attacks(override_db, make_user):
    """Stress-test 2.1: Verify cross-type token replay attacks are rejected."""
    user = make_user()
    user.token_version = 1
    override_db.add(user)
    await override_db.commit()

    access_token = create_access_token(user.id, token_version=1)
    refresh_token = create_refresh_token(user.id, token_version=1)
    magic_token = create_magic_link_token(user.email)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Attack 1: Pass access token as refresh token
        r1 = await client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})
        assert r1.status_code == 401
        assert r1.json()["error_code"] == "INVALID_REFRESH_TOKEN"
        assert "not a valid refresh token" in r1.json()["message"].lower()

        # Attack 2: Pass refresh token as Bearer access token
        r2 = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {refresh_token}"})
        assert r2.status_code == 401
        assert r2.json()["error_code"] == "INVALID_TOKEN"

        # Attack 3: Pass magic link token as Bearer access token
        r3 = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {magic_token}"})
        assert r3.status_code == 401
        assert r3.json()["error_code"] == "INVALID_TOKEN"

        # Attack 4: Pass magic link token as refresh token
        r4 = await client.post("/api/v1/auth/refresh", json={"refresh_token": magic_token})
        assert r4.status_code == 401
        assert r4.json()["error_code"] == "INVALID_REFRESH_TOKEN"


@pytest.mark.asyncio
async def test_expired_token_rejection(override_db, make_user):
    """Stress-test 2.2: Verify expired access and refresh tokens cannot be replayed."""
    user = make_user()
    user.token_version = 1
    override_db.add(user)
    await override_db.commit()

    # Create expired access token (-10 seconds)
    expired_access = create_access_token(user.id, expires_delta=timedelta(seconds=-10), token_version=1)
    # Create expired refresh token (-10 seconds)
    expired_refresh = create_refresh_token(user.id, expires_delta=timedelta(seconds=-10), token_version=1)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Expired access token rejected
        r1 = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_access}"})
        assert r1.status_code == 401
        assert r1.json()["error_code"] == "INVALID_TOKEN"

        # Expired refresh token rejected
        r2 = await client.post("/api/v1/auth/refresh", json={"refresh_token": expired_refresh})
        assert r2.status_code == 401
        assert r2.json()["error_code"] == "INVALID_REFRESH_TOKEN"


@pytest.mark.asyncio
async def test_forged_signature_and_algorithm_tampering(override_db, make_user):
    """Stress-test 2.3: Verify algorithm none attack and key tampering attacks fail."""
    user = make_user()
    user.token_version = 1
    override_db.add(user)
    await override_db.commit()

    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=30)
    payload = {
        "sub": str(user.id),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "access",
        "token_version": 1,
    }

    # Attack 1: alg: none
    none_alg_token = jwt.encode(payload, key="", algorithm="none")

    # Attack 2: signed with incorrect secret
    wrong_key_token = jwt.encode(payload, key="completely-wrong-jwt-secret-key-64b", algorithm="HS256")

    # Attack 3: malformed string
    malformed_token = "eyJhbGciOiJIUzI1NiJ9.not-valid-json-payload.corrupted"

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        for bad_tok in (none_alg_token, wrong_key_token, malformed_token):
            resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {bad_tok}"})
            assert resp.status_code == 401
            assert resp.json()["error_code"] == "INVALID_TOKEN"


# ==============================================================================
# SECTION 3: SUPERADMIN HMAC COMPARISON & ENVIRONMENT INVARIANTS
# ==============================================================================


@pytest.mark.asyncio
async def test_superadmin_hmac_timing_and_equality_edge_cases(override_db, monkeypatch):
    """Stress-test 3.1: Verify constant-time HMAC comparison, prefix/suffix attacks,
    case sensitivity, and whitespace handling."""
    admin_key = "SentinelSecret2026_Strict#Key"
    monkeypatch.setattr(settings, "SUPERADMIN_SECRET_KEY", admin_key)

    # 1. Exact match succeeds
    assert await get_superadmin(x_superadmin_key=admin_key, credentials=None, db=override_db) is True

    # 2. Leading/trailing whitespace in header is stripped cleanly
    assert await get_superadmin(x_superadmin_key=f"  {admin_key}  ", credentials=None, db=override_db) is True

    # 3. Off-by-one / prefix attack (missing last character)
    with pytest.raises(SanctuaryException) as exc1:
        await get_superadmin(x_superadmin_key=admin_key[:-1], credentials=None, db=override_db)
    assert exc1.value.status_code == 403
    assert exc1.value.error_code == "SUPERADMIN_FORBIDDEN"

    # 4. Suffix attack (missing first character)
    with pytest.raises(SanctuaryException) as exc2:
        await get_superadmin(x_superadmin_key=admin_key[1:], credentials=None, db=override_db)
    assert exc2.value.status_code == 403
    assert exc2.value.error_code == "SUPERADMIN_FORBIDDEN"

    # 5. Middle character alteration
    corrupted_middle = admin_key[:10] + "X" + admin_key[11:]
    with pytest.raises(SanctuaryException) as exc3:
        await get_superadmin(x_superadmin_key=corrupted_middle, credentials=None, db=override_db)
    assert exc3.value.status_code == 403
    assert exc3.value.error_code == "SUPERADMIN_FORBIDDEN"

    # 6. Case sensitivity test
    with pytest.raises(SanctuaryException) as exc4:
        await get_superadmin(x_superadmin_key=admin_key.lower(), credentials=None, db=override_db)
    assert exc4.value.status_code == 403
    assert exc4.value.error_code == "SUPERADMIN_FORBIDDEN"


@pytest.mark.asyncio
async def test_superadmin_empty_and_null_rejection(override_db, monkeypatch):
    """Stress-test 3.2: Verify empty strings, whitespace-only strings, None values,
    and unconfigured settings fail closed."""
    # Scenario A: Secret is configured
    monkeypatch.setattr(settings, "SUPERADMIN_SECRET_KEY", "RealSecretKey_123")

    for bad_header in ("", "   ", "\t\n", None):
        with pytest.raises(SanctuaryException) as exc:
            await get_superadmin(x_superadmin_key=bad_header, credentials=None, db=override_db)
        assert exc.value.status_code == 403
        assert exc.value.error_code == "SUPERADMIN_FORBIDDEN"

    # Scenario B: Secret in settings is empty string -> header "" must NOT match!
    monkeypatch.setattr(settings, "SUPERADMIN_SECRET_KEY", "")
    for test_header in ("", "   ", "RealSecretKey_123", None):
        with pytest.raises(SanctuaryException) as exc:
            await get_superadmin(x_superadmin_key=test_header, credentials=None, db=override_db)
        assert exc.value.status_code == 403
        assert exc.value.error_code == "SUPERADMIN_FORBIDDEN"

    # Scenario C: Secret in settings is whitespace -> whitespace header must NOT match!
    monkeypatch.setattr(settings, "SUPERADMIN_SECRET_KEY", "   ")
    with pytest.raises(SanctuaryException) as exc:
        await get_superadmin(x_superadmin_key="   ", credentials=None, db=override_db)
    assert exc.value.status_code == 403
    assert exc.value.error_code == "SUPERADMIN_FORBIDDEN"


def test_validate_production_secrets_enforces_superadmin_secret(monkeypatch):
    """Stress-test 3.3: Verify boot-time production validation strictly rejects
    missing or placeholder SUPERADMIN_SECRET_KEY."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", "a" * 32)
    monkeypatch.setattr(settings, "DATABASE_URL", "postgresql+asyncpg://user:pass@host:5432/db")
    monkeypatch.setattr(settings, "SUPABASE_URL", "https://xyz.supabase.co")
    monkeypatch.setattr(settings, "SUPABASE_SERVICE_ROLE_KEY", "service_role_key_value")
    monkeypatch.setattr(settings, "CONTACT_BRIDGE_SECRET_KEY", "contact_bridge_secret_value")
    monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", "razorpay_key_secret_prod_32b")
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", "razorpay_webhook_secret_prod_32b")

    # 1. Empty secret raises RuntimeError
    monkeypatch.setattr(settings, "SUPERADMIN_SECRET_KEY", "")
    with pytest.raises(RuntimeError) as exc1:
        validate_production_secrets()
    assert "SUPERADMIN_SECRET_KEY is required" in str(exc1.value)

    # 2. Placeholder secret raises RuntimeError
    monkeypatch.setattr(settings, "SUPERADMIN_SECRET_KEY", "placeholder_superadmin_secret_key")
    with pytest.raises(RuntimeError) as exc2:
        validate_production_secrets()
    assert "must not be a placeholder" in str(exc2.value)

    # 3. Real secret passes
    monkeypatch.setattr(settings, "SUPERADMIN_SECRET_KEY", "real_production_superadmin_key_999")
    validate_production_secrets()  # Should complete with no exception
