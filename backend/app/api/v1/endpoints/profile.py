from decimal import Decimal
from typing import Any, Dict
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from ....core.database import get_db
    from ....core.security import encrypt_contact_bridge
    from ....models.domain.user import User
    from ....schemas.base_response import SanctuaryResponse
    from ....schemas.profile import ProfileCreate
    from ...deps import get_current_user
except (ImportError, ValueError):
    from backend.app.core.database import get_db
    from backend.app.core.security import encrypt_contact_bridge
    from backend.app.models.domain.user import User
    from backend.app.schemas.base_response import SanctuaryResponse
    from backend.app.schemas.profile import ProfileCreate
    from backend.app.api.deps import get_current_user


router = APIRouter()


@router.post(
    "/create",
    response_model=SanctuaryResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Complete initial seeker profile onboarding",
)
async def create_profile(
    payload: ProfileCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SanctuaryResponse[Dict[str, Any]]:
    """Persists seeker onboarding details, encrypts contact bridge, and marks profile complete."""
    current_user.full_name = payload.full_name
    current_user.dob = payload.dob
    current_user.gender = payload.gender
    current_user.interested_in = payload.interested_in
    current_user.contact_bridge_type = payload.contact_bridge_type

    bridge_raw = payload.contact_bridge_handle or payload.contact_bridge_raw or ""
    current_user.contact_bridge_encrypted = encrypt_contact_bridge(bridge_raw)

    current_user.bio = payload.bio or ""
    current_user.profession = payload.profession or ""
    current_user.education = payload.education or ""
    current_user.photos = payload.photos or []

    if payload.avatar_url:
        current_user.avatar_url = payload.avatar_url
    elif payload.photos:
        current_user.avatar_url = payload.photos[0]

    if payload.latitude is not None:
        current_user.latitude = payload.latitude
    if payload.longitude is not None:
        current_user.longitude = payload.longitude

    if payload.voice_spark_url:
        current_user.voice_spark_url = payload.voice_spark_url
    if payload.voice_spark_duration is not None and payload.voice_spark_duration > 0:
        current_user.voice_spark_duration = Decimal(str(payload.voice_spark_duration))

    current_user.is_profile_completed = True

    await db.commit()
    await db.refresh(current_user)

    return SanctuaryResponse(
        data={
            "id": str(current_user.id),
            "is_profile_completed": current_user.is_profile_completed,
            "full_name": current_user.full_name,
            "avatar_url": current_user.avatar_url,
        },
        message="Profile setup completed successfully.",
    )
