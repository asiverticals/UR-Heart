import pytest
from unittest.mock import patch
import httpx
from httpx import ASGITransport

from backend.app.api.deps import get_current_user
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.exceptions import SanctuaryException
from backend.app.main import app
from backend.app.services.billing_entitlement_service import billing_entitlement_service

@pytest.mark.asyncio
async def test_c2_currency_gating_hides_usd_when_disabled():
    """Test 1: Condition C2 Gate: When ENABLE_GLOBAL_USD_BILLING=false, catalog endpoint returns strictly INR and hides USD values."""
    with patch.object(settings, "ENABLE_GLOBAL_USD_BILLING", False):
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/v1/store/catalog")
            assert res.status_code == 200
            body = res.json()
            assert body["success"] is True
            data = body["data"]

            assert data["currency"] == "INR"
            assert data["usd_enabled"] is False
            assert len(data["products"]) == 8

            # Every product must have usd_price set to None under Condition C2
            for p in data["products"]:
                assert p["usd_price"] is None
                assert p["currency_symbol"] == "₹"
                assert p["inr_price"] > 0

            # Verify exact product specifications
            skus = {p["id"]: p for p in data["products"]}
            assert skus["direct_letter_single"]["inr_price"] == 29.0
            assert skus["direct_letter_single"]["product_class"] == "micro_perk"
            assert skus["profile_unlock_single"]["inr_price"] == 39.0
            assert skus["super_like_pack_3"]["inr_price"] == 49.0
            assert skus["spotlight_boost_24h"]["inr_price"] == 79.0
            assert skus["sacred_bridge_instant"]["inr_price"] == 99.0
            assert skus["pass_sovereign_weekly"]["inr_price"] == 299.0
            assert skus["pass_sovereign_weekly"]["product_class"] == "pass"
            assert skus["pass_sovereign_monthly"]["inr_price"] == 999.0
            assert skus["pass_sovereign_quarter"]["inr_price"] == 2499.0

@pytest.mark.asyncio
async def test_c2_currency_gating_exposes_usd_when_enabled():
    """Test 2: When ENABLE_GLOBAL_USD_BILLING=true, catalog exposes both USD and INR pricing."""
    with patch.object(settings, "ENABLE_GLOBAL_USD_BILLING", True):
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/v1/store/catalog")
            assert res.status_code == 200
            data = res.json()["data"]

            assert data["usd_enabled"] is True
            for p in data["products"]:
                assert p["usd_price"] is not None
                assert p["usd_price"] > 0
                assert p["inr_price"] > 0

            skus = {p["id"]: p for p in data["products"]}
            assert skus["direct_letter_single"]["usd_price"] == 0.99
            assert skus["pass_sovereign_weekly"]["usd_price"] == 9.99
            assert skus["pass_sovereign_monthly"]["usd_price"] == 29.99
            assert skus["pass_sovereign_quarter"]["usd_price"] == 49.99

@pytest.mark.asyncio
async def test_get_store_balances(db_session, make_user):
    """Test 3: GET /api/v1/store/balances returns exact integer values from authenticated User record."""
    user = make_user(
        full_name="Wealthy Seeker",
        is_profile_completed=True,
        reward_balance=350,
        streak_count=7,
        swipes_remaining=50,
        direct_letters_count=4,
        boost_points=120,
        subscription_tier="spark",
        is_ad_free=True,
    )
    db_session.add(user)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/v1/store/balances")
            assert res.status_code == 200
            data = res.json()["data"]

            assert data["reward_balance"] == 350
            assert data["streak_count"] == 7
            assert data["swipes_remaining"] == 50
            assert data["direct_letters_count"] == 4
            assert data["boost_points"] == 120
            assert data["subscription_tier"] == "spark"
            assert data["is_ad_free"] is True
    finally:
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_provision_user_entitlements(db_session, make_user):
    """Test 4: provision_user_entitlements increments user balances correctly without race conditions."""
    user = make_user(
        full_name="Perk Seeker",
        is_profile_completed=True,
        direct_letters_count=1,
        boost_points=0,
        reveal_tokens_count=1,
        reward_balance=0,
        swipes_remaining=25,
        subscription_tier="free",
        is_ad_free=False,
    )
    db_session.add(user)
    await db_session.commit()

    # 1. Direct letter single
    r1 = await billing_entitlement_service.provision_user_entitlements(
        user=user,
        product_identifier="direct_letter_single",
        session=db_session,
    )
    assert r1["direct_letters_count"] == 2
    assert user.direct_letters_count == 2

    # 2. Spotlight boost 24h
    r2 = await billing_entitlement_service.provision_user_entitlements(
        user=user,
        product_identifier="spotlight_boost_24h",
        session=db_session,
    )
    assert r2["boost_points"] == 100
    assert user.boost_points == 100

    # 3. Profile unlock single
    await billing_entitlement_service.provision_user_entitlements(
        user=user,
        product_identifier="profile_unlock_single",
        session=db_session,
    )
    assert user.reveal_tokens_count == 2

    # 4. Super like pack 3
    await billing_entitlement_service.provision_user_entitlements(
        user=user,
        product_identifier="super_like_pack_3",
        session=db_session,
    )
    assert user.reward_balance == 3

    # 5. Sacred bridge instant
    await billing_entitlement_service.provision_user_entitlements(
        user=user,
        product_identifier="sacred_bridge_instant",
        session=db_session,
    )
    assert user.reward_balance == 4

    # 6. Sovereign Pass Weekly
    r_pass = await billing_entitlement_service.provision_user_entitlements(
        user=user,
        product_identifier="pass_sovereign_weekly",
        session=db_session,
    )
    assert r_pass["subscription_tier"] == "spark"
    assert r_pass["is_ad_free"] is True
    assert user.subscription_tier == "spark"
    assert user.is_ad_free is True
    assert user.swipes_remaining == 999
    assert user.direct_letters_count == 7  # 2 previous + 5 granted
    assert user.subscription_expires_at is not None

    # 7. Sovereign Pass Monthly
    await billing_entitlement_service.provision_user_entitlements(
        user=user,
        product_identifier="pass_sovereign_monthly",
        session=db_session,
    )
    assert user.subscription_tier == "flame"
    assert user.is_voice_verified is True
    assert user.direct_letters_count == 32  # 7 + 25

    # 8. Sovereign Pass Quarter
    await billing_entitlement_service.provision_user_entitlements(
        user=user,
        product_identifier="pass_sovereign_quarter",
        session=db_session,
    )
    assert user.subscription_tier == "kindred"
    assert user.direct_letters_count == 107  # 32 + 75

    # 9. Invalid SKU raises SanctuaryException
    with pytest.raises(SanctuaryException) as exc_info:
        await billing_entitlement_service.provision_user_entitlements(
            user=user,
            product_identifier="non_existent_sku",
            session=db_session,
        )
    assert exc_info.value.status_code == 400
    assert exc_info.value.error_code == "INVALID_PRODUCT"
