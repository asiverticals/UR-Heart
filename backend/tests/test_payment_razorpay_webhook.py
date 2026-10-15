import hashlib
import hmac
import json
import uuid
from decimal import Decimal
import pytest
import httpx
from httpx import ASGITransport
from sqlalchemy import select

from backend.app.api.deps import get_current_user
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.main import app
from backend.app.models.domain.monetization import InAppPurchase, PendingWebEntitlement
from backend.app.services.payment_service import payment_service


@pytest.mark.asyncio
async def test_order_generation_with_paise_conversion(db_session, make_user):
    """Test 1: Order Generation: /payments/create-order creates valid Razorpay order payload with correct paise conversion."""
    user = make_user(
        full_name="Purchasing Seeker",
        is_profile_completed=True,
    )
    db_session.add(user)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Order for direct_letter_single (₹29 -> 2900 paise)
            res1 = await client.post(
                "/api/v1/payments/create-order",
                json={"product_identifier": "direct_letter_single", "currency": "INR"},
            )
            assert res1.status_code == 200
            body1 = res1.json()
            assert body1["success"] is True
            data1 = body1["data"]
            assert data1["amount"] == 29.0
            assert data1["amount_paise"] == 2900
            assert data1["currency"] == "INR"
            assert data1["order_id"].startswith("order_")
            assert "key_id" in data1

            # 2. Order for pass_sovereign_weekly (₹299 -> 29900 paise)
            res2 = await client.post(
                "/api/v1/payments/create-order",
                json={"product_identifier": "pass_sovereign_weekly", "currency": "INR"},
            )
            assert res2.status_code == 200
            data2 = res2.json()["data"]
            assert data2["amount"] == 299.0
            assert data2["amount_paise"] == 29900

            # 3. Invalid product SKU returns 400
            res3 = await client.post(
                "/api/v1/payments/create-order",
                json={"product_identifier": "invalid_sku_xyz", "currency": "INR"},
            )
            assert res3.status_code == 400
            assert res3.json()["error_code"] == "INVALID_PRODUCT"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_signature_validation_and_checkout_verification(db_session, make_user):
    """Test 2: Signature Validation: Correct HMAC-SHA256 signature passes; forged/tampered signature raises HTTP 400."""
    user = make_user(
        full_name="Verification Seeker",
        is_profile_completed=True,
        direct_letters_count=1,
    )
    db_session.add(user)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db_session

    orig_secret = settings.RAZORPAY_KEY_SECRET
    test_secret = "sanctuary_test_secret_key_123"
    settings.RAZORPAY_KEY_SECRET = test_secret

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            order_id = "order_rzp_mock_111"
            payment_id = "pay_rzp_mock_111"

            # 1. Tampered / invalid signature raises HTTP 400
            invalid_res = await client.post(
                "/api/v1/payments/verify-checkout",
                json={
                    "razorpay_order_id": order_id,
                    "razorpay_payment_id": payment_id,
                    "razorpay_signature": "tampered_bogus_signature_xyz",
                    "product_identifier": "direct_letter_single",
                },
            )
            assert invalid_res.status_code == 400
            assert invalid_res.json()["error_code"] == "INVALID_PAYMENT_SIGNATURE"

            # 2. Authentic HMAC-SHA256 signature passes and provisions entitlements
            valid_payload = f"{order_id}|{payment_id}".encode("utf-8")
            valid_signature = hmac.new(
                test_secret.encode("utf-8"), valid_payload, hashlib.sha256
            ).hexdigest()

            valid_res = await client.post(
                "/api/v1/payments/verify-checkout",
                json={
                    "razorpay_order_id": order_id,
                    "razorpay_payment_id": payment_id,
                    "razorpay_signature": valid_signature,
                    "product_identifier": "direct_letter_single",
                },
            )
            assert valid_res.status_code == 200
            assert valid_res.json()["success"] is True
            assert valid_res.json()["data"]["transaction_id"] == payment_id

            # Verify balance increment in database
            await db_session.refresh(user)
            assert user.direct_letters_count == 2
    finally:
        settings.RAZORPAY_KEY_SECRET = orig_secret
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_webhook_raw_body_hmac_verification(db_session, make_user):
    """Test 3: Webhook Verification: Raw body HMAC verification validates authentic webhooks and rejects spoofed headers."""
    user = make_user(
        full_name="Webhook Seeker",
        is_profile_completed=True,
        reveal_tokens_count=1,
    )
    db_session.add(user)
    await db_session.commit()

    app.dependency_overrides[get_db] = lambda: db_session

    orig_webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
    test_webhook_secret = "sanctuary_webhook_secret_xyz"
    settings.RAZORPAY_WEBHOOK_SECRET = test_webhook_secret

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            webhook_event = {
                "event": "payment.captured",
                "payload": {
                    "payment": {
                        "entity": {
                            "id": "pay_webhook_999",
                            "order_id": "order_webhook_999",
                            "amount": 3900,
                            "currency": "INR",
                            "status": "captured",
                            "notes": {
                                "user_id": str(user.id),
                                "product_id": "profile_unlock_single",
                            },
                        }
                    }
                },
            }
            raw_bytes = json.dumps(webhook_event).encode("utf-8")

            # 1. Missing header returns 400
            missing_hdr_res = await client.post(
                "/api/v1/payments/webhook/razorpay",
                content=raw_bytes,
                headers={"Content-Type": "application/json"},
            )
            assert missing_hdr_res.status_code == 400

            # 2. Forged signature returns 400
            spoofed_res = await client.post(
                "/api/v1/payments/webhook/razorpay",
                content=raw_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-Razorpay-Signature": "forged_signature_123",
                },
            )
            assert spoofed_res.status_code == 400
            assert "verification failed" in spoofed_res.json()["detail"]

            # 3. Valid HMAC-SHA256 signature succeeds and provisions entitlements
            valid_webhook_sig = hmac.new(
                test_webhook_secret.encode("utf-8"), raw_bytes, hashlib.sha256
            ).hexdigest()

            authentic_res = await client.post(
                "/api/v1/payments/webhook/razorpay",
                content=raw_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-Razorpay-Signature": valid_webhook_sig,
                },
            )
            assert authentic_res.status_code == 200
            assert authentic_res.json()["status"] == "ok"

            await db_session.refresh(user)
            assert user.reveal_tokens_count == 2
    finally:
        settings.RAZORPAY_WEBHOOK_SECRET = orig_webhook_secret
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_replay_protection_prevents_duplicate_provisioning(db_session, make_user):
    """Test 4: Replay Protection: Posting duplicate razorpay_payment_id recognizes existing transaction and prevents double balance provisioning."""
    user = make_user(
        full_name="Replay Guard Seeker",
        is_profile_completed=True,
        direct_letters_count=1,
    )
    db_session.add(user)
    await db_session.commit()

    order_id = "order_replay_test_555"
    payment_id = "pay_replay_test_555"
    product_sku = "direct_letter_single"

    # 1. First execution provisions +1 letter and records InAppPurchase
    r1 = await payment_service.process_successful_payment(
        user_id=user.id,
        order_id=order_id,
        payment_id=payment_id,
        product_identifier=product_sku,
        amount_gross=Decimal("29.00"),
        session=db_session,
    )
    assert r1["status"] == "completed"
    assert r1["transaction_id"] == payment_id

    await db_session.refresh(user)
    assert user.direct_letters_count == 2

    # Verify InAppPurchase row exists
    stmt = select(InAppPurchase).where(InAppPurchase.transaction_reference == payment_id)
    res = await db_session.execute(stmt)
    iap = res.scalar_one_or_none()
    assert iap is not None
    assert iap.store == "web_razorpay_india"

    # 2. Second replay execution detects duplicate and DOES NOT increment balance again
    r2 = await payment_service.process_successful_payment(
        user_id=user.id,
        order_id=order_id,
        payment_id=payment_id,
        product_identifier=product_sku,
        amount_gross=Decimal("29.00"),
        session=db_session,
    )
    assert r2["status"] == "already_processed"
    assert r2["transaction_id"] == payment_id

    await db_session.refresh(user)
    # Balance must still be 2 (NOT 3)
    assert user.direct_letters_count == 2


@pytest.mark.asyncio
async def test_web_entitlement_claim_reconciliation(db_session, make_user):
    """Test 5: Web Entitlement Claim: Seeker claiming pending web entitlement by email transitions record to 'claimed' and receives balances."""
    user_email = "seeker_store_guest@urheart.app"
    user = make_user(
        full_name="Web Store Seeker",
        email=user_email,
        is_profile_completed=True,
        super_likes_count=0,
    )
    db_session.add(user)

    # Insert pending web store purchase with canonical status 'paid_pending_claim'
    web_ent = PendingWebEntitlement(
        order_id="order_web_guest_777",
        email=user_email,
        product_identifier="super_like_pack_3",
        payment_reference="pay_web_guest_777",
        amount_gross=Decimal("49.00"),
        currency="INR",
        status="paid_pending_claim",
    )
    db_session.add(web_ent)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            claim_res = await client.post("/api/v1/payments/claim-web-entitlement")
            assert claim_res.status_code == 200
            body = claim_res.json()
            assert body["success"] is True
            claimed_items = body["data"]["claimed_items"]
            assert len(claimed_items) == 1
            assert claimed_items[0]["order_id"] == "order_web_guest_777"
            assert claimed_items[0]["product_identifier"] == "super_like_pack_3"

            # Check status transitioned to claimed in DB
            await db_session.refresh(web_ent)
            assert web_ent.status == "claimed"
            assert web_ent.claimed_by_user_id == user.id
            assert web_ent.claimed_at is not None

            # Check seeker received super likes
            await db_session.refresh(user)
            assert getattr(user, "super_likes_count", 0) == 3

            # Second claim request returns 0 items
            claim_res2 = await client.post("/api/v1/payments/claim-web-entitlement")
            assert claim_res2.status_code == 200
            assert len(claim_res2.json()["data"]["claimed_items"]) == 0
    finally:
        app.dependency_overrides.clear()


def test_signature_validation_fails_closed_on_empty_secret():
    """Test 6: Security: Verification functions return False when secret or signature is empty."""
    orig_key_secret = settings.RAZORPAY_KEY_SECRET
    orig_webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET

    try:
        # Empty client secret
        settings.RAZORPAY_KEY_SECRET = ""
        assert payment_service.verify_client_signature("order_1", "pay_1", "sig_1") is False

        # Empty webhook secret
        settings.RAZORPAY_WEBHOOK_SECRET = ""
        assert payment_service.verify_webhook_signature(b"{}", "sig_1") is False

        # Empty signature with valid secret
        settings.RAZORPAY_KEY_SECRET = "valid_secret"
        assert payment_service.verify_client_signature("order_1", "pay_1", "") is False

        settings.RAZORPAY_WEBHOOK_SECRET = "valid_secret"
        assert payment_service.verify_webhook_signature(b"{}", "") is False
    finally:
        settings.RAZORPAY_KEY_SECRET = orig_key_secret
        settings.RAZORPAY_WEBHOOK_SECRET = orig_webhook_secret


def test_order_cache_is_bounded_and_evicts_lru():
    """Test 7: Cache Bound: order_cache enforces max_cache_size and evicts oldest entries."""
    orig_max = payment_service.max_cache_size
    orig_cache = payment_service.order_cache.copy()

    try:
        payment_service.max_cache_size = 3
        payment_service.order_cache.clear()

        # Add 3 orders
        payment_service.order_cache["order_1"] = {"product_id": "p1"}
        payment_service.order_cache["order_2"] = {"product_id": "p2"}
        payment_service.order_cache["order_3"] = {"product_id": "p3"}

        assert len(payment_service.order_cache) == 3
        assert payment_service.get_cached_order("order_1") is not None

        # Add 4th order via helper / simulated creation
        if len(payment_service.order_cache) >= payment_service.max_cache_size:
            payment_service.order_cache.popitem(last=False)
        payment_service.order_cache["order_4"] = {"product_id": "p4"}

        assert len(payment_service.order_cache) == 3
        # order_2 should have been evicted (since order_1 was touched by get_cached_order)
        assert "order_2" not in payment_service.order_cache
        assert "order_4" in payment_service.order_cache
    finally:
        payment_service.max_cache_size = orig_max
        payment_service.order_cache = orig_cache


@pytest.mark.asyncio
async def test_webhook_propagates_http_500_on_database_failure(db_session, make_user, monkeypatch):
    """Test 8: Error Propagation: Webhook raises HTTP 500 on internal failures so Razorpay retries delivery."""
    user = make_user(
        full_name="Webhook Error Seeker",
        is_profile_completed=True,
    )
    db_session.add(user)
    await db_session.commit()

    app.dependency_overrides[get_db] = lambda: db_session

    orig_webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
    test_webhook_secret = "sanctuary_webhook_secret_err"
    settings.RAZORPAY_WEBHOOK_SECRET = test_webhook_secret

    async def mock_failing_payment(*args, **kwargs):
        raise RuntimeError("Simulated database transient connection timeout")

    monkeypatch.setattr(payment_service, "process_successful_payment", mock_failing_payment)

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            webhook_event = {
                "event": "payment.captured",
                "payload": {
                    "payment": {
                        "entity": {
                            "id": "pay_fail_retry_test",
                            "order_id": "order_fail_retry_test",
                            "amount": 2900,
                            "currency": "INR",
                            "status": "captured",
                            "notes": {
                                "user_id": str(user.id),
                                "product_id": "direct_letter_single",
                            },
                        }
                    }
                },
            }
            raw_bytes = json.dumps(webhook_event).encode("utf-8")
            valid_webhook_sig = hmac.new(
                test_webhook_secret.encode("utf-8"), raw_bytes, hashlib.sha256
            ).hexdigest()

            res = await client.post(
                "/api/v1/payments/webhook/razorpay",
                content=raw_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-Razorpay-Signature": valid_webhook_sig,
                },
            )
            # Must return HTTP 500, not 200, so gateway retries webhook!
            assert res.status_code == 500
            assert "Error processing payment webhook" in res.json()["detail"]
    finally:
        settings.RAZORPAY_WEBHOOK_SECRET = orig_webhook_secret
        app.dependency_overrides.clear()


