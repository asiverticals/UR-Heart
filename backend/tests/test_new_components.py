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


@pytest.mark.asyncio
async def test_user_blocking_endpoints(db_session, make_user):
    """Verify POST /api/v1/users/{id}/block, GET /api/v1/users/blocked, and DELETE /api/v1/users/{id}/block."""
    from backend.app.api.deps import get_current_user, get_db

    user1 = make_user(full_name="Blocker User", is_profile_completed=True)
    user2 = make_user(full_name="Target User", is_profile_completed=True)
    db_session.add_all([user1, user2])
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user1
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Block user2
            block_resp = await client.post(
                f"/api/v1/users/{user2.id}/block",
                json={"reason": "abusive_behavior"},
            )
            assert block_resp.status_code == 200
            assert block_resp.json()["data"]["blocked"] is True

            # 2. Cannot block self
            self_resp = await client.post(f"/api/v1/users/{user1.id}/block")
            assert self_resp.status_code == 400

            # 3. List blocked users
            list_resp = await client.get("/api/v1/users/blocked")
            assert list_resp.status_code == 200
            assert str(user2.id) in list_resp.json()["data"]

            # 4. Unblock user2
            unblock_resp = await client.delete(f"/api/v1/users/{user2.id}/block")
            assert unblock_resp.status_code == 200
            assert unblock_resp.json()["data"]["unblocked"] is True
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_legal_statutory_and_emergency_sla(db_session, make_user):
    """Verify 24-hr emergency SLA for NCII/explicit content and statutory disclosure endpoints."""
    from backend.app.api.deps import get_current_user, get_db

    user1 = make_user(full_name="Reporting Seeker", is_profile_completed=True)
    user2 = make_user(full_name="Target Seeker", is_profile_completed=True)
    db_session.add_all([user1, user2])
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user1
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. 24-hr emergency takedown for explicit_content
            g_resp = await client.post(
                "/api/v1/legal/grievance",
                json={
                    "reported_user_id": str(user2.id),
                    "violation_category": "explicit_content",
                    "evidence_text": "NCII emergency takedown request",
                },
            )
            assert g_resp.status_code == 200
            data = g_resp.json()["data"]
            from datetime import datetime
            ack = datetime.fromisoformat(data["acknowledgment_sent_at"])
            due_takedown = datetime.fromisoformat(data["emergency_takedown_due_at"])
            diff_hours = (due_takedown - ack).total_seconds() / 3600
            assert 0 < diff_hours <= 24.0

            due_resolution = datetime.fromisoformat(data["statutory_resolution_due_at"])
            diff_days = (due_resolution - ack).total_seconds() / 86400
            assert 14.0 < diff_days <= 15.0

            # Verify grievance listing returns emergency takedown deadline
            list_resp = await client.get("/api/v1/legal/grievances")
            assert list_resp.status_code == 200
            list_items = list_resp.json()["data"]
            assert len(list_items) >= 1
            matched_item = next(i for i in list_items if i["dossier_reference_id"] == data["dossier_reference_id"])
            assert matched_item["emergency_takedown_due_at"] is not None
            assert matched_item["statutory_resolution_due_at"] is not None

            # 2. Statutory disclosures
            terms_resp = await client.get("/api/v1/legal/terms")
            assert terms_resp.status_code == 200
            assert terms_resp.json()["data"]["entity"] == "ASI Verticals Private Limited"

            privacy_resp = await client.get("/api/v1/legal/privacy")
            assert privacy_resp.status_code == 200
            assert len(privacy_resp.json()["data"]["languages_supported"]) >= 10

            griev_officer_resp = await client.get("/api/v1/legal/grievance-officer")
            assert griev_officer_resp.status_code == 200
            assert griev_officer_resp.json()["data"]["emergency_takedown_sla_hours"] == 24

            refund_resp = await client.get("/api/v1/legal/refund-policy")
            assert refund_resp.status_code == 200

            # 3. Consent record audit log
            consent_resp = await client.post(
                "/api/v1/legal/consent-record",
                json={
                    "consent_purpose_id": "purpose_dpdp_onboarding_v1",
                    "installation_uuid": "hw_install_test_123",
                },
            )
            assert consent_resp.status_code == 200
            assert consent_resp.json()["data"]["recorded"] is True

            # 4. Reject empty or whitespace consent_purpose_id (Issue #2)
            empty_resp = await client.post(
                "/api/v1/legal/consent-record",
                json={
                    "consent_purpose_id": "   ",
                    "installation_uuid": "hw_install_test_123",
                },
            )
            assert empty_resp.status_code == 422
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)



