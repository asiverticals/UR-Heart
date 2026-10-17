import uuid
from datetime import date
import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings, validate_production_secrets
from backend.app.core.database import get_db
from backend.app.core.exceptions import SanctuaryException
from backend.app.main import app
from backend.app.models.domain.legal import BlockedUser
from backend.app.models.domain.match_and_chat import Match
from backend.app.models.domain.user import User
from backend.app.services.payment_service import payment_service
from backend.app.api.deps import get_current_user


@pytest.mark.asyncio
async def test_user_blocking_with_active_match_satisfies_constraint(db_session: AsyncSession, make_user):
    """Assert blocking a user with an active match severs match with closure_status='unmatched' without 500 error."""
    # Ensure ordered IDs for u1 < u2
    uid1 = uuid.uuid4()
    uid2 = uuid.uuid4()
    if uid1 > uid2:
        uid1, uid2 = uid2, uid1

    user1 = make_user(id=uid1, full_name="Seeker One", is_profile_completed=True)
    user2 = make_user(id=uid2, full_name="Seeker Two", is_profile_completed=True)
    db_session.add_all([user1, user2])
    await db_session.flush()

    # Create active match
    match = Match(
        id=uuid.uuid4(),
        user1_id=user1.id,
        user2_id=user2.id,
        is_active=True,
        closure_status="active",
    )
    db_session.add(match)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user1
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                f"/api/v1/users/{user2.id}/block",
                json={"reason": "abusive_interaction"},
            )
            # Must succeed with 200 OK (previously crashed with 500 due to chk_matches_closure_status)
            assert resp.status_code == 200
            assert resp.json()["data"]["blocked"] is True

            # Verify Match in DB is severed with correct allowed closure_status
            await db_session.refresh(match)
            assert match.is_active is False
            assert match.closure_status == "unmatched"
            assert match.closure_note == "blocked_by_user"
            assert match.closed_by_user_id == user1.id

            # Verify BlockedUser record exists
            stmt = select(BlockedUser).where(
                BlockedUser.blocker_id == user1.id,
                BlockedUser.blocked_id == user2.id,
            )
            res = await db_session.execute(stmt)
            blocked_rec = res.scalar_one_or_none()
            assert blocked_rec is not None
            assert blocked_rec.reason == "abusive_interaction"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_store_receipt_verification_strict_gating():
    """Assert verify_store_receipt allows dummy tokens only in TESTING mode, rejecting in non-testing."""
    dummy_token = "valid_google_play_purchase_token_12345"

    # In TESTING mode: allowed for test harnesses
    settings.TESTING = True
    assert await payment_service.verify_store_receipt(dummy_token, "test_sku") is True
    assert await payment_service.verify_store_receipt("short", "test_sku") is False

    # In Non-TESTING mode: dummy tokens must be rejected
    settings.TESTING = False
    try:
        assert await payment_service.verify_store_receipt(dummy_token, "test_sku") is False
    finally:
        settings.TESTING = True


@pytest.mark.asyncio
async def test_verify_checkout_rejects_sku_tampering(db_session: AsyncSession, make_user):
    """Assert verify-checkout rejects client-submitted SKU that differs from authoritative order contract."""
    user = make_user(full_name="Purchasing Seeker", is_profile_completed=True)
    db_session.add(user)
    await db_session.commit()

    order_id = "order_test_tamper_123"
    # Pre-cache order contract
    payment_service.order_cache[order_id] = {
        "order_id": order_id,
        "product_id": "sacred_bridge_reveal",
        "user_id": str(user.id),
        "amount_paise": 4900,
        "currency": "INR",
        "status": "created",
    }

    # Generate genuine client signature for the order
    import hmac, hashlib
    orig_key_secret = settings.RAZORPAY_KEY_SECRET
    settings.RAZORPAY_KEY_SECRET = "test_razorpay_secret_key_32b"
    secret = settings.RAZORPAY_KEY_SECRET.encode()
    payment_id = "pay_test_999"
    msg = f"{order_id}|{payment_id}".encode()
    sig = hmac.new(secret, msg, hashlib.sha256).hexdigest()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # Client attempts SKU tampering (buying expensive perk with cheap order)
            resp = await client.post(
                "/api/v1/payments/verify-checkout",
                json={
                    "razorpay_order_id": order_id,
                    "razorpay_payment_id": payment_id,
                    "razorpay_signature": sig,
                    "product_identifier": "unlimited_diamond_boost",
                },
            )
            assert resp.status_code == 400
            assert resp.json()["error_code"] == "SKU_TAMPERING_DETECTED"
    finally:
        settings.RAZORPAY_KEY_SECRET = orig_key_secret
        payment_service.order_cache.pop(order_id, None)
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_verify_checkout_rejects_unknown_order_in_non_test_mode(db_session: AsyncSession, make_user):
    """Assert verify-checkout rejects unknown orders in non-testing mode, preventing fallback SKU trust."""
    user = make_user(full_name="Attacker Seeker", is_profile_completed=True)
    db_session.add(user)
    await db_session.commit()

    order_id = "order_nonexistent_999"
    orig_key_secret = settings.RAZORPAY_KEY_SECRET
    settings.RAZORPAY_KEY_SECRET = "test_razorpay_secret_key_32b"
    secret = settings.RAZORPAY_KEY_SECRET.encode()
    payment_id = "pay_test_888"
    msg = f"{order_id}|{payment_id}".encode()
    import hmac, hashlib
    sig = hmac.new(secret, msg, hashlib.sha256).hexdigest()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db_session

    settings.TESTING = False
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/payments/verify-checkout",
                json={
                    "razorpay_order_id": order_id,
                    "razorpay_payment_id": payment_id,
                    "razorpay_signature": sig,
                    "product_identifier": "free_perk",
                },
            )
            assert resp.status_code == 404
            assert resp.json()["error_code"] == "ORDER_RECORD_NOT_FOUND"
    finally:
        settings.RAZORPAY_KEY_SECRET = orig_key_secret
        settings.TESTING = True
        app.dependency_overrides.clear()


def test_production_secrets_validation_razorpay():
    """Assert validate_production_secrets enforces RAZORPAY_KEY_SECRET and RAZORPAY_WEBHOOK_SECRET in production."""
    orig_env = settings.ENVIRONMENT
    orig_jwt = settings.JWT_SECRET_KEY
    orig_db = settings.DATABASE_URL
    orig_sup_url = settings.SUPABASE_URL
    orig_sup_key = settings.SUPABASE_SERVICE_ROLE_KEY
    orig_adm_key = settings.SUPERADMIN_SECRET_KEY
    orig_bridge = settings.CONTACT_BRIDGE_SECRET_KEY
    orig_rp_key = settings.RAZORPAY_KEY_SECRET
    orig_rp_wh = settings.RAZORPAY_WEBHOOK_SECRET

    settings.ENVIRONMENT = "production"
    settings.JWT_SECRET_KEY = "a_very_secure_production_jwt_secret_key_32_chars_long"
    settings.DATABASE_URL = "postgresql+asyncpg://user:pass@host:5432/db"
    settings.SUPABASE_URL = "https://supabase.prod.urheart.app"
    settings.SUPABASE_SERVICE_ROLE_KEY = "service_role_key_prod_123"
    settings.SUPERADMIN_SECRET_KEY = "mock_superadmin_secret_key_32b_prod"
    settings.CONTACT_BRIDGE_SECRET_KEY = "contact_bridge_secret_32b_prod"
    settings.RAZORPAY_KEY_SECRET = ""
    settings.RAZORPAY_WEBHOOK_SECRET = ""

    try:
        # Missing RAZORPAY_KEY_SECRET
        with pytest.raises(RuntimeError, match="RAZORPAY_KEY_SECRET is required"):
            validate_production_secrets()

        settings.RAZORPAY_KEY_SECRET = "real_rp_secret_123"
        # Missing RAZORPAY_WEBHOOK_SECRET
        with pytest.raises(RuntimeError, match="RAZORPAY_WEBHOOK_SECRET is required"):
            validate_production_secrets()

        # Placeholder RAZORPAY_WEBHOOK_SECRET
        settings.RAZORPAY_WEBHOOK_SECRET = "placeholder_webhook_secret"
        with pytest.raises(RuntimeError, match="must not be a placeholder"):
            validate_production_secrets()

        # Valid production secrets
        settings.RAZORPAY_WEBHOOK_SECRET = "real_wh_secret_123"
        validate_production_secrets()  # Should not raise
    finally:
        settings.ENVIRONMENT = orig_env
        settings.JWT_SECRET_KEY = orig_jwt
        settings.DATABASE_URL = orig_db
        settings.SUPABASE_URL = orig_sup_url
        settings.SUPABASE_SERVICE_ROLE_KEY = orig_sup_key
        settings.SUPERADMIN_SECRET_KEY = orig_adm_key
        settings.CONTACT_BRIDGE_SECRET_KEY = orig_bridge
        settings.RAZORPAY_KEY_SECRET = orig_rp_key
        settings.RAZORPAY_WEBHOOK_SECRET = orig_rp_wh
