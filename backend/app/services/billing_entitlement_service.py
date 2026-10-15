from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.exceptions import SanctuaryException
from ..models.domain.user import User

CATALOG_PRODUCTS: Dict[str, Dict[str, Any]] = {
    "pass_weekly": {
        "id": "pass_weekly",
        "title": "Weekly Sovereign Pass",
        "product_class": "pass",
        "inr_price": 49.00,
        "usd_price": 0.99,
        "currency_symbol": "₹",
        "badge_label": "7 Days",
        "description": "100 Swipes for 7 days of intentional discovery.",
        "entitlements": {"swipes_added": 100, "duration_days": 7},
    },
    "pass_monthly": {
        "id": "pass_monthly",
        "title": "Monthly Sovereign Pass",
        "product_class": "pass",
        "inr_price": 149.00,
        "usd_price": 2.99,
        "currency_symbol": "₹",
        "badge_label": "30 Days",
        "description": "500 Swipes + 5 Direct Letters for 30 days.",
        "entitlements": {"swipes_added": 500, "direct_letters_added": 5, "duration_days": 30},
    },
    "pass_infinity": {
        "id": "pass_infinity",
        "title": "Infinity Sovereign Pass",
        "product_class": "pass",
        "inr_price": 1499.00,
        "usd_price": 29.99,
        "currency_symbol": "₹",
        "badge_label": "Infinity",
        "description": "Infinity Swipes + 15 Direct Letters (non-expiring entitlement).",
        "entitlements": {"unlimited_swipes": True, "direct_letters_added": 15},
    },
    "contact_key_instant": {
        "id": "contact_key_instant",
        "title": "Instant Contact Key",
        "product_class": "micro_perk",
        "inr_price": 29.00,
        "usd_price": 0.49,
        "currency_symbol": "₹",
        "badge_label": "Instant",
        "description": "1 Instant Contact Key unsealing mutual contact bridge.",
        "entitlements": {"instant_contact_keys": 1},
    },
    "direct_letters_pack_3": {
        "id": "direct_letters_pack_3",
        "title": "Direct Letter Pack (x3)",
        "product_class": "micro_perk",
        "inr_price": 49.00,
        "usd_price": 0.99,
        "currency_symbol": "₹",
        "badge_label": "3 Letters",
        "description": "3 Intentional Direct Letters bypassing discovery deck.",
        "entitlements": {"direct_letters_added": 3},
    },
    "passport_24h": {
        "id": "passport_24h",
        "title": "24h Global Passport",
        "product_class": "micro_perk",
        "inr_price": 99.00,
        "usd_price": 1.99,
        "currency_symbol": "₹",
        "badge_label": "24 Hours",
        "description": "24-Hour Global Passport across world sanctuaries.",
        "entitlements": {"passport_hours": 24},
    },
}

TIER_RANKS: Dict[str, int] = {
    "free": 0,
    "spark": 1,
    "flame": 2,
    "kindred": 3,
    "lifetime": 4,
}

def _resolve_subscription(user: User, pass_tier: str, duration_days: int, now: datetime) -> None:
    """Calculates non-downgrading subscription tier and cumulative duration extension."""
    cur_exp = user.subscription_expires_at
    if cur_exp is not None and cur_exp.tzinfo is None:
        cur_exp = cur_exp.replace(tzinfo=timezone.utc)

    is_currently_active = cur_exp is not None and cur_exp > now
    base_time = cur_exp if is_currently_active else now

    current_rank = TIER_RANKS.get(user.subscription_tier or "free", 0)
    new_rank = TIER_RANKS.get(pass_tier, 0)

    # Preserve higher tier if current active subscription has a higher rank
    if is_currently_active and current_rank > new_rank:
        pass
    else:
        user.subscription_tier = pass_tier

    user.subscription_expires_at = base_time + timedelta(days=duration_days)
    user.is_ad_free = True


class BillingEntitlementService:
    """Sovereign Store Catalog & atomic entitlement provisioning engine governed by Condition C2."""

    def get_active_catalog(self, is_web_store: bool = False) -> List[Dict[str, Any]]:
        """Returns the active product catalog.
        
        Condition C2 Invariant:
        If settings.ENABLE_GLOBAL_USD_BILLING is False, USD pricing is strictly hidden
        and omitted from client delivery, enforcing Indian Rupee domestic priority.
        
        Web Store Parity:
        When is_web_store is True, prices remain identical while descriptions and badges
        reflect +20% bonus perks.
        """
        usd_enabled = getattr(settings, "ENABLE_GLOBAL_USD_BILLING", False)
        catalog: List[Dict[str, Any]] = []

        for p_id, item in CATALOG_PRODUCTS.items():
            product = dict(item)
            if not usd_enabled:
                product["usd_price"] = None

            if is_web_store:
                if p_id == "pass_weekly":
                    product["badge_label"] = "+20% Perks (120 Swipes)"
                    product["description"] = "120 Swipes (Includes +20% Web Store Bonus, 7 days)."
                elif p_id == "pass_monthly":
                    product["badge_label"] = "+20% Perks (600 Swipes)"
                    product["description"] = "600 Swipes + 6 Letters (Includes +20% Web Store Bonus, 30 days)."
                elif p_id == "pass_infinity":
                    product["badge_label"] = "+20% Perks (18 Letters)"
                    product["description"] = "Infinity Swipes + 18 Letters (Includes +20% Web Store Bonus)."
                elif p_id == "contact_key_instant":
                    product["badge_label"] = "+20% Perks"
                    product["description"] = "1 Instant Contact Key + 20 Bonus Swipes (Web Store Bonus)."
                elif p_id == "direct_letters_pack_3":
                    product["badge_label"] = "+20% Perks (4 Letters)"
                    product["description"] = "4 Direct Letters (Includes +20% Web Store Bonus)."
                elif p_id == "passport_24h":
                    product["badge_label"] = "+20% Perks (29 Hours)"
                    product["description"] = "29 Hours Global Passport (Includes +20% Web Store Bonus)."

            catalog.append(product)

        return catalog

    async def provision_user_entitlements(
        self,
        user: User,
        product_identifier: str,
        session: AsyncSession,
        is_web_store: bool = False,
    ) -> Dict[str, Any]:
        """Atomically provisions entitlement yields to the user account based on SKU.
        
        Web Store Bonus:
        When is_web_store is True, seeker receives 20% extra perks on purchased items.
        """
        now = datetime.now(timezone.utc)
        multiplier = 1.2 if is_web_store else 1.0

        if product_identifier == "pass_weekly":
            swipes = int(round(100 * multiplier))
            user.swipes_remaining = (user.swipes_remaining or 0) + swipes
            _resolve_subscription(user, "spark", 7, now)
        elif product_identifier == "pass_monthly":
            swipes = int(round(500 * multiplier))
            letters = int(round(5 * multiplier))
            user.swipes_remaining = (user.swipes_remaining or 0) + swipes
            user.direct_letters_count = (user.direct_letters_count or 0) + letters
            _resolve_subscription(user, "flame", 30, now)
        elif product_identifier == "pass_infinity":
            letters = int(round(15 * multiplier))
            user.has_unlimited_swipes = True
            user.swipes_remaining = max(user.swipes_remaining or 0, 9999)
            user.direct_letters_count = (user.direct_letters_count or 0) + letters
            _resolve_subscription(user, "lifetime", 36500, now)
        elif product_identifier == "contact_key_instant":
            user.instant_contact_keys = (getattr(user, "instant_contact_keys", 0) or 0) + 1
            user.instant_bridge_passes = (getattr(user, "instant_bridge_passes", 0) or 0) + 1
            if is_web_store:
                user.swipes_remaining = (user.swipes_remaining or 0) + 20
        elif product_identifier == "direct_letters_pack_3":
            letters = int(round(3 * multiplier))
            user.direct_letters_count = (user.direct_letters_count or 0) + letters
        elif product_identifier == "passport_24h":
            hours = int(round(24 * multiplier))
            current_passport = user.passport_expires_at
            if current_passport is not None and current_passport.tzinfo is None:
                current_passport = current_passport.replace(tzinfo=timezone.utc)
            base = current_passport if (current_passport and current_passport > now) else now
            user.passport_expires_at = base + timedelta(hours=hours)

        # Legacy backward-compatibility aliases
        elif product_identifier == "direct_letter_single":
            letters = int(round(1 * multiplier))
            user.direct_letters_count = (user.direct_letters_count or 0) + letters
        elif product_identifier == "profile_unlock_single":
            user.reveal_tokens_count = (user.reveal_tokens_count or 0) + 1
        elif product_identifier == "super_like_pack_3":
            likes = int(round(3 * multiplier))
            user.super_likes_count = (getattr(user, "super_likes_count", 0) or 0) + likes
        elif product_identifier == "spotlight_boost_24h":
            boost = int(round(100 * multiplier))
            user.boost_points = (user.boost_points or 0) + boost
        elif product_identifier == "sacred_bridge_instant":
            user.instant_contact_keys = (getattr(user, "instant_contact_keys", 0) or 0) + 1
            user.instant_bridge_passes = (getattr(user, "instant_bridge_passes", 0) or 0) + 1
        elif product_identifier == "pass_sovereign_weekly":
            _resolve_subscription(user, "spark", 7, now)
            user.swipes_remaining = 999
            user.direct_letters_count = (user.direct_letters_count or 0) + (6 if is_web_store else 5)
        elif product_identifier == "pass_sovereign_monthly":
            _resolve_subscription(user, "flame", 30, now)
            user.direct_letters_count = (user.direct_letters_count or 0) + (30 if is_web_store else 25)
            user.is_voice_verified = True
        elif product_identifier == "pass_sovereign_quarter":
            _resolve_subscription(user, "kindred", 90, now)
            user.direct_letters_count = (user.direct_letters_count or 0) + (90 if is_web_store else 75)
            user.is_voice_verified = True
        else:
            raise SanctuaryException(
                error_code="INVALID_PRODUCT",
                message=f"Unknown product identifier '{product_identifier}'",
                status_code=400,
            )

        await session.commit()
        await session.refresh(user)

        return {
            "user_id": str(user.id),
            "product_identifier": product_identifier,
            "provisioned": True,
            "is_web_store": is_web_store,
            "direct_letters_count": user.direct_letters_count,
            "boost_points": user.boost_points,
            "super_likes_count": getattr(user, "super_likes_count", 0),
            "instant_contact_keys": getattr(user, "instant_contact_keys", 0),
            "instant_bridge_passes": getattr(user, "instant_bridge_passes", 0),
            "has_unlimited_swipes": getattr(user, "has_unlimited_swipes", False),
            "passport_expires_at": user.passport_expires_at.isoformat() if user.passport_expires_at else None,
            "swipes_remaining": user.swipes_remaining,
            "subscription_tier": user.subscription_tier,
            "subscription_expires_at": user.subscription_expires_at.isoformat() if user.subscription_expires_at else None,
            "is_ad_free": user.is_ad_free,
            "reward_balance": user.reward_balance,
        }

billing_entitlement_service = BillingEntitlementService()

def get_billing_entitlement_service() -> BillingEntitlementService:
    return billing_entitlement_service
