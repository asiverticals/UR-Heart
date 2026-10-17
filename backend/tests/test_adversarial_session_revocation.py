import asyncio
from datetime import datetime, timezone
import httpx
import jwt
import pytest
from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.security import create_access_token, create_refresh_token
from backend.app.main import app
from backend.app.models.domain.user import User


@pytest.fixture
def override_db(db_session):
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    yield db_session
    app.dependency_overrides.clear()


def make_custom_jwt(user_id, token_version_val, token_type="access", secret=None):
    """Helper to craft JWTs with arbitrary token_version data types for adversarial fuzzing."""
    now = datetime.now(timezone.utc).timestamp()
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "token_version": token_version_val,
        "iat": int(now),
        "exp": int(now + 3600),
    }
    return jwt.encode(payload, secret or settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


@pytest.mark.asyncio
async def test_multi_device_revocation_all_sessions_invalidated(override_db, make_user):
    """Adversarial 1: Multi-Device Revocation.
    User logs in on 3 independent devices. When Device 1 calls /logout,
    ALL devices (1, 2, and 3) must immediately lose both access and refresh capabilities.
    """
    user = make_user()
    user.token_version = 1
    override_db.add(user)
    await override_db.commit()

    # Mint separate session tokens for Device 1, 2, 3
    d1_access = create_access_token(user.id, token_version=1)
    d1_refresh = create_refresh_token(user.id, token_version=1)

    d2_access = create_access_token(user.id, token_version=1)
    d2_refresh = create_refresh_token(user.id, token_version=1)

    d3_access = create_access_token(user.id, token_version=1)
    d3_refresh = create_refresh_token(user.id, token_version=1)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Pre-condition: All 3 devices are active and authenticated
        for tok in [d1_access, d2_access, d3_access]:
            res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tok}"})
            assert res.status_code == 200, f"Token failed pre-condition: {res.text}"

        # Device 1 initiates logout
        logout_res = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {d1_access}"},
        )
        assert logout_res.status_code == 200
        assert logout_res.json()["data"]["token_version"] == 2

        # Post-condition 1: Access tokens on ALL devices must immediately be rejected
        for i, tok in enumerate([d1_access, d2_access, d3_access], start=1):
            check_res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tok}"})
            assert check_res.status_code == 401, f"Device {i} access token was not revoked"
            err = check_res.json()
            assert err["error_code"] == "TOKEN_REVOKED"

        # Post-condition 2: Refresh tokens on remaining devices (Device 2 & 3) must be rejected
        for i, ref_tok in enumerate([d2_refresh, d3_refresh], start=2):
            ref_res = await client.post("/api/v1/auth/refresh", json={"refresh_token": ref_tok})
            assert ref_res.status_code == 401, f"Device {i} refresh token was not rejected"
            err = ref_res.json()
            assert err["error_code"] == "INVALID_REFRESH_TOKEN"
            assert "revoked" in err["message"].lower()


@pytest.mark.asyncio
async def test_revoked_token_replay_logout_rejected_and_immutable(override_db, make_user):
    """Adversarial 2: Replay Attack on Logout.
    Attempting to call /logout with an already revoked token must fail with 401 TOKEN_REVOKED
    and MUST NOT mutate the database token_version further.
    """
    user = make_user()
    user.token_version = 1
    override_db.add(user)
    await override_db.commit()

    tok_v1 = create_access_token(user.id, token_version=1)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Legitimate first logout
        r1 = await client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {tok_v1}"})
        assert r1.status_code == 200
        assert r1.json()["data"]["token_version"] == 2

        # Verify DB is at token_version == 2
        stmt = select(User).where(User.id == user.id)
        res = await override_db.execute(stmt)
        u1 = res.scalar_one()
        assert u1.token_version == 2

        # Malicious / Replay second logout with revoked tok_v1
        r2 = await client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {tok_v1}"})
        assert r2.status_code == 401
        assert r2.json()["error_code"] == "TOKEN_REVOKED"

        # Crucial check: token_version must STILL be 2, NOT 3
        res = await override_db.execute(stmt)
        u2 = res.scalar_one()
        assert u2.token_version == 2, "DB token_version was mutated by an unauthorized revoked request!"


@pytest.mark.asyncio
async def test_concurrent_logout_race_conditions(override_db, make_user):
    """Adversarial 3: Concurrent Logout Race Condition.
    Two devices invoke /logout simultaneously with valid v1 tokens.
    Session revocation must converge safely without corrupting the user record.
    """
    user = make_user()
    user.token_version = 1
    override_db.add(user)
    await override_db.commit()

    tok_a = create_access_token(user.id, token_version=1)
    tok_b = create_access_token(user.id, token_version=1)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        req_a = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {tok_a}"})
        req_b = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {tok_b}"})

        res_a, res_b = await asyncio.gather(req_a, req_b, return_exceptions=True)

        # At least one must succeed
        statuses = [getattr(res_a, "status_code", None), getattr(res_b, "status_code", None)]
        assert 200 in statuses, f"Neither concurrent logout succeeded: {statuses}"

        # User token_version in DB must be >= 2
        stmt = select(User).where(User.id == user.id)
        res = await override_db.execute(stmt)
        u = res.scalar_one()
        assert u.token_version >= 2

        # In all cases, neither tok_a nor tok_b may access /auth/me anymore
        for tok in [tok_a, tok_b]:
            check = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tok}"})
            assert check.status_code == 401
            assert check.json()["error_code"] == "TOKEN_REVOKED"


@pytest.mark.asyncio
async def test_token_version_type_confusion_and_range_fuzzing(override_db, make_user):
    """Adversarial 4: Type Confusion & Range Fuzzing on token_version.
    Attacker crafts signed JWTs with non-integer types (bool, float, string, negative)
    to bypass token_version comparison. All must be strictly rejected.
    """
    user = make_user()
    user.token_version = 2
    override_db.add(user)
    await override_db.commit()

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        fuzz_cases = [
            ("boolean True", True),
            ("boolean False", False),
            ("float", 2.5),
            ("string representation", "2"),
            ("negative integer", -1),
            ("zero", 0),
            ("None", None),
        ]

        for desc, tv_val in fuzz_cases:
            # 1. Fuzz Access Token
            fuzzed_access = make_custom_jwt(user.id, tv_val, token_type="access")
            res_acc = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {fuzzed_access}"})
            assert res_acc.status_code == 401, f"Fuzz case '{desc}' bypassed access token validation! Status: {res_acc.status_code}"
            assert res_acc.json()["error_code"] == "TOKEN_REVOKED"

            # 2. Fuzz Refresh Token
            fuzzed_refresh = make_custom_jwt(user.id, tv_val, token_type="refresh")
            res_ref = await client.post("/api/v1/auth/refresh", json={"refresh_token": fuzzed_refresh})
            assert res_ref.status_code == 401, f"Fuzz case '{desc}' bypassed refresh token validation! Status: {res_ref.status_code}"
            assert res_ref.json()["error_code"] == "INVALID_REFRESH_TOKEN"


@pytest.mark.asyncio
async def test_soft_deleted_user_logout_fails_safely(override_db, make_user):
    """Adversarial 5: Soft-deleted user account handling.
    A user whose account is soft-deleted must fail closed upon attempting logout or token refresh.
    """
    user = make_user()
    user.token_version = 1
    user.deleted_at = datetime.now(timezone.utc)
    override_db.add(user)
    await override_db.commit()

    access_tok = create_access_token(user.id, token_version=1)
    refresh_tok = create_refresh_token(user.id, token_version=1)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Logout attempt on soft-deleted account returns 401 USER_NOT_FOUND
        logout_res = await client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {access_tok}"})
        assert logout_res.status_code == 401
        assert logout_res.json()["error_code"] == "USER_NOT_FOUND"

        # Refresh attempt on soft-deleted account returns 404 SEEKER_NOT_FOUND
        refresh_res = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_tok})
        assert refresh_res.status_code == 404
        assert refresh_res.json()["error_code"] == "SEEKER_NOT_FOUND"


@pytest.mark.asyncio
async def test_interleaved_refreshes_and_logouts_cycle(override_db, make_user):
    """Adversarial 6: Interleaved Refreshes & Logouts across multiple lifecycle turns.
    Ensures that token_version monotonically increases across multiple sessions and cycles.
    """
    user = make_user()
    user.token_version = 1
    override_db.add(user)
    await override_db.commit()

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Cycle 1: token_version 1
        t1_acc = create_access_token(user.id, token_version=1)
        t1_ref = create_refresh_token(user.id, token_version=1)

        # Refresh at cycle 1 rotates tokens
        r_ref1 = await client.post("/api/v1/auth/refresh", json={"refresh_token": t1_ref})
        assert r_ref1.status_code == 200
        t1_acc_rot = r_ref1.json()["access_token"]
        t1_ref_rot = r_ref1.json()["refresh_token"]

        # Logout at cycle 1
        r_log1 = await client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {t1_acc_rot}"})
        assert r_log1.status_code == 200
        assert r_log1.json()["data"]["token_version"] == 2

        # Cycle 1 tokens dead
        assert (await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {t1_acc}"})).status_code == 401
        assert (await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {t1_acc_rot}"})).status_code == 401
        assert (await client.post("/api/v1/auth/refresh", json={"refresh_token": t1_ref})).status_code == 401
        assert (await client.post("/api/v1/auth/refresh", json={"refresh_token": t1_ref_rot})).status_code == 401

        # Cycle 2: mint token at version 2
        t2_acc = create_access_token(user.id, token_version=2)
        t2_ref = create_refresh_token(user.id, token_version=2)

        # Cycle 2 works
        assert (await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {t2_acc}"})).status_code == 200

        # Logout at cycle 2
        r_log2 = await client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {t2_acc}"})
        assert r_log2.status_code == 200
        assert r_log2.json()["data"]["token_version"] == 3

        # Cycle 2 tokens dead
        assert (await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {t2_acc}"})).status_code == 401
        assert (await client.post("/api/v1/auth/refresh", json={"refresh_token": t2_ref})).status_code == 401
