from typing import List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.domain.user import User
from ....schemas.feed import (
    DiscoveryFeedResponse,
    SwipeRequest,
    SwipeResponse,
    SwipesRemainingResponse,
)
from ....services.feed_service import FeedService, get_feed_service
from ...deps import get_current_user

router = APIRouter()

@router.get(
    "",
    response_model=DiscoveryFeedResponse,
    status_code=status.HTTP_200_OK,
    summary="Get 10-Swipe Discovery Deck with DPDP Coordinate Fuzzing",
)
async def get_discovery_deck(
    limit: int = Query(20, ge=1, le=50, description="Max candidate profiles to return"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    feed_service: FeedService = Depends(get_feed_service),
) -> DiscoveryFeedResponse:
    """Retrieves discovery feed cards adhering to DPDP coordinate fuzzing and indexed self-exclusion perimeter."""
    profiles = await feed_service.get_discovery_feed(
        current_user=current_user,
        session=db,
        limit=limit,
    )
    return DiscoveryFeedResponse(
        profiles=profiles,
        swipes_remaining=current_user.swipes_remaining,
    )

@router.post(
    "/swipe",
    response_model=SwipeResponse,
    status_code=status.HTTP_200_OK,
    summary="Record Swipe Action & Decrement Daily Mindful Quota",
)
async def record_swipe_action(
    req: SwipeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    feed_service: FeedService = Depends(get_feed_service),
) -> SwipeResponse:
    """Evaluates swipe intent, decrements daily swipe quota, and provisions matches on mutual likes."""
    result = await feed_service.record_swipe(
        current_user=current_user,
        target_id=req.target_id,
        action=req.action,
        direct_letter=req.direct_letter_text,
        session=db,
    )
    return SwipeResponse(
        is_match=result["is_match"],
        match_id=result["match_id"],
        swipes_remaining=result["swipes_remaining"],
    )

@router.get(
    "/swipes-remaining",
    response_model=SwipesRemainingResponse,
    status_code=status.HTTP_200_OK,
    summary="Check Remaining Swipe Quota & Daily Refresh Countdown",
)
async def get_swipes_remaining(
    current_user: User = Depends(get_current_user),
    feed_service: FeedService = Depends(get_feed_service),
) -> SwipesRemainingResponse:
    """Returns current seeker's daily quota balance, streak count, and seconds until UTC midnight refresh."""
    seconds_until_refresh = feed_service.calculate_seconds_until_midnight()
    return SwipesRemainingResponse(
        swipes_remaining=current_user.swipes_remaining,
        streak_count=current_user.streak_count,
        seconds_until_refresh=seconds_until_refresh,
    )
