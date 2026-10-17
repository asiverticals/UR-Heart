import uuid
from decimal import Decimal
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.exceptions import SanctuaryException
from ....models.domain.legal import BlockedUser
from ....models.domain.user import User
from ....schemas.base_response import SanctuaryResponse
from ....schemas.profile import ProfilePublicResponse
from ....schemas.revelation import (
    PhotoRevealRequest,
    PhotoRevealRespondRequest,
    PhotoRevealResponse,
    PhotoRevealStatusResponse,
    PhotoRevealUnlockPerkRequest,
)
from ....services.feed_service import FeedService
from ....services.photo_reveal_service import PhotoRevealService, get_photo_reveal_service
from ...deps import get_current_user

router = APIRouter()

@router.post("/photo/request", response_model=SanctuaryResponse[PhotoRevealResponse])
async def request_photo_reveal(
    payload: PhotoRevealRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: PhotoRevealService = Depends(get_photo_reveal_service),
):
    """Initiates photo veil unmasking request to another seeker."""
    result = await service.request_photo_reveal(
        requester_id=current_user.id,
        target_id=payload.target_id,
        session=db,
    )
    return SanctuaryResponse(
        data=PhotoRevealResponse(
            target_id=result["target_id"],
            status=result["status"],
            is_revealed=result["is_revealed"],
            message=result["message"],
        ),
        message=result["message"],
    )

@router.post("/photo/respond", response_model=SanctuaryResponse[PhotoRevealResponse])
async def respond_to_photo_reveal(
    payload: PhotoRevealRespondRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: PhotoRevealService = Depends(get_photo_reveal_service),
):
    """Accepts or declines a pending photo veil unmasking request."""
    result = await service.respond_to_photo_reveal(
        target_id=current_user.id,
        requester_id=payload.requester_id,
        accept=payload.accept,
        session=db,
    )
    return SanctuaryResponse(
        data=PhotoRevealResponse(
            target_id=result["target_id"],
            status=result["status"],
            is_revealed=result["is_revealed"],
            message=result["message"],
        ),
        message=result["message"],
    )

@router.get("/photo/status/{target_id}", response_model=SanctuaryResponse[PhotoRevealStatusResponse])
async def get_photo_reveal_status(
    target_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: PhotoRevealService = Depends(get_photo_reveal_service),
):
    """Returns the current photo veil mask status between authenticated seeker and target."""
    result = await service.get_photo_reveal_status(
        user_a=current_user.id,
        user_b=target_id,
        session=db,
    )
    return SanctuaryResponse(
        data=PhotoRevealStatusResponse(
            target_id=result["target_id"],
            status=result["status"],
            is_revealed=result["is_revealed"],
        ),
        message="Photo reveal status fetched.",
    )

@router.post("/photo/unlock-perk", response_model=SanctuaryResponse[PhotoRevealResponse])
async def unlock_photo_with_perk(
    payload: PhotoRevealUnlockPerkRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: PhotoRevealService = Depends(get_photo_reveal_service),
):
    """Dispatches an expedited bilateral reveal invitation via micro-perk redemption; requires target consent to unmask veil (BNS 2023 § 77)."""
    result = await service.unlock_photo_with_perk(
        user_id=current_user.id,
        target_id=payload.target_id,
        session=db,
        purchase_reference=payload.purchase_reference,
    )
    return SanctuaryResponse(
        data=PhotoRevealResponse(
            target_id=result["target_id"],
            status=result["status"],
            is_revealed=result["is_revealed"],
            message=result["message"],
        ),
        message=result["message"],
    )

@router.get("/profile/{target_id}", response_model=SanctuaryResponse[ProfilePublicResponse])
async def get_seeker_public_profile(
    target_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    service: PhotoRevealService = Depends(get_photo_reveal_service),
):
    """Retrieves candidate public profile with DPDP fuzzed distance and verified reveal veil state."""
    # Assert not blocked
    blocked_stmt = select(BlockedUser).where(
        ((BlockedUser.blocker_id == current_user.id) & (BlockedUser.blocked_id == target_id))
        | ((BlockedUser.blocker_id == target_id) & (BlockedUser.blocked_id == current_user.id))
    )
    if (await db.execute(blocked_stmt)).scalar_one_or_none():
        raise SanctuaryException(
            error_code="SEEKER_BLOCKED",
            message="Cannot view blocked seeker profile.",
            status_code=403,
        )

    target_stmt = select(User).where(User.id == target_id)
    target = (await db.execute(target_stmt)).scalar_one_or_none()
    if not target:
        raise SanctuaryException(
            error_code="TARGET_NOT_FOUND",
            message="Target seeker does not exist.",
            status_code=404,
        )

    # Compute reveal state
    reveal_status = await service.get_photo_reveal_status(current_user.id, target_id, db)
    is_revealed = reveal_status["is_revealed"]

    # Calculate distance if coordinates exist
    distance_km = None
    if current_user.latitude and current_user.longitude and target.latitude and target.longitude:
        feed_svc = FeedService()
        lat1, lon1 = feed_svc.fuzz_coordinates(float(current_user.latitude), float(current_user.longitude))
        lat2, lon2 = feed_svc.fuzz_coordinates(float(target.latitude), float(target.longitude))
        distance_km = feed_svc.calculate_haversine_distance(lat1, lon1, lat2, lon2)

    profile_dict = {
        "id": target.id,
        "full_name": target.full_name,
        "dob": target.dob,
        "gender": target.gender,
        "interested_in": target.interested_in,
        "location_name": target.location_name,
        "bio": target.bio,
        "profession": target.profession,
        "education": target.education,
        "streak_count": target.streak_count,
        "boost_points": target.boost_points,
        "kyc_status": target.kyc_status,
        "is_photo_veiled": not is_revealed,
        "photos": (target.photos or []) if is_revealed else [],
        "avatar_url": target.avatar_url if is_revealed else None,
        "voice_spark_url": (
            f"/api/v1/media/voice/{target.id}/spark.m4a"
            if target.voice_spark_url
            else None
        ),
        "voice_spark_prompt": target.voice_spark_prompt,
        "voice_spark_duration": target.voice_spark_duration or Decimal("7.0"),
        "is_voice_verified": target.is_voice_verified,
        "distance_km": distance_km,
    }

    return SanctuaryResponse(
        data=ProfilePublicResponse.model_validate(profile_dict),
        message="Seeker profile loaded.",
    )
