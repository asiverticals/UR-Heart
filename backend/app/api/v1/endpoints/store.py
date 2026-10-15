from fastapi import APIRouter, Depends

from ....core.config import settings
from ....models.domain.user import User
from ....schemas.base_response import SanctuaryResponse
from ....schemas.monetization import StoreCatalogResponse, StoreBalancesResponse, StoreProductItem
from ....services.billing_entitlement_service import billing_entitlement_service
from ...deps import get_current_user

router = APIRouter()

@router.get("/catalog", response_model=SanctuaryResponse[StoreCatalogResponse])
async def get_store_catalog(
    is_web_store: bool = False,
) -> SanctuaryResponse[StoreCatalogResponse]:
    """Retrieves the active sovereign product catalog strictly gated by Condition C2."""
    usd_enabled = getattr(settings, "ENABLE_GLOBAL_USD_BILLING", False)
    raw_products = billing_entitlement_service.get_active_catalog(is_web_store=is_web_store)
    products = [StoreProductItem(**p) for p in raw_products]

    return SanctuaryResponse(
        data=StoreCatalogResponse(
            currency="INR",
            usd_enabled=usd_enabled,
            products=products,
        ),
        message="Active sovereign store catalog retrieved successfully.",
    )

@router.get("/balances", response_model=SanctuaryResponse[StoreBalancesResponse])
async def get_store_balances(
    current_user: User = Depends(get_current_user),
) -> SanctuaryResponse[StoreBalancesResponse]:
    """Retrieves seeker wallet balances, active passes, and daily mindful quotas."""
    return SanctuaryResponse(
        data=StoreBalancesResponse(
            reward_balance=current_user.reward_balance or 0,
            streak_count=current_user.streak_count or 0,
            swipes_remaining=current_user.swipes_remaining or 0,
            direct_letters_count=current_user.direct_letters_count or 0,
            boost_points=current_user.boost_points or 0,
            super_likes_count=getattr(current_user, "super_likes_count", 0) or 0,
            instant_bridge_passes=getattr(current_user, "instant_bridge_passes", 0) or 0,
            subscription_tier=current_user.subscription_tier or "free",
            is_ad_free=current_user.is_ad_free or False,
        ),
        message="Seeker store balances retrieved successfully.",
    )
