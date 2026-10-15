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
            assert len(data["products"]) == 6

            # Every product must have usd_price set to None under Condition C2
            for p in data["products"]:
                assert p["usd_price"] is None
                assert p["currency_symbol"] == "₹"
                assert p["inr_price"] > 0

            # Verify exact product specifications for 6 canonical SKUs
            skus = {p["id"]: p for p in data["products"]}
            assert skus["pass_weekly"]["inr_price"] == 49.0
            assert skus["pass_weekly"]["product_class"] == "pass"
            assert skus["pass_monthly"]["inr_price"] == 149.0
            assert skus["pass_monthly"]["product_class"] == "pass"
            assert skus["pass_infinity"]["inr_price"] == 1499.0
            assert skus["pass_infinity"]["product_class"] == "pass"
            assert skus["contact_key_instant"]["inr_price"] == 29.0
            assert skus["contact_key_instant"]["product_class"] == "micro_perk"
            assert skus["direct_letters_pack_3"]["inr_price"] == 49.0
            assert skus["direct_letters_pack_3"]["product_class"] == "micro_perk"
            assert skus["passport_24h"]["inr_price"] == 99.0
            assert skus["passport_24h"]["product_class"] == "micro_perk"

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
            assert skus["pass_weekly"]["usd_price"] == 0.99
            assert skus["pass_monthly"]["usd_price"] == 2.99
            assert skus["pass_infinity"]["usd_price"] == 29.99
            assert skus["contact_key_instant"]["usd_price"] == 0.49
            assert skus["direct_letters_pack_3"]["usd_price"] == 0.99
            assert skus["passport_24h"]["usd_price"] == 1.99

@pytest.mark.asyncio
async def test_web_store_catalog_bonus_perks():
    """Test: Web Store catalog endpoint preserves identical pricing while rendering +20% bonus perk badges."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/store/catalog?is_web_store=true")
        assert res.status_code == 200
        data = res.json()["data"]
        skus = {p["id"]: p for p in data["products"]}

        assert skus["pass_weekly"]["inr_price"] == 49.0
        assert "+20%" in skus["pass_weekly"]["badge_label"]
        assert "120 Swipes" in skus["pass_weekly"]["description"]

        assert skus["pass_monthly"]["inr_price"] == 149.0
        assert "+20%" in skus["pass_monthly"]["badge_label"]
        assert "600 Swipes" in skus["pass_monthly"]["description"]

        assert skus["pass_infinity"]["inr_price"] == 1499.0
        assert "+20%" in skus["pass_infinity"]["badge_label"]

        assert skus["contact_key_instant"]["inr_price"] == 29.0
        assert "+20%" in skus["contact_key_instant"]["badge_label"]

        assert skus["direct_letters_pack_3"]["inr_price"] == 49.0
        assert "+20%" in skus["direct_letters_pack_3"]["badge_label"]

        assert skus["passport_24h"]["inr_price"] == 99.0
        assert "+20%" in skus["passport_24h"]["badge_label"]

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
    """Test 4: provision_user_entitlements increments user balances correctly for 6 canonical products."""
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

    # 1. pass_weekly: +100 swipes, 7-day spark subscription
    r1 = await billing_entitlement_service.provision_user_entitlements(
        user=user,
        product_identifier="pass_weekly",
        session=db_session,
    )
    assert user.swipes_remaining == 125
    assert user.subscription_tier == "spark"
    assert user.is_ad_free is True
    assert user.subscription_expires_at is not None

    # 2. pass_monthly: +500 swipes, +5 direct letters, 30-day flame subscription
    r2 = await billing_entitlement_service.provision_user_entitlements(
        user=user,
        product_identifier="pass_monthly",
        session=db_session,
    )
    assert user.swipes_remaining == 625
    assert user.direct_letters_count == 6  # 1 + 5
    assert user.subscription_tier == "flame"

    # 3. pass_infinity: unlimited swipes, +15 direct letters, lifetime tier
    r3 = await billing_entitlement_service.provision_user_entitlements(
        user=user,
        product_identifier="pass_infinity",
        session=db_session,
    )
    assert user.has_unlimited_swipes is True
    assert user.direct_letters_count == 21  # 6 + 15
    assert user.subscription_tier == "lifetime"

    # 4. contact_key_instant: +1 instant contact key
    r4 = await billing_entitlement_service.provision_user_entitlements(
        user=user,
        product_identifier="contact_key_instant",
        session=db_session,
    )
    assert user.instant_contact_keys == 1

    # 5. direct_letters_pack_3: +3 direct letters
    r5 = await billing_entitlement_service.provision_user_entitlements(
        user=user,
        product_identifier="direct_letters_pack_3",
        session=db_session,
    )
    assert user.direct_letters_count == 24  # 21 + 3

    # 6. passport_24h: passport_expires_at extended by 24 hours
    r6 = await billing_entitlement_service.provision_user_entitlements(
        user=user,
        product_identifier="passport_24h",
        session=db_session,
    )
    assert user.passport_expires_at is not None

    # 7. Web Store Bonus: +20% extra perks
    before_swipes = user.swipes_remaining
    await billing_entitlement_service.provision_user_entitlements(
        user=user,
        product_identifier="pass_weekly",
        session=db_session,
        is_web_store=True,
    )
    # 100 * 1.2 = 120 swipes added
    assert user.swipes_remaining == before_swipes + 120

    # 8. Invalid SKU raises SanctuaryException
    with pytest.raises(SanctuaryException) as exc_info:
        await billing_entitlement_service.provision_user_entitlements(
            user=user,
            product_identifier="non_existent_sku",
            session=db_session,
        )
    assert exc_info.value.status_code == 400
    assert exc_info.value.error_code == "INVALID_PRODUCT"

@pytest.mark.asyncio
async def test_pass_renewal_preserves_tier_and_extends_duration(db_session, make_user):
    """Test 5: Purchasing a weekly pass while holding an active kindred pass does not downgrade tier and extends duration."""
    user = make_user(
        full_name="Kindred Seeker",
        is_profile_completed=True,
        subscription_tier="free",
    )
    db_session.add(user)
    await db_session.commit()

    # 1. Purchase 90-day Kindred pass
    await billing_entitlement_service.provision_user_entitlements(
        user=user,
        product_identifier="pass_sovereign_quarter",
        session=db_session,
    )
    assert user.subscription_tier == "kindred"
    exp1 = user.subscription_expires_at

    # 2. Purchase weekly pass (normally 'spark' and 7 days)
    r2 = await billing_entitlement_service.provision_user_entitlements(
        user=user,
        product_identifier="pass_sovereign_weekly",
        session=db_session,
    )
    # Tier must remain 'kindred' (not downgraded to 'spark')
    assert user.subscription_tier == "kindred"
    assert r2["subscription_tier"] == "kindred"
    # Expiration must be extended by 7 days beyond exp1
    assert user.subscription_expires_at > exp1
    diff = user.subscription_expires_at - exp1
    assert round(diff.total_seconds() / 86400) == 7
