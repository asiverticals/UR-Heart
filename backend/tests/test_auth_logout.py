import uuid
from unittest.mock import patch
import httpx
import pytest
from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.security import create_access_token, create_refresh_token
from backend.app.main import app
from backend.app.models.domain.user import User
from backend.app.services.auth_service import auth_service
from backend.app.api.deps import get_superadmin


@pytest.fixture
def override_db(db_session):
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    yield db_session
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_logout_increments_token_version(override_db, make_user):
    """Test 1: Calling POST /api/v1/auth/logout increments user.token_version in database."""
    user = make_user()
    user.token_version = 1
    override_db.add(user)
    await override_db.commit()
    await override_db.refresh(user)

    access_token = create_access_token(user.id, token_version=1)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["revoked"] is True
    assert data["data"]["token_version"] == 2

    # Verify user record in database has updated token_version
    stmt = select(User).where(User.id == user.id)
    res = await override_db.execute(stmt)
    updated_user = res.scalar_one()
    assert updated_user.token_version == 2


@pytest.mark.asyncio
async def test_access_token_rejected_after_logout(override_db, make_user):
    """Test 2: Access token with previous token_version is rejected with HTTP 401 TOKEN_REVOKED."""
    user = make_user()
    user.token_version = 1
    override_db.add(user)
    await override_db.commit()

    old_access_token = create_access_token(user.id, token_version=1)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Before logout, /api/v1/auth/me succeeds
        resp_before = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {old_access_token}"},
        )
        assert resp_before.status_code == 200

        # Perform logout
        logout_resp = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {old_access_token}"},
        )
        assert logout_resp.status_code == 200

        # After logout, old access token must be rejected with 401 TOKEN_REVOKED
        resp_after = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {old_access_token}"},
        )
        assert resp_after.status_code == 401
        err_data = resp_after.json()
        assert err_data["success"] is False
        assert err_data["error_code"] == "TOKEN_REVOKED"


@pytest.mark.asyncio
async def test_refresh_token_rejected_after_logout(override_db, make_user):
    """Test 3: Refresh token with previous token_version is rejected with HTTP 401 INVALID_REFRESH_TOKEN."""
    user = make_user()
    user.token_version = 1
    override_db.add(user)
    await override_db.commit()

    access_token = create_access_token(user.id, token_version=1)
    old_refresh_token = create_refresh_token(user.id, token_version=1)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Perform logout
        logout_resp = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert logout_resp.status_code == 200

        # Old refresh token must be rejected with 401 INVALID_REFRESH_TOKEN
        refresh_resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": old_refresh_token},
        )
        assert refresh_resp.status_code == 401
        err_data = refresh_resp.json()
        assert err_data["success"] is False
        assert err_data["error_code"] == "INVALID_REFRESH_TOKEN"
        assert "revoked" in err_data["message"].lower()


@pytest.mark.asyncio
async def test_new_tokens_after_logout_succeed_and_rotate(override_db, make_user):
    """Test 4: Newly issued tokens matching the new token_version succeed and can refresh."""
    user = make_user()
    user.token_version = 1
    override_db.add(user)
    await override_db.commit()

    old_access_token = create_access_token(user.id, token_version=1)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Logout
        await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {old_access_token}"},
        )

        # Re-fetch user to get latest token_version
        stmt = select(User).where(User.id == user.id)
        res = await override_db.execute(stmt)
        user_in_db = res.scalar_one()
        assert user_in_db.token_version == 2

        # Issue new tokens with current token_version
        new_access_token = create_access_token(user.id, token_version=user_in_db.token_version)
        new_refresh_token = create_refresh_token(user.id, token_version=user_in_db.token_version)

        # GET /api/v1/auth/me succeeds with new access token
        resp_me = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {new_access_token}"},
        )
        assert resp_me.status_code == 200

        # POST /api/v1/auth/refresh succeeds and returns rotated tokens with token_version=2
        resp_refresh = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": new_refresh_token},
        )
        assert resp_refresh.status_code == 200
        data = resp_refresh.json()
        assert "access_token" in data
        assert "refresh_token" in data


@pytest.mark.asyncio
async def test_logout_without_auth_header_fails_with_401(override_db):
    """Test 5: POST /api/v1/auth/logout without credentials yields HTTP 401 UNAUTHORIZED."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/auth/logout")

    assert resp.status_code == 401
    data = resp.json()
    assert data["success"] is False
    assert data["error_code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_multiple_sequential_logouts_increment_token_version(override_db, make_user):
    """Test 6: Multiple logouts increment token_version sequentially and invalidate all previous versions."""
    user = make_user()
    user.token_version = 1
    override_db.add(user)
    await override_db.commit()

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # First logout
        tok1 = create_access_token(user.id, token_version=1)
        r1 = await client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {tok1}"})
        assert r1.status_code == 200
        assert r1.json()["data"]["token_version"] == 2

        # Second logout using tok2
        tok2 = create_access_token(user.id, token_version=2)
        r2 = await client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {tok2}"})
        assert r2.status_code == 200
        assert r2.json()["data"]["token_version"] == 3

        # Both tok1 and tok2 are now revoked
        check1 = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tok1}"})
        assert check1.status_code == 401
        assert check1.json()["error_code"] == "TOKEN_REVOKED"

        check2 = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tok2}"})
        assert check2.status_code == 401
        assert check2.json()["error_code"] == "TOKEN_REVOKED"


@pytest.mark.asyncio
async def test_superadmin_secret_key_environment_driven_hmac(override_db, monkeypatch):
    """Test 7: SUPERADMIN_SECRET_KEY is purely environment-driven with constant-time HMAC comparison."""
    from backend.app.core.exceptions import SanctuaryException

    test_secret = "test-secret-env-configured-key-2026"
    monkeypatch.setattr(settings, "SUPERADMIN_SECRET_KEY", test_secret)

    # Valid secret passes
    assert await get_superadmin(x_superadmin_key=test_secret, credentials=None, db=override_db) is True

    # Invalid secret raises SUPERADMIN_FORBIDDEN
    with pytest.raises(SanctuaryException) as exc1:
        await get_superadmin(x_superadmin_key="wrong-secret-key", credentials=None, db=override_db)
    assert exc1.value.status_code == 403
    assert exc1.value.error_code == "SUPERADMIN_FORBIDDEN"

    # Empty key raises SUPERADMIN_FORBIDDEN
    with pytest.raises(SanctuaryException) as exc2:
        await get_superadmin(x_superadmin_key="", credentials=None, db=override_db)
    assert exc2.value.status_code == 403
    assert exc2.value.error_code == "SUPERADMIN_FORBIDDEN"

    # Empty env secret fails closed even if matching empty key
    monkeypatch.setattr(settings, "SUPERADMIN_SECRET_KEY", "")
    with pytest.raises(SanctuaryException) as exc3:
        await get_superadmin(x_superadmin_key="", credentials=None, db=override_db)
    assert exc3.value.status_code == 403
