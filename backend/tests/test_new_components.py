import hmac
import hashlib
import json
from decimal import Decimal
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from backend.app.core.config import settings
from backend.app.main import app
from backend.app.services.storage_service import (
    SupabaseStorageService,
    UnifiedStorageService,
    CloudflareR2StorageService,
)
from backend.app.services.email_service import EmailService
from backend.app.services.ai_service import AIService
from backend.app.services.payment_service import payment_service


@pytest.mark.asyncio
async def test_supabase_storage_service(monkeypatch):
    """Verify Supabase Storage URL generation and credential validation."""
    from unittest.mock import MagicMock
    import httpx

    service = SupabaseStorageService(
        supabase_url="https://test-sub.supabase.co",
        service_role_key="mock_service_key",
        bucket_name="ur-heart-media",
    )
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "url": "/object/upload/sign/ur-heart-media/users/123/moments/slot_1.webp?token=test_token"
    }
    monkeypatch.setattr(httpx.Client, "post", lambda self, url, headers=None, json=None: mock_resp)

    put_url = service.generate_presigned_put_url("users/123/moments/slot_1.webp")
    assert "https://test-sub.supabase.co/storage/v1/object/upload/sign/ur-heart-media/users/123/moments/slot_1.webp?token=test_token" == put_url

    public_url = service.get_public_cdn_url("users/123/moments/slot_1.webp")
    assert "https://test-sub.supabase.co/storage/v1/object/public/ur-heart-media/users/123/moments/slot_1.webp" == public_url


@pytest.mark.asyncio
async def test_unified_storage_fallback(monkeypatch):
    """Verify UnifiedStorageService chooses Supabase when R2 is unconfigured."""
    from unittest.mock import MagicMock
    import httpx

    supabase = SupabaseStorageService(
        supabase_url="https://fallback.supabase.co",
        service_role_key="test_key",
    )
    r2 = CloudflareR2StorageService(account_id="", access_key_id="", secret_access_key="")
    unified = UnifiedStorageService(r2_service=r2, supabase_service=supabase)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "url": "/object/upload/sign/ur-heart-media/test_key.webp?token=test_token"
    }
    monkeypatch.setattr(httpx.Client, "post", lambda self, url, headers=None, json=None: mock_resp)

    put_url = unified.generate_presigned_put_url("test_key.webp")
    assert "fallback.supabase.co" in put_url


@pytest.mark.asyncio
async def test_email_service_fallback():
    """Verify EmailService waterfall gracefully falls back to sandbox in test environment."""
    email_srv = EmailService()
    # With placeholder keys, it should fall back to mock sandbox and return True
    success = await email_srv.send_email(
        to_email="seeker@example.com",
        subject="Sacred Test",
        html_content="<p>Test</p>",
    )
    assert success is True

    magic_ok = await email_srv.send_magic_link("seeker@example.com", "https://urheart.app/auth/verify?token=123")
    assert magic_ok is True


@pytest.mark.asyncio
async def test_ai_service_cluster_failover():
    """Verify AIService cascades through engines and provides graceful fallback when keys are placeholders."""
    ai_srv = AIService()
    res = await ai_srv.generate_completion(
        messages=[{"role": "user", "content": "Hello Wingman"}]
    )
    assert "engine" in res
    assert "content" in res

    # Whisper voice transcription test in sandbox mode
    whisper_res = await ai_srv.transcribe_voice_spark(b"fake_audio_bytes")
    assert whisper_res["success"] is True
    assert "text" in whisper_res


@pytest.mark.asyncio
async def test_stripe_signature_verification(monkeypatch):
    """Verify Stripe HMAC-SHA256 signature verification logic."""
    secret = "test_stripe_webhook_secret_key"
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", secret)
    raw_body = b'{"type": "checkout.session.completed"}'
    import time
    ts = str(int(time.time()))
    signed_payload = f"{ts}.".encode("utf-8") + raw_body
    sig = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    sig_header = f"t={ts},v1={sig}"

    is_valid = payment_service.verify_stripe_signature(raw_body, sig_header)
    assert is_valid is True

    is_invalid = payment_service.verify_stripe_signature(raw_body, f"t={ts},v1=bad_sig")
    assert is_invalid is False


@pytest.mark.asyncio
async def test_revenuecat_authorization_verification(monkeypatch):
    """Verify RevenueCat Bearer token verification."""
    secret = "test_revenuecat_webhook_secret_key"
    monkeypatch.setattr(settings, "REVENUECAT_WEBHOOK_SECRET", secret)
    auth_header = f"Bearer {secret}"

    assert payment_service.verify_revenuecat_authorization(auth_header) is True
    assert payment_service.verify_revenuecat_authorization("Bearer invalid_token") is False


@pytest.mark.asyncio
async def test_superadmin_sentinel_gate(monkeypatch):
    """Verify Superadmin Sentinel Gate denies unauthorized requests and permits valid key."""
    test_key = "test_sentinel_secret_key_2026"
    monkeypatch.setattr(settings, "SUPERADMIN_SECRET_KEY", test_key)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Without key -> 403
        resp_forbidden = await ac.get("/api/v1/sentinel")
        assert resp_forbidden.status_code == 403

        # With secret key -> 200 with diagnostics
        resp_ok = await ac.get(
            "/api/v1/sentinel",
            headers={"X-Superadmin-Key": test_key},
        )
        assert resp_ok.status_code == 200
        data = resp_ok.json()
        assert "services" in data
        assert "supabase" in data["services"]


def test_stripe_amount_currency_conversions():
    """Verify Stripe integer subunits to Decimal major units across standard, zero-decimal, and 3-decimal currencies."""
    from backend.app.api.v1.endpoints.payments import convert_stripe_amount
    # Standard 2-decimal (INR, USD, EUR)
    assert convert_stripe_amount(19900, "INR") == Decimal("199.00")
    assert convert_stripe_amount(2500, "USD") == Decimal("25.00")
    # Zero-decimal (JPY, KRW, VND)
    assert convert_stripe_amount(500, "JPY") == Decimal("500")
    assert convert_stripe_amount(15000, "KRW") == Decimal("15000")
    # 3-decimal (BHD, KWD)
    assert convert_stripe_amount(1500, "KWD") == Decimal("1.500")
    # Special case: UGX (Stripe API represents 5 UGX as 500, divided by 100)
    assert convert_stripe_amount(500, "UGX") == Decimal("5.00")
    # None
    assert convert_stripe_amount(None, "USD") is None


def test_eva_bio_non_whitespace_validation():
    """Verify EvaBioPolishRequest rejects whitespace-only or sparse whitespace strings."""
    from backend.app.schemas.eva import EvaBioPolishRequest
    import pydantic

    # 10 spaces should fail
    with pytest.raises(pydantic.ValidationError):
        EvaBioPolishRequest(raw_bio="          ")

    # 2 letters with spaces in between should fail (< 10 non-whitespace chars)
    with pytest.raises(pydantic.ValidationError):
        EvaBioPolishRequest(raw_bio="a         b")

    # Valid bio with >= 10 non-whitespace characters should succeed
    valid = EvaBioPolishRequest(raw_bio="Mindful connection seeker")
    assert valid.raw_bio == "Mindful connection seeker"


@pytest.mark.asyncio
async def test_sentinel_rejects_placeholder_groq_whisper(monkeypatch):
    """Verify Sentinel diagnostic flags placeholder Groq Whisper keys as inactive."""
    monkeypatch.setattr(settings, "SUPERADMIN_SECRET_KEY", "test_key")
    monkeypatch.setattr(settings, "GROQ_API_KEY", "placeholder_groq_api_key")
    monkeypatch.setattr(settings, "GROQ_VOICE_API_KEY", "")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/sentinel", headers={"X-Superadmin-Key": "test_key"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["services"]["groq_whisper"] is False
        assert data["services"]["groq_lpu"] is False


def test_supabase_storage_wraps_network_errors(monkeypatch):
    """Verify SupabaseStorageService wraps httpx.RequestError into SanctuaryException."""
    from backend.app.services.storage_service import SupabaseStorageService
    from backend.app.core.exceptions import SanctuaryException
    import httpx

    service = SupabaseStorageService(
        supabase_url="https://xyz.supabase.co",
        service_role_key="service_role_key",
        bucket_name="sanctuary-media",
    )

    def mock_post_raise(*args, **kwargs):
        raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr(httpx.Client, "post", mock_post_raise)
    with pytest.raises(SanctuaryException) as exc_info:
        service.put_object_bytes("test.webp", b"test")
    assert exc_info.value.status_code == 503
    assert exc_info.value.error_code == "STORAGE_PUT_FAILED"

    def mock_req_raise(*args, **kwargs):
        raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr(httpx.Client, "request", mock_req_raise)
    with pytest.raises(SanctuaryException) as exc_info:
        service.delete_object("test.webp")
    assert exc_info.value.status_code == 503
    assert exc_info.value.error_code == "STORAGE_DELETE_FAILED"


@pytest.mark.asyncio
async def test_ai_service_call_gemini_max_tokens(monkeypatch):
    """Verify AIService._call_gemini forwards max_tokens in generationConfig."""
    import httpx
    from unittest.mock import MagicMock
    from backend.app.services.ai_service import AIService

    ai = AIService()
    ai.gemini_api_key = "test_gemini_key"

    captured_payload = {}

    async def mock_post(self, url, headers=None, json=None, timeout=None):
        nonlocal captured_payload
        captured_payload = json
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "candidates": [
                {"content": {"parts": [{"text": "Gemini response text"}]}}
            ]
        }
        return mock_resp

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    result = await ai._call_gemini(
        messages=[{"role": "user", "content": "Test prompt"}],
        temperature=0.7,
        max_tokens=256,
    )

    assert result == "Gemini response text"
    assert captured_payload["generationConfig"]["maxOutputTokens"] == 256
    assert captured_payload["generationConfig"]["temperature"] == 0.7


@pytest.mark.asyncio
async def test_payment_service_rejects_negative_amount():
    """Verify PaymentService.process_successful_payment rejects negative gross amounts with 400."""
    from unittest.mock import AsyncMock
    from backend.app.core.exceptions import SanctuaryException
    import uuid

    mock_session = AsyncMock()
    fake_user_id = uuid.uuid4()

    with pytest.raises(SanctuaryException) as exc_info:
        await payment_service.process_successful_payment(
            user_id=fake_user_id,
            order_id="order_test_123",
            payment_id="pay_neg_123",
            product_identifier="com.urheart.sparks.10",
            amount_gross=Decimal("-10.00"),
            session=mock_session,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.error_code == "INVALID_PAYMENT_AMOUNT"


