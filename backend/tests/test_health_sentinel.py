import pytest
import httpx
from fastapi import Request
from backend.app.main import app
from backend.app.core.config import settings, validate_production_secrets
from backend.app.core.exceptions import SanctuaryException
from backend.app.core.limiter import limiter

# Temporary test route to trigger rate limiter deterministically
@app.get("/test-rate-limit")
@limiter.limit("2/minute")
async def rate_limited_route(request: Request):
    return {"message": "allowed"}

# Temporary test route to test SanctuaryException serialization
@app.get("/test-sanctuary-exception")
async def exception_route():
    raise SanctuaryException(
        error_code="TEST_ERROR",
        message="Test sanctuary exception triggered",
        status_code=400,
        details={"hint": "verification"},
    )

@pytest.mark.asyncio
async def test_health_get():
    """Test 1: GET /health returns 200, valid JSON, and header X-Sanctuary-Alive: true."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.headers.get("X-Sanctuary-Alive") == "true"
        assert resp.headers.get("Cache-Control") == "no-cache, no-store, must-revalidate"
        data = resp.json()
        assert data["status"] == "alive"
        assert data["sanctuary"] == "active"
        assert data["db_overhead_ms"] == 0

        # Verify /api/v1/health prefix mounting
        v1_resp = await client.get("/api/v1/health")
        assert v1_resp.status_code == 200
        assert v1_resp.headers.get("X-Sanctuary-Alive") == "true"

@pytest.mark.asyncio
async def test_health_head():
    """Test 2: HEAD /health returns 200, 0-length body, and header X-Sanctuary-Alive: true."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.head("/health")
        assert resp.status_code == 200
        assert resp.headers.get("X-Sanctuary-Alive") == "true"
        assert resp.headers.get("Cache-Control") == "no-cache, no-store, must-revalidate"
        assert len(resp.content) == 0

@pytest.mark.asyncio
async def test_root_head_and_get():
    """Test 3: HEAD / and GET / respond with keep-alive headers for UptimeRobot."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        head_resp = await client.head("/")
        assert head_resp.status_code == 200
        assert head_resp.headers.get("X-Sanctuary-Alive") == "true"
        assert len(head_resp.content) == 0

        get_resp = await client.get("/")
        assert get_resp.status_code == 200
        assert get_resp.headers.get("X-Sanctuary-Alive") == "true"
        data = get_resp.json()
        assert data["sanctuary"] == "active"

@pytest.mark.asyncio
async def test_security_headers_middleware():
    """Test that Starlette security headers are injected into HTTP responses."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "DENY"
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert "geolocation=()" in resp.headers.get("Permissions-Policy", "")

@pytest.mark.asyncio
async def test_rate_limiter_exceeded():
    """Test 4: Rate limiter fires and returns structured HTTP 429 when limits are breached."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Request 1 & 2 succeed (limit is 2/minute)
        r1 = await client.get("/test-rate-limit")
        assert r1.status_code == 200
        r2 = await client.get("/test-rate-limit")
        assert r2.status_code == 200

        # Request 3 breaches limit
        r3 = await client.get("/test-rate-limit")
        assert r3.status_code == 429
        data = r3.json()
        assert data["success"] is False
        assert data["error_code"] == "RATE_LIMIT_EXCEEDED"
        assert "Too many requests" in data["message"]
        assert "timestamp" in data

@pytest.mark.asyncio
async def test_sanctuary_exception_handling():
    """Test that SanctuaryException routes through custom handler yielding unified error JSON."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/test-sanctuary-exception")
        assert resp.status_code == 400
        data = resp.json()
        assert data["success"] is False
        assert data["error_code"] == "TEST_ERROR"
        assert data["message"] == "Test sanctuary exception triggered"
        assert data["details"]["hint"] == "verification"
        assert "timestamp" in data

def test_validate_production_secrets():
    """Test 5: validate_production_secrets() raises RuntimeError on short JWT_SECRET_KEY when ENVIRONMENT=production."""
    orig_env = settings.ENVIRONMENT
    orig_jwt = settings.JWT_SECRET_KEY
    orig_sub = settings.SUPABASE_URL
    orig_key = settings.SUPABASE_SERVICE_ROLE_KEY
    orig_db = settings.DATABASE_URL
    orig_admin = settings.SUPERADMIN_SECRET_KEY
    orig_cb = settings.CONTACT_BRIDGE_SECRET_KEY
    try:
        settings.ENVIRONMENT = "production"
        settings.JWT_SECRET_KEY = "too-short"
        settings.SUPABASE_URL = "https://test.supabase.co"
        settings.SUPABASE_SERVICE_ROLE_KEY = "test-service-key"
        settings.SUPERADMIN_SECRET_KEY = "secure-superadmin-secret-32b-key"
        settings.CONTACT_BRIDGE_SECRET_KEY = "secure-contact-bridge-32b-key"
        settings.DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/urheart"
        with pytest.raises(RuntimeError, match="JWT_SECRET_KEY must be at least 32 characters"):
            validate_production_secrets()

        # When JWT_SECRET_KEY has >= 32 chars and persistent DB / Supabase is configured
        settings.JWT_SECRET_KEY = "a" * 32
        validate_production_secrets()  # Should succeed without error
    finally:
        settings.ENVIRONMENT = orig_env
        settings.JWT_SECRET_KEY = orig_jwt
        settings.SUPABASE_URL = orig_sub
        settings.SUPABASE_SERVICE_ROLE_KEY = orig_key
        settings.DATABASE_URL = orig_db
        settings.SUPERADMIN_SECRET_KEY = orig_admin
        settings.CONTACT_BRIDGE_SECRET_KEY = orig_cb


@pytest.mark.asyncio
async def test_sentinels_rate_limit_exempt():
    """Test 6: Verify liveness sentinels (/health and /) are exempt from rate limiting."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Rapidly invoke /health 10 times; should all succeed 200 without 429
        for _ in range(10):
            resp = await client.get("/health")
            assert resp.status_code == 200
            assert resp.headers.get("X-Sanctuary-Alive") == "true"

        # Rapidly invoke root sentinel / 10 times
        for _ in range(10):
            resp = await client.get("/")
            assert resp.status_code == 200
            assert resp.headers.get("X-Sanctuary-Alive") == "true"


@pytest.mark.asyncio
async def test_cors_credentials_security():
    """Test 7: Verify credentialed CORS policy allows trusted origins and rejects wildcards/untrusted origins."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 1. Trusted origin receives CORS allow headers
        trusted_headers = {"Origin": "https://urheart.app"}
        resp = await client.get("/health", headers=trusted_headers)
        assert resp.status_code == 200
        assert resp.headers.get("access-control-allow-origin") == "https://urheart.app"
        assert resp.headers.get("access-control-allow-credentials") == "true"

        # 2. Local dev origin receives CORS allow headers
        dev_headers = {"Origin": "http://localhost:3000"}
        resp = await client.get("/health", headers=dev_headers)
        assert resp.status_code == 200
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"
        assert resp.headers.get("access-control-allow-credentials") == "true"

        # 3. Disallowed origin does NOT receive access-control-allow-origin header
        untrusted_headers = {"Origin": "https://malicious-cross-origin.com"}
        resp = await client.get("/health", headers=untrusted_headers)
        assert resp.status_code == 200
        assert "access-control-allow-origin" not in resp.headers

