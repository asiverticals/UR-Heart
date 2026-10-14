from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.domain.user import User
from ....schemas.base_response import SanctuaryResponse
from ....schemas.streak import (
    MorningHarvestClaimRequest,
    StreakStatusResponse,
    HarvestClaimResponse,
)
from ....services.streak_engine import StreakEngine, get_streak_engine
from ...deps import get_current_user

router = APIRouter()

@router.get("/status", response_model=SanctuaryResponse[StreakStatusResponse])
async def get_streak_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    engine: StreakEngine = Depends(get_streak_engine),
):
    """Retrieves current user's mindful streak status, decay countdown, and morning slumber harvest availability."""
    decayed = engine.evaluate_streak_decay(current_user)
    if decayed:
        await db.commit()

    remaining_seconds = engine.calculate_remaining_seconds(current_user)
    is_active = (current_user.streak_count or 0) > 0 and remaining_seconds > 0
    harvest_available = engine.is_harvest_available(current_user)

    data = StreakStatusResponse(
        streak_count=current_user.streak_count,
        boost_points=current_user.boost_points,
        streak_expires_at=current_user.streak_expires_at,
        is_active=is_active,
        remaining_seconds=remaining_seconds,
        morning_harvest_available=harvest_available,
    )
    return SanctuaryResponse(data=data, message="Mindful streak status loaded.")

@router.post("/claim-morning-harvest", response_model=SanctuaryResponse[HarvestClaimResponse])
async def claim_morning_harvest(
    payload: MorningHarvestClaimRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    engine: StreakEngine = Depends(get_streak_engine),
):
    """Claims daily morning harvest rewards based on nocturnal accelerometer rest multiplier."""
    result = await engine.claim_morning_harvest(
        user=current_user,
        sleep_hours=payload.sleep_duration_hours,
        session=db,
    )
    return SanctuaryResponse(
        data=HarvestClaimResponse.model_validate(result),
        message=result["message"],
    )

@router.post("/heartbeat", response_model=SanctuaryResponse[StreakStatusResponse])
async def streak_heartbeat(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    engine: StreakEngine = Depends(get_streak_engine),
):
    """Lightweight activity check-in that refreshes the 24-hour streak window."""
    engine.record_daily_activity(current_user)
    await db.commit()

    remaining_seconds = engine.calculate_remaining_seconds(current_user)
    harvest_available = engine.is_harvest_available(current_user)

    data = StreakStatusResponse(
        streak_count=current_user.streak_count,
        boost_points=current_user.boost_points,
        streak_expires_at=current_user.streak_expires_at,
        is_active=True,
        remaining_seconds=remaining_seconds,
        morning_harvest_available=harvest_available,
    )
    return SanctuaryResponse(data=data, message="Mindful streak refreshed.")
