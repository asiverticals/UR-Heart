from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.exceptions import SanctuaryException
from ..models.domain.user import User

STATIC_PRODUCT_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "direct_letter_single",
        "title": "Direct Thought Letter",
        "description": "Send an intentional direct letter bypassing discovery swipe deck.",
        "product_class": "micro_perk",
        "inr_price": 29.0,
        "usd_price": 0.99,
        "currency_symbol": "₹",
        "badge_label": "Popular",
        "entitlement": "+1 direct_letter",
    },
    {
        "id": "profile_unlock_single",
        "title": "Modesty Veil Unveil",
        "description": "Unveils 35px photo blur veil for a single admired seeker.",
        "product_class": "micro_perk",
        "inr_price": 39.0,
        "usd_price": 1.49,
        "currency_symbol": "₹",
        "badge_label": None,
        "entitlement": "+1 profile_unveil",
    },
    {
        "id": "super_like_pack_3",
        "title": "Resonance Spark (x3)",
        "description": "+3 High-resonance Super Likes with top deck placement.",
        "product_class": "micro_perk",
        "inr_price": 49.0,
        "usd_price": 1.99,
        "currency_symbol": "₹",
        "badge_label": "3x Spark",
        "entitlement": "+3 super_likes",
    },
    {
        "id": "spotlight_boost_24h",
        "title": "24h Sanctuary Spotlight",
        "description": "24-hour priority discovery placement (+100 Boost Points).",
        "product_class": "micro_perk",
        "inr_price": 79.0,
        "usd_price": 2.99,
        "currency_symbol": "₹",
        "badge_label": "24 Hours",
        "entitlement": "+100 boost_points",
    },
    {
        "id": "sacred_bridge_instant",
        "title": "Instant Bridge Key",
        "description": "Instant reveal of WhatsApp/Instagram contact without 3-ad ritual.",
        "product_class": "micro_perk",
        "inr_price": 99.0,
        "usd_price": 3.99,
        "currency_symbol": "₹",
        "badge_label": "Instant",
        "entitlement": "instant_bridge_reveal",
    },
    {
        "id": "pass_sovereign_weekly",
        "title": "Sovereign Pass (7 Days)",
        "description": "Unlimited Swipes, Ad-Free UI, +5 Direct Letters for 7 days.",
        "product_class": "pass",
        "inr_price": 299.0,
        "usd_price": 9.99,
        "currency_symbol": "₹",
        "badge_label": "7 Days",
        "entitlement": "Unlimited Swipes, Ad-Free UI, +5 Direct Letters",
    },
    {
        "id": "pass_sovereign_monthly",
        "title": "Sovereign Pass (30 Days)",
        "description": "Complete Sanctuary access, +25 Letters, Voice Verification Badge for 30 days.",
        "product_class": "pass",
        "inr_price": 999.0,
        "usd_price": 29.99,
        "currency_symbol": "₹",
        "badge_label": "Most Mindful",
        "entitlement": "Full Sanctuary Pass, +25 Letters, Voice Verification Badge",
    },
    {
        "id": "pass_sovereign_quarter",
        "title": "Sovereign Pass (90 Days)",
        "description": "Complete access, +75 Direct Letters, AI Wingman priority for 90 days.",
        "product_class": "pass",
        "inr_price": 2499.0,
        "usd_price": 49.99,
        "currency_symbol": "₹",
        "badge_label": "Best Value",
        "entitlement": "Complete access, +75 Direct Letters, AI Wingman priority",
    },
]

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
    user.swipes_remaining = 999

class BillingEntitlementService:
    """Sovereign Store Catalog & atomic entitlement provisioning engine governed by Condition C2."""

    def get_active_catalog(self) -> List[Dict[str, Any]]:
        """Returns the active product catalog.
        
        Condition C2 Invariant:
        If settings.ENABLE_GLOBAL_USD_BILLING is False, USD pricing is strictly hidden
        and omitted from client delivery, enforcing Indian Rupee domestic priority.
        """
        usd_enabled = getattr(settings, "ENABLE_GLOBAL_USD_BILLING", False)
        catalog: List[Dict[str, Any]] = []

        for item in STATIC_PRODUCT_CATALOG:
            product = dict(item)
            if not usd_enabled:
                product["usd_price"] = None
            catalog.append(product)

        return catalog

    async def provision_user_entitlements(
        self,
        user: User,
        product_identifier: str,
        session: AsyncSession,
    ) -> Dict[str, Any]:
        """Atomically provisions entitlement yields to the user account based on SKU."""
        now = datetime.now(timezone.utc)

        if product_identifier == "direct_letter_single":
            user.direct_letters_count = (user.direct_letters_count or 0) + 1
        elif product_identifier == "profile_unlock_single":
            user.reveal_tokens_count = (user.reveal_tokens_count or 0) + 1
        elif product_identifier == "super_like_pack_3":
            user.super_likes_count = (getattr(user, "super_likes_count", 0) or 0) + 3
        elif product_identifier == "spotlight_boost_24h":
            user.boost_points = (user.boost_points or 0) + 100
        elif product_identifier == "sacred_bridge_instant":
            user.instant_bridge_passes = (getattr(user, "instant_bridge_passes", 0) or 0) + 1
        elif product_identifier == "pass_sovereign_weekly":
            _resolve_subscription(user, "spark", 7, now)
            user.direct_letters_count = (user.direct_letters_count or 0) + 5
        elif product_identifier == "pass_sovereign_monthly":
            _resolve_subscription(user, "flame", 30, now)
            user.direct_letters_count = (user.direct_letters_count or 0) + 25
            user.is_voice_verified = True
        elif product_identifier == "pass_sovereign_quarter":
            _resolve_subscription(user, "kindred", 90, now)
            user.direct_letters_count = (user.direct_letters_count or 0) + 75
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
            "direct_letters_count": user.direct_letters_count,
            "boost_points": user.boost_points,
            "super_likes_count": getattr(user, "super_likes_count", 0),
            "instant_bridge_passes": getattr(user, "instant_bridge_passes", 0),
            "swipes_remaining": user.swipes_remaining,
            "subscription_tier": user.subscription_tier,
            "subscription_expires_at": user.subscription_expires_at.isoformat() if user.subscription_expires_at else None,
            "is_ad_free": user.is_ad_free,
            "reward_balance": user.reward_balance,
        }

billing_entitlement_service = BillingEntitlementService()

def get_billing_entitlement_service() -> BillingEntitlementService:
    return billing_entitlement_service
