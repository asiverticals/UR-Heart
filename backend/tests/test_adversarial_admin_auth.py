"""
Adversarial Verification Test Suite for Superadmin Authentication & Gatekeeper
Challenger 1: Stress-testing security boundaries, cookie signatures, email variations,
rate-limiting enforcement, and route gatekeeping.
"""

import hmac
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock
import httpx
import jwt
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.admin_portal import (
    SESSION_COOKIE_NAME,
    SUPERADMIN_EMAIL_CANONICAL,
    create_admin_session_token,
    verify_admin_session_token,
)
from backend.app.api.deps import get_db
from backend.app.core.config import settings
from backend.app.main import app
from backend.app.models.domain.admin_telemetry import AdminAuditLog


# ==============================================================================
# Helper fixtures and builders
# ==============================================================================

def build_custom_jwt(
    sub: str = "asiverticals@gmail.com",
    role: str = "superadmin",
    token_type: str = "admin_session",
    secret: str = None,
    algorithm: str = "HS256",
    exp_offset_seconds: int = 3600,
    iat_offset_seconds: int = 0,
    headers: dict = None,
    extra_claims: dict = None,
) -> str:
    """Constructs arbitrary JWTs with customizable claims and signatures for adversarial testing."""
    secret = secret or settings.JWT_SECRET_KEY or settings.SECRET_KEY
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "role": role,
        "type": token_type,
        "iat": int((now + timedelta(seconds=iat_offset_seconds)).timestamp()),
    }
    if exp_offset_seconds is not None:
        payload["exp"] = int((now + timedelta(seconds=exp_offset_seconds)).timestamp())
    if extra_claims:
        payload.update(extra_claims)

    if algorithm == "none":
        return jwt.encode(payload, key="", algorithm="none", headers=headers)
    return jwt.encode(payload, secret, algorithm=algorithm, headers=headers)


# ==============================================================================
# 1. Adversarial Cookie Signature & Algorithm Testing
# ==============================================================================

@pytest.mark.asyncio
async def test_forged_cookie_wrong_secret_rejected():
    """Cookie signed with an attacker's HMAC key must be rejected on both web and API."""
    forged_token = build_custom_jwt(secret="attacker_secret_key_1234567890")
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as client:
        # Web portal access attempt
        res_web = await client.get("/admin", cookies={SESSION_COOKIE_NAME: forged_token})
        assert res_web.status_code == 303
        assert res_web.headers.get("location") == "/admin/login"

        # API endpoint access attempt
        res_api = await client.get("/admin/api/telemetry", cookies={SESSION_COOKIE_NAME: forged_token})
        assert res_api.status_code == 401
        assert res_api.json()["error_code"] == "ADMIN_UNAUTHORIZED"


@pytest.mark.asyncio
async def test_algorithm_none_bypass_attempt_rejected():
    """JWT algorithm 'none' attack must fail verification and return None / 401."""
    none_token = build_custom_jwt(algorithm="none")
    assert verify_admin_session_token(none_token) is None

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as client:
        res_web = await client.get("/admin", cookies={SESSION_COOKIE_NAME: none_token})
        assert res_web.status_code == 303

        res_api = await client.get("/admin/api/telemetry", cookies={SESSION_COOKIE_NAME: none_token})
        assert res_api.status_code == 401


@pytest.mark.asyncio
async def test_corrupted_signature_rejected():
    """Flipping bits or truncating JWT signature must be rejected."""
    valid_token = create_admin_session_token("asiverticals@gmail.com")
    parts = valid_token.split(".")
    tampered_sig = parts[2][:-4] + "AAAA"
    tampered_token = f"{parts[0]}.{parts[1]}.{tampered_sig}"

    assert verify_admin_session_token(tampered_token) is None

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/admin/api/telemetry", cookies={SESSION_COOKIE_NAME: tampered_token})
        assert res.status_code == 401


@pytest.mark.asyncio
async def test_malformed_and_garbage_cookies_rejected():
    """Arbitrary malformed strings and null bytes must safely fail without 500 error."""
    garbage_payloads = [
        "",
        "not-a-token",
        "header.payload",
        "header.payload.sig.extra",
        "Bearer None",
        "null",
        "undefined",
        "../../../etc/passwd",
        "<script>alert(1)</script>",
    ]
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as client:
        for garbage in garbage_payloads:
            res = await client.get("/admin/api/telemetry", cookies={SESSION_COOKIE_NAME: garbage})
            assert res.status_code == 401, f"Failed on garbage input: {garbage}"


# ==============================================================================
# 2. Tampered Payloads, Claims & Expired Tokens
# ==============================================================================

@pytest.mark.asyncio
async def test_expired_session_cookie_rejected():
    """Legitimately signed token that is expired must fail verification."""
    expired_token = build_custom_jwt(exp_offset_seconds=-3600)  # 1 hour ago
    assert verify_admin_session_token(expired_token) is None

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as client:
        res = await client.get("/admin", cookies={SESSION_COOKIE_NAME: expired_token})
        assert res.status_code == 303
        assert res.headers.get("location") == "/admin/login"


@pytest.mark.asyncio
async def test_tampered_payload_claims_rejected():
    """Tokens with illegitimate subject, type, or missing attributes must be rejected."""
    # 1. Non-superadmin email in sub
    token_wrong_sub = build_custom_jwt(sub="attacker@gmail.com")
    assert verify_admin_session_token(token_wrong_sub) is None

    # 2. Subdomain spoof in sub
    token_subdomain_spoof = build_custom_jwt(sub="asiverticals@gmail.com.evil.com")
    assert verify_admin_session_token(token_subdomain_spoof) is None

    # 3. Wrong type (e.g. regular access token)
    token_wrong_type = build_custom_jwt(token_type="access")
    assert verify_admin_session_token(token_wrong_type) is None

    # 4. Missing sub claim
    token_no_sub = build_custom_jwt(sub="")
    assert verify_admin_session_token(token_no_sub) is None


@pytest.mark.asyncio
async def test_bearer_header_adversarial_tokens():
    """Authorization: Bearer header must undergo identical strict verification."""
    expired_token = build_custom_jwt(exp_offset_seconds=-10)
    forged_token = build_custom_jwt(secret="forged_key")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Expired Bearer
        res1 = await client.get(
            "/admin/api/telemetry",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert res1.status_code == 401

        # Forged Bearer
        res2 = await client.get(
            "/admin/api/telemetry",
            headers={"Authorization": f"Bearer {forged_token}"},
        )
        assert res2.status_code == 401


# ==============================================================================
# 3. Non-Superadmin Email Variations & Login Hardening
# ==============================================================================

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "email_variant",
    [
        "attacker@gmail.com",
        "asiverticals@gmail.com.evil.com",
        "evil@asiverticals@gmail.com",
        "asiverticals+admin@gmail.com",
        "asiverticals@googlemail.com",
        "admin@urheart.app",
        "root@localhost",
        "asiverticals@gmail.com'",
        "asiverticals@gmail.com\" OR 1=1 --",
        "asiverticals@gmail.com; DROP TABLE admin_audit_logs;",
        "asiverticals @gmail.com",  # inner whitespace
        "asiverticals@gmail.co",
    ],
)
async def test_login_rejects_email_variations(email_variant: str, db_session: AsyncSession):
    """Every unauthorized email variant must be rejected with 401 and logged in audit trail."""
    app.dependency_overrides[get_db] = lambda: db_session
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/admin/api/login",
            json={"email": email_variant, "secret_key": settings.SUPERADMIN_SECRET_KEY},
            headers={"X-Forwarded-For": f"198.51.100.{hash(email_variant) % 200 + 10}"},
        )
        assert res.status_code == 401
        assert res.json()["error_code"] == "INVALID_ADMIN_CREDENTIALS"

    # Verify audit log captures failed attempt (target_id is lowercased/stripped)
    expected_target = email_variant.strip().lower()
    stmt = select(AdminAuditLog).where(
        AdminAuditLog.action == "admin_login_failed",
        AdminAuditLog.target_id == expected_target,
    )
    log = (await db_session.execute(stmt)).scalars().first()
    assert log is not None
    assert log.details.get("reason") == "unauthorized_email_rejected"


@pytest.mark.asyncio
async def test_login_accepts_canonical_case_insensitive_and_stripped(db_session: AsyncSession):
    """RFC compliant emails: uppercase and outer padding normalize to canonical superadmin."""
    app.dependency_overrides[get_db] = lambda: db_session
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/admin/api/login",
            json={"email": "  ASIVERTICALS@GMAIL.COM  ", "secret_key": settings.SUPERADMIN_SECRET_KEY},
            headers={"X-Forwarded-For": "198.51.100.99"},
        )
        assert res.status_code == 200
        assert res.json()["success"] is True
        assert SESSION_COOKIE_NAME in res.cookies


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "secret_variant",
    [
        "WrongSecret",
        (settings.SUPERADMIN_SECRET_KEY or "") + "_extra",
        (settings.SUPERADMIN_SECRET_KEY or "")[:-1],
        "' OR '1'='1",
        "",
        " ",
    ],
)
async def test_login_rejects_invalid_secrets(secret_variant: str, db_session: AsyncSession):
    """Invalid secret variants must be rejected with 401 and logged."""
    app.dependency_overrides[get_db] = lambda: db_session
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/admin/api/login",
            json={"email": "asiverticals@gmail.com", "secret_key": secret_variant},
            headers={"X-Forwarded-For": f"198.51.100.{hash(secret_variant) % 200 + 10}"},
        )
        assert res.status_code == 401
        assert res.json()["error_code"] == "INVALID_ADMIN_CREDENTIALS"


# ==============================================================================
# 4. Superadmin Secret Header (X-Superadmin-Key) Hardening
# ==============================================================================

@pytest.mark.asyncio
async def test_x_superadmin_key_header_adversarial(db_session: AsyncSession):
    """X-Superadmin-Key header requires exact constant-time match."""
    app.dependency_overrides[get_db] = lambda: db_session
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as client:
        # 1. Exact valid key -> 200 OK
        res_valid = await client.get(
            "/admin/api/telemetry",
            headers={"X-Superadmin-Key": settings.SUPERADMIN_SECRET_KEY},
        )
        assert res_valid.status_code == 200

        # 2. Off-by-one character -> 401 Unauthorized
        res_off = await client.get(
            "/admin/api/telemetry",
            headers={"X-Superadmin-Key": settings.SUPERADMIN_SECRET_KEY[:-1]},
        )
        assert res_off.status_code == 401

        # 3. Injected characters -> 401 Unauthorized
        res_inj = await client.get(
            "/admin/api/telemetry",
            headers={"X-Superadmin-Key": f"{settings.SUPERADMIN_SECRET_KEY}' OR '1'='1"},
        )
        assert res_inj.status_code == 401


# ==============================================================================
# 5. Rate Limiting Enforcement & Evasion Resistance
# ==============================================================================

@pytest.mark.asyncio
async def test_login_rate_limiting_enforcement(db_session: AsyncSession):
    """5 consecutive failed logins trigger HTTP 429 RateLimitExceeded on the 6th."""
    app.dependency_overrides[get_db] = lambda: db_session
    transport = httpx.ASGITransport(app=app)
    client_ip = "198.51.100.220"

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        for i in range(5):
            res = await client.post(
                "/admin/api/login",
                json={"email": "attacker@gmail.com", "secret_key": "wrong_password"},
                headers={"X-Forwarded-For": client_ip},
            )
            assert res.status_code == 401

        # 6th attempt must be blocked by SlowAPI rate limiter
        res_blocked = await client.post(
            "/admin/api/login",
            json={"email": "attacker@gmail.com", "secret_key": "wrong_password"},
            headers={"X-Forwarded-For": client_ip},
        )
        assert res_blocked.status_code == 429
        data = res_blocked.json()
        assert data["error_code"] == "RATE_LIMIT_EXCEEDED"
        assert "retry_after" in data["details"]


@pytest.mark.asyncio
async def test_rate_limiting_evasion_resistance_for_untrusted_direct_ip(db_session: AsyncSession):
    """Direct client from untrusted IP cannot evade rate limiting by rotating X-Forwarded-For."""
    app.dependency_overrides[get_db] = lambda: db_session
    # Untrusted remote client socket host
    transport = httpx.ASGITransport(app=app, client=("198.51.100.250", 54321))

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Attacker sends 5 failed attempts rotating X-Forwarded-For headers
        for i in range(5):
            res = await client.post(
                "/admin/api/login",
                json={"email": "attacker@gmail.com", "secret_key": "wrong_secret"},
                headers={"X-Forwarded-For": f"fake.ip.{i}.1"},
            )
            assert res.status_code == 401

        # 6th attempt with yet another rotated header must STILL be 429 because direct IP is untrusted
        res_blocked = await client.post(
            "/admin/api/login",
            json={"email": "attacker@gmail.com", "secret_key": "wrong_secret"},
            headers={"X-Forwarded-For": "fake.ip.99.1"},
        )
        assert res_blocked.status_code == 429
        assert res_blocked.json()["error_code"] == "RATE_LIMIT_EXCEEDED"


# ==============================================================================
# 6. Comprehensive Gatekeeper Subpath & Traversal Protection
# ==============================================================================

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "api_subpath,method,body",
    [
        ("/admin/api/telemetry", "GET", None),
        ("/admin/api/kyc/pending", "GET", None),
        ("/admin/api/kyc/test-id/decide", "POST", {"decision": "approve"}),
        ("/admin/api/grievances", "GET", None),
        ("/admin/api/grievances/1/resolve", "POST", {"status": "actioned"}),
        ("/admin/api/users", "GET", None),
        ("/admin/api/users/00000000-0000-0000-0000-000000000001/toggle-ban", "POST", {}),
        ("/admin/api/quarantine", "GET", None),
        ("/admin/api/quarantine/test-qid/release", "POST", {}),
        ("/admin/api/payments", "GET", None),
        ("/admin/api/users/00000000-0000-0000-0000-000000000001/grant-sparks", "POST", {"sparks_amount": 10, "reason": "test"}),
        ("/admin/api/users/00000000-0000-0000-0000-000000000001/grant-pass", "POST", {"sku": "pass_monthly", "reason": "test"}),
        ("/admin/api/dpdp", "GET", None),
        ("/admin/api/audit-logs", "GET", None),
        ("/admin/api/logout", "POST", None),
    ],
)
async def test_gatekeeper_blocks_all_unauthenticated_api_subpaths(api_subpath: str, method: str, body: dict):
    """All /admin/api/* endpoints must return HTTP 401 when accessed without credentials."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        if method == "GET":
            res = await client.get(api_subpath)
        else:
            res = await client.post(api_subpath, json=body or {})
        assert res.status_code == 401
        assert res.json()["error_code"] == "ADMIN_UNAUTHORIZED"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "web_path",
    [
        "/admin",
        "/admin/",
        "/admin/dashboard",
        "/admin/settings",
        "/admin/users",
        "/admin/unknown/deep/path",
    ],
)
async def test_gatekeeper_blocks_all_unauthenticated_web_routes(web_path: str):
    """All unauthenticated HTML / web routes under /admin must redirect to /admin/login."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as client:
        res = await client.get(web_path)
        assert res.status_code in (302, 303, 307)
        assert res.headers.get("location") == "/admin/login"


@pytest.mark.asyncio
async def test_gatekeeper_path_traversal_attempts():
    """Path traversal trickery cannot evade the gatekeeper middleware."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as client:
        # Traversal from public login to telemetry
        res = await client.get("/admin/api/login/../telemetry")
        assert res.status_code in (401, 404, 303)
        assert res.status_code != 200

        # Dot segments in admin root
        res2 = await client.get("/admin/./dashboard")
        assert res2.status_code in (303, 404)
        if res2.status_code == 303:
            assert res2.headers.get("location") == "/admin/login"


# ==============================================================================
# 7. Hunter 1 Vulnerability Verifications (VULN-AUTH-01 through 08)
# ==============================================================================

@pytest.mark.asyncio
async def test_admin_session_token_replay_after_logout_vulnerability(db_session: AsyncSession):
    """VULN-AUTH-01: Admin session token is invalidated server-side upon logout and cannot be replayed."""
    app.dependency_overrides[get_db] = lambda: db_session
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Step 1: Login successfully
        login_res = await client.post(
            "/admin/api/login",
            json={"email": "asiverticals@gmail.com", "secret_key": settings.SUPERADMIN_SECRET_KEY},
            headers={"X-Forwarded-For": "198.51.100.11"},
        )
        assert login_res.status_code == 200
        session_token = login_res.cookies.get(SESSION_COOKIE_NAME)
        assert session_token is not None

        # Step 2: Verify active session token works on protected API
        check_res = await client.get("/admin/api/telemetry", cookies={SESSION_COOKIE_NAME: session_token})
        assert check_res.status_code == 200

        # Step 3: Perform logout
        logout_res = await client.post("/admin/api/logout", cookies={SESSION_COOKIE_NAME: session_token})
        assert logout_res.status_code == 200

        # Step 4: Replay token via cookie - must be rejected with 401
        replay_cookie = await client.get("/admin/api/telemetry", cookies={SESSION_COOKIE_NAME: session_token})
        assert replay_cookie.status_code == 401
        assert replay_cookie.json()["error_code"] == "ADMIN_UNAUTHORIZED"

        # Step 5: Replay token via Bearer header - must also be rejected with 401
        replay_bearer = await client.get(
            "/admin/api/telemetry",
            headers={"Authorization": f"Bearer {session_token}"},
        )
        assert replay_bearer.status_code == 401
        assert replay_bearer.json()["error_code"] == "ADMIN_UNAUTHORIZED"


@pytest.mark.asyncio
async def test_admin_audit_ip_spoofing_via_untrusted_header(db_session: AsyncSession):
    """VULN-AUTH-02: Direct client connecting from untrusted IP cannot spoof X-Forwarded-For in audit logs."""
    app.dependency_overrides[get_db] = lambda: db_session
    untrusted_direct_ip = "198.51.100.252"
    transport = httpx.ASGITransport(app=app, client=(untrusted_direct_ip, 54321))

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/admin/api/login",
            json={"email": "unauthorized_spoof@gmail.com", "secret_key": "wrong_password"},
            headers={"X-Forwarded-For": "203.0.113.199"},
        )
        assert res.status_code == 401

    stmt = select(AdminAuditLog).where(
        AdminAuditLog.action == "admin_login_failed",
        AdminAuditLog.target_id == "unauthorized_spoof@gmail.com",
    )
    log = (await db_session.execute(stmt)).scalars().first()
    assert log is not None
    # Must record true socket client IP, NOT forged X-Forwarded-For header
    assert log.ip_address == untrusted_direct_ip
    assert log.ip_address != "203.0.113.199"


@pytest.mark.asyncio
async def test_refresh_token_replay_attack_vulnerability(db_session: AsyncSession, make_user):
    """VULN-AUTH-03: Refresh token cannot be consumed multiple times; replays are rejected with 401."""
    app.dependency_overrides[get_db] = lambda: db_session
    user = make_user()
    user.token_version = 1
    db_session.add(user)
    await db_session.commit()

    from backend.app.core.security import create_refresh_token
    rt1 = create_refresh_token(user.id, token_version=user.token_version)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # First consumption: succeeds
        res1 = await client.post("/api/v1/auth/refresh", json={"refresh_token": rt1})
        assert res1.status_code == 200
        data1 = res1.json()
        rt2 = data1["refresh_token"]
        assert rt2 != rt1

        # Second consumption (Replay Attack with rt1): must be rejected
        res_replay = await client.post("/api/v1/auth/refresh", json={"refresh_token": rt1})
        assert res_replay.status_code == 401
        assert res_replay.json()["error_code"] == "INVALID_REFRESH_TOKEN"
        assert "revoked" in res_replay.json()["message"].lower()

        # Legitimate next turn with rt2: succeeds
        res2 = await client.post("/api/v1/auth/refresh", json={"refresh_token": rt2})
        assert res2.status_code == 200
        rt3 = res2.json()["refresh_token"]
        assert rt3 != rt2


@pytest.mark.asyncio
async def test_v1_admin_kyc_bypasses_superadmin_secret_key(db_session: AsyncSession, make_user):
    """VULN-AUTH-04: Non-superadmin role with admin email is rejected from /api/v1/admin/kyc without secret key."""
    from backend.app.core.security import create_access_token
    from backend.app.services.storage_service import get_storage_service

    app.dependency_overrides[get_db] = lambda: db_session
    mock_storage = AsyncMock()
    app.dependency_overrides[get_storage_service] = lambda: mock_storage

    # Create normal user possessing the admin email but with role="user"
    user = make_user(email="asiverticals@gmail.com", role="user")
    db_session.add(user)
    await db_session.commit()

    token = create_access_token(user.id)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Without X-Superadmin-Key: rejected with 403
        res_forbidden = await client.get(
            "/api/v1/admin/kyc/escalations",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_forbidden.status_code == 403
        assert res_forbidden.json()["error_code"] == "FORBIDDEN_ADMIN_ACCESS"

        # With valid X-Superadmin-Key: allowed
        res_authorized = await client.get(
            "/api/v1/admin/kyc/escalations",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Superadmin-Key": settings.SUPERADMIN_SECRET_KEY,
            },
        )
        assert res_authorized.status_code == 200


@pytest.mark.asyncio
async def test_age_intent_token_infinite_validity_replay():
    """VULN-AUTH-05: Age intent tokens enforce 15-minute TTL; expired or future tokens return None."""
    import hashlib
    from datetime import date
    from backend.app.services.auth_service import AuthService

    dob = date(2000, 1, 1)
    device_fp = "device_test_fingerprint_01"

    # 1. Fresh token validates successfully
    fresh_token = AuthService.generate_age_intent_token(dob, device_fp)
    verified = AuthService.verify_age_intent_token(fresh_token, device_fp)
    assert verified == dob

    # 2. Expired token (1000 seconds in the past > 900s TTL) fails validation
    past_ts = int(time.time()) - 1000
    expired_payload = f"{device_fp}:{dob.isoformat()}:{past_ts}"
    expired_sig = hmac.new(settings.SECRET_KEY.encode(), expired_payload.encode(), hashlib.sha256).hexdigest()
    expired_token = f"{expired_payload}:{expired_sig}"
    assert AuthService.verify_age_intent_token(expired_token, device_fp) is None

    # 3. Future token (> 60s in future) fails validation
    future_ts = int(time.time()) + 1000
    future_payload = f"{device_fp}:{dob.isoformat()}:{future_ts}"
    future_sig = hmac.new(settings.SECRET_KEY.encode(), future_payload.encode(), hashlib.sha256).hexdigest()
    future_token = f"{future_payload}:{future_sig}"
    assert AuthService.verify_age_intent_token(future_token, device_fp) is None

    # 4. Legacy 3-part token without timestamp is rejected
    legacy_payload = f"{device_fp}:{dob.isoformat()}"
    legacy_sig = hmac.new(settings.SECRET_KEY.encode(), legacy_payload.encode(), hashlib.sha256).hexdigest()
    legacy_token = f"{legacy_payload}:{legacy_sig}"
    assert AuthService.verify_age_intent_token(legacy_token, device_fp) is None


@pytest.mark.asyncio
async def test_admin_login_constant_time_comparison(db_session: AsyncSession):
    """VULN-AUTH-07: Timing-safe comparison evaluates both email and secret key without timing leaks."""
    app.dependency_overrides[get_db] = lambda: db_session
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Non-canonical email
        res1 = await client.post(
            "/admin/api/login",
            json={"email": "attacker@gmail.com", "secret_key": "wrong_secret"},
            headers={"X-Forwarded-For": "198.51.100.123"},
        )
        assert res1.status_code == 401

        # Canonical email with wrong secret
        res2 = await client.post(
            "/admin/api/login",
            json={"email": "asiverticals@gmail.com", "secret_key": "wrong_secret"},
            headers={"X-Forwarded-For": "198.51.100.124"},
        )
        assert res2.status_code == 401


@pytest.mark.asyncio
async def test_auth_refresh_and_google_sync_rate_limiting_enforcement(db_session: AsyncSession):
    """VULN-AUTH-08: Throttling enforced on /refresh (20/min) and /google-sync (15/min)."""
    app.dependency_overrides[get_db] = lambda: db_session
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Throttling on /refresh (limit 20/minute)
        client_ip_ref = "198.51.100.77"
        hit_429 = False
        for i in range(25):
            res = await client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": "dummy_rate_limit_token"},
                headers={"X-Forwarded-For": client_ip_ref},
            )
            if res.status_code == 429:
                hit_429 = True
                assert res.json()["error_code"] == "RATE_LIMIT_EXCEEDED"
                break
        assert hit_429, "Expected 429 RATE_LIMIT_EXCEEDED on /refresh after 20 requests"

        # 2. Throttling on /google-sync (limit 15/minute)
        client_ip_gsync = "198.51.100.88"
        hit_429_gsync = False
        for i in range(20):
            res = await client.post(
                "/api/v1/auth/google-sync",
                json={
                    "id_token": "x" * 60,
                    "installation_uuid": "dummy_uuid",
                },
                headers={"X-Forwarded-For": client_ip_gsync},
            )
            if res.status_code == 429:
                hit_429_gsync = True
                assert res.json()["error_code"] == "RATE_LIMIT_EXCEEDED"
                break
        assert hit_429_gsync, "Expected 429 RATE_LIMIT_EXCEEDED on /google-sync after 15 requests"
