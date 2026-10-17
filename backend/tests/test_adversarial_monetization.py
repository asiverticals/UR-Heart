import hashlib
import hmac
import json
from decimal import Decimal
import httpx
from httpx import ASGITransport
import pytest
from sqlalchemy import select

from backend.app.api.deps import get_current_user
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.main import app
from backend.app.models.domain.monetization import InAppPurchase, PendingWebEntitlement
from backend.app.services.payment_service import payment_service


@pytest.mark.asyncio
async def test_webhook_replay_after_web_claim_prevents_double_crediting(db_session, make_user):
    """FIND-PAY-01: Replaying a validly signed Razorpay webhook after a pending web entitlement
    has already been claimed must NOT double-provision entitlements or create duplicate purchases."""
    user = make_user(email="seeker_replay@urheart.app", swipes_remaining=25, is_profile_completed=True)
    db_session.add(user)
    await db_session.commit()

    order_id = "order_rep_test_001"
    payment_id = "pay_rep_test_001"

    # 1. Existing pending entitlement claimed by user
    pending = PendingWebEntitlement(
        order_id=order_id,
        email=user.email,
        product_identifier="pass_weekly",
        payment_reference=payment_id,
        amount_gross=Decimal("49.00"),
        currency="INR",
        status="paid_pending_claim",
    )
    db_session.add(pending)
    await db_session.commit()

    # User claims the entitlement
    claimed = await payment_service.claim_web_entitlements(user=user, session=db_session)
    assert len(claimed) == 1
    await db_session.refresh(user)
    initial_swipes = user.swipes_remaining

    # Assert InAppPurchase record was created on claim to seal cross-table idempotency
    iap_res = await db_session.execute(
        select(InAppPurchase).where(InAppPurchase.transaction_reference == payment_id)
    )
    iap = iap_res.scalar_one_or_none()
    assert iap is not None
    assert iap.product_identifier == "pass_weekly"

    # 2. Authentic webhook for the same payment is replayed
    orig_secret = settings.RAZORPAY_WEBHOOK_SECRET
    test_secret = "test_webhook_secret_key_123"
    settings.RAZORPAY_WEBHOOK_SECRET = test_secret
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            webhook_event = {
                "event": "payment.captured",
                "payload": {
                    "payment": {
                        "entity": {
                            "id": payment_id,
                            "order_id": order_id,
                            "amount": 4900,
                            "currency": "INR",
                            "status": "captured",
                            "notes": {
                                "email": user.email,
                                "product_id": "pass_weekly",
                            },
                        }
                    }
                },
            }
            raw_body = json.dumps(webhook_event).encode("utf-8")
            sig = hmac.new(test_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

            res = await client.post(
                "/api/v1/payments/webhook/razorpay",
                content=raw_body,
                headers={"Content-Type": "application/json", "X-Razorpay-Signature": sig},
            )
            assert res.status_code == 200

            # 3. Assert user balance was NOT doubled
            await db_session.refresh(user)
            assert user.swipes_remaining == initial_swipes
    finally:
        settings.RAZORPAY_WEBHOOK_SECRET = orig_secret
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_verify_checkout_prevents_unauthorized_user_claiming_guest_order(db_session, make_user):
    """FIND-PAY-02: An authenticated user must not be able to steal a guest order created by
    another email, and guest checkout verification must strictly validate verified email."""
    alice = make_user(email="alice@urheart.app", full_name="Alice Seeker", is_profile_completed=True)
    attacker = make_user(email="attacker@urheart.app", full_name="Attacker", is_profile_completed=True)
    db_session.add_all([alice, attacker])
    await db_session.commit()

    order_id = "order_guest_steal_001"
    payment_service.order_cache[order_id] = {
        "order_id": order_id,
        "product_id": "pass_infinity",
        "user_id": None,
        "email": "alice@urheart.app",
        "amount_inr": 1499.0,
        "amount_paise": 149900,
    }

    orig_secret = settings.RAZORPAY_KEY_SECRET
    settings.RAZORPAY_KEY_SECRET = "test_key_secret_32b"
    payment_id = "pay_guest_steal_001"
    raw_sig = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        f"{order_id}|{payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()

    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Attacker attempts to claim Alice's guest order -> 403 Forbidden
            app.dependency_overrides[get_current_user] = lambda: attacker
            resp_attacker = await client.post(
                "/api/v1/payments/verify-checkout",
                json={
                    "razorpay_order_id": order_id,
                    "razorpay_payment_id": payment_id,
                    "razorpay_signature": raw_sig,
                    "product_identifier": "pass_infinity",
                },
            )
            assert resp_attacker.status_code == 403
            assert resp_attacker.json()["error_code"] == "ORDER_OWNERSHIP_MISMATCH"

            # 2. Legitimate guest buyer (Alice) verifies order -> 200 OK (str(None) bug fixed)
            app.dependency_overrides[get_current_user] = lambda: alice
            resp_alice = await client.post(
                "/api/v1/payments/verify-checkout",
                json={
                    "razorpay_order_id": order_id,
                    "razorpay_payment_id": payment_id,
                    "razorpay_signature": raw_sig,
                    "product_identifier": "pass_infinity",
                },
            )
            assert resp_alice.status_code == 200
            assert resp_alice.json()["success"] is True
    finally:
        settings.RAZORPAY_KEY_SECRET = orig_secret
        payment_service.order_cache.pop(order_id, None)
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_webhook_rejects_underpayment_price_tampering(db_session, make_user):
    """FIND-PAY-03: Webhook must reject payments where the paid amount is less than
    the authoritative catalog price for the requested product SKU."""
    user = make_user(full_name="Underpayer Seeker", is_profile_completed=True)
    db_session.add(user)
    await db_session.commit()

    orig_secret = settings.RAZORPAY_WEBHOOK_SECRET
    settings.RAZORPAY_WEBHOOK_SECRET = "test_webhook_secret_key_123"
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # pass_infinity catalog price is ₹1,499.00 (149900 paise). Attacker pays 100 paise (₹1.00).
            webhook_event = {
                "event": "payment.captured",
                "payload": {
                    "payment": {
                        "entity": {
                            "id": "pay_underpay_attack_001",
                            "order_id": "order_underpay_attack_001",
                            "amount": 100,  # ₹1.00 instead of ₹1,499.00
                            "currency": "INR",
                            "status": "captured",
                            "notes": {
                                "user_id": str(user.id),
                                "product_id": "pass_infinity",
                            },
                        }
                    }
                },
            }
            raw_body = json.dumps(webhook_event).encode("utf-8")
            sig = hmac.new(settings.RAZORPAY_WEBHOOK_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()

            res = await client.post(
                "/api/v1/payments/webhook/razorpay",
                content=raw_body,
                headers={"Content-Type": "application/json", "X-Razorpay-Signature": sig},
            )
            # Must reject underpayment and NOT provision lifetime pass
            assert res.status_code == 200
            assert res.json().get("status") == "ignored_underpayment"

            await db_session.refresh(user)
            assert getattr(user, "has_unlimited_swipes", False) is False
            assert user.subscription_tier != "lifetime"
    finally:
        settings.RAZORPAY_WEBHOOK_SECRET = orig_secret
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_concurrent_guest_webhooks_handle_integrity_error_without_500(db_session):
    """FIND-PAY-04: Duplicate or concurrent webhooks inserting PendingWebEntitlement must
    gracefully handle unique constraint collisions and acknowledge with 200 OK, not 500."""
    orig_secret = settings.RAZORPAY_WEBHOOK_SECRET
    settings.RAZORPAY_WEBHOOK_SECRET = "test_webhook_secret_key_123"
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            webhook_event = {
                "event": "payment.captured",
                "payload": {
                    "payment": {
                        "entity": {
                            "id": "pay_concurrent_dup_001",
                            "order_id": "order_concurrent_dup_001",
                            "amount": 4900,
                            "currency": "INR",
                            "status": "captured",
                            "notes": {
                                "email": "guest_dup@urheart.app",
                                "product_id": "pass_weekly",
                            },
                        }
                    }
                },
            }
            raw_body = json.dumps(webhook_event).encode("utf-8")
            sig = hmac.new(settings.RAZORPAY_WEBHOOK_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()

            # First delivery succeeds
            res1 = await client.post(
                "/api/v1/payments/webhook/razorpay",
                content=raw_body,
                headers={"Content-Type": "application/json", "X-Razorpay-Signature": sig},
            )
            assert res1.status_code == 200
            assert res1.json()["status"] == "ok"

            # Immediate re-delivery must return 200 OK (idempotent acknowledge), NEVER 500
            res2 = await client.post(
                "/api/v1/payments/webhook/razorpay",
                content=raw_body,
                headers={"Content-Type": "application/json", "X-Razorpay-Signature": sig},
            )
            assert res2.status_code == 200
            assert res2.json()["status"] == "ok"
    finally:
        settings.RAZORPAY_WEBHOOK_SECRET = orig_secret
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_claimed_web_entitlements_receive_advertised_20_percent_bonus(db_session, make_user):
    """FIND-PAY-05: Claimed web store entitlements must provision with is_web_store=True
    to deliver the advertised +20% bonus perks."""
    user = make_user(
        email="bonus_test@urheart.app",
        swipes_remaining=0,
        direct_letters_count=0,
        is_profile_completed=True,
    )
    db_session.add(user)
    await db_session.commit()

    pending = PendingWebEntitlement(
        order_id="order_bonus_test_001",
        email=user.email,
        product_identifier="pass_weekly",
        payment_reference="pay_bonus_test_001",
        amount_gross=Decimal("49.00"),
        currency="INR",
        status="paid_pending_claim",
    )
    db_session.add(pending)
    await db_session.commit()

    claimed = await payment_service.claim_web_entitlements(user=user, session=db_session)
    assert len(claimed) == 1

    await db_session.refresh(user)
    # Advertised web store weekly pass yield is 120 swipes (100 base + 20 web bonus)
    assert user.swipes_remaining == 120


@pytest.mark.asyncio
async def test_in_app_purchase_verification_binds_amount_to_catalog(db_session, make_user):
    """FIND-PAY-06: Mobile IAP verification must bind transaction ledger amount to authoritative
    server-side catalog pricing, preventing client amount fabrication."""
    user = make_user(full_name="IAP Seeker", is_profile_completed=True)
    db_session.add(user)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/payments/verify-in-app-purchase",
                json={
                    "order_id": "google_order_12345",
                    "product_identifier": "pass_weekly",
                    "purchase_token": "valid_google_token_1234567890",
                    "amount_gross": 0.00,  # Fabricated by client
                },
            )
            assert resp.status_code == 200

            # Verify InAppPurchase row in DB was bounded to catalog price (₹49.00), not ₹0.00
            res = await db_session.execute(
                select(InAppPurchase).where(
                    InAppPurchase.transaction_reference == "valid_google_token_1234567890"
                )
            )
            iap = res.scalar_one_or_none()
            assert iap is not None
            assert iap.amount_gross == Decimal("49.00")
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_case_insensitive_email_reconciliation_for_web_entitlements(db_session, make_user):
    """FIND-PAY-07: Entitlement matching must be case-insensitive to ensure seekers claiming
    with differing email case variations receive their purchases."""
    user = make_user(email="alice.seeker@urheart.app", swipes_remaining=0, is_profile_completed=True)
    db_session.add(user)
    await db_session.commit()

    pending = PendingWebEntitlement(
        order_id="order_case_test_001",
        email="Alice.Seeker@UrHeart.App",  # Mixed case
        product_identifier="pass_weekly",
        payment_reference="pay_case_test_001",
        amount_gross=Decimal("49.00"),
        currency="INR",
        status="paid_pending_claim",
    )
    db_session.add(pending)
    await db_session.commit()

    claimed = await payment_service.claim_web_entitlements(user=user, session=db_session)
    assert len(claimed) == 1
    assert claimed[0]["order_id"] == "order_case_test_001"

    await db_session.refresh(pending)
    assert pending.status == "claimed"
    assert pending.claimed_by_user_id == user.id


@pytest.mark.asyncio
async def test_claim_web_entitlement_rate_limited(db_session, make_user):
    """FIND-PAY-08: POST /api/v1/payments/claim-web-entitlement enforces rate limiting (10/minute)."""
    user = make_user(email="ratelimit_seeker@urheart.app", is_profile_completed=True)
    db_session.add(user)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db_session

    client_ip = "198.51.100.222"
    headers = {"X-Forwarded-For": client_ip}

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # 10 requests allowed under 10/minute limit
            for _ in range(10):
                resp = await client.post("/api/v1/payments/claim-web-entitlement", headers=headers)
                assert resp.status_code == 200

            # 11th request breaches 10/minute rate limit -> 429
            blocked_resp = await client.post("/api/v1/payments/claim-web-entitlement", headers=headers)
            assert blocked_resp.status_code == 429
            data = blocked_resp.json()
            assert data["error_code"] == "RATE_LIMIT_EXCEEDED"
    finally:
        app.dependency_overrides.clear()
