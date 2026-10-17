from decimal import Decimal
import re
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from ....core.database import get_db
    from ....core.exceptions import SanctuaryException
    from ....core.security import encrypt_contact_bridge
    from ....models.domain.user import User
    from ....schemas.base_response import SanctuaryResponse
    from ....schemas.profile import ProfileCreate, ProfileUpdate, ProfileResponse
    from ...deps import get_current_user
except (ImportError, ValueError):
    from backend.app.core.database import get_db
    from backend.app.core.exceptions import SanctuaryException
    from backend.app.core.security import encrypt_contact_bridge
    from backend.app.models.domain.user import User
    from backend.app.schemas.base_response import SanctuaryResponse
    from backend.app.schemas.profile import ProfileCreate, ProfileUpdate, ProfileResponse
    from backend.app.api.deps import get_current_user


router = APIRouter()

_UUID_PATTERN = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)


def _validate_user_media_ownership(url: Optional[str], user_id: Any, field_name: str) -> None:
    """Strictly prevents cross-tenant media key binding or identity hijacking."""
    if not url:
        return
    user_str = str(user_id)
    # 1. Cloudflare R2 / S3 path: users/{uuid}/...
    if "users/" in url and f"users/{user_str}/" not in url:
        raise SanctuaryException(
            error_code="CROSS_TENANT_MEDIA_FORBIDDEN",
            message=f"Unauthorized: {field_name} must belong to authenticated seeker.",
            status_code=status.HTTP_403_FORBIDDEN,
        )
    # 2. Prevent binding another user's UUID in media / streaming proxy URLs
    found_uuids = _UUID_PATTERN.findall(url)
    for found_uuid in found_uuids:
        if found_uuid.lower() != user_str.lower():
            raise SanctuaryException(
                error_code="CROSS_TENANT_MEDIA_FORBIDDEN",
                message=f"Unauthorized: {field_name} must belong to authenticated seeker.",
                status_code=status.HTTP_403_FORBIDDEN,
            )


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
    if current_user.is_profile_completed:
        raise SanctuaryException(
            error_code="PROFILE_ALREADY_COMPLETED",
            message="Seeker profile has already been onboarded.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Validate media ownership against cross-tenant hijacking
    if payload.photos:
        for p in payload.photos:
            _validate_user_media_ownership(p, current_user.id, "photos")
    if payload.avatar_url:
        _validate_user_media_ownership(payload.avatar_url, current_user.id, "avatar_url")
    if payload.voice_spark_url:
        _validate_user_media_ownership(payload.voice_spark_url, current_user.id, "voice_spark_url")

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


@router.put(
    "",
    response_model=SanctuaryResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Update seeker profile details",
)
@router.put(
    "/",
    response_model=SanctuaryResponse[Dict[str, Any]],
    include_in_schema=False,
)
async def update_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SanctuaryResponse[Dict[str, Any]]:
    """Updates mutable seeker profile fields, handles contact bridge re-encryption, and returns updated state."""
    if not current_user.is_profile_completed:
        raise SanctuaryException(
            error_code="PROFILE_NOT_COMPLETED",
            message="Seeker profile has not been completed. Complete onboarding via /create first.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    update_data = payload.model_dump(exclude_unset=True)

    if "full_name" in update_data and payload.full_name is not None:
        current_user.full_name = payload.full_name.strip()

    if "bio" in update_data and payload.bio is not None:
        current_user.bio = payload.bio.strip()

    if "profession" in update_data and payload.profession is not None:
        current_user.profession = payload.profession.strip()

    if "education" in update_data and payload.education is not None:
        current_user.education = payload.education.strip()

    if "gender" in update_data and payload.gender is not None:
        current_user.gender = payload.gender

    if "interested_in" in update_data and payload.interested_in is not None:
        current_user.interested_in = payload.interested_in

    if "photos" in update_data and payload.photos is not None:
        for p in payload.photos:
            _validate_user_media_ownership(p, current_user.id, "photos")
        current_user.photos = payload.photos
        if not payload.avatar_url and payload.photos:
            current_user.avatar_url = payload.photos[0]

    if "avatar_url" in update_data and payload.avatar_url is not None:
        _validate_user_media_ownership(payload.avatar_url, current_user.id, "avatar_url")
        current_user.avatar_url = payload.avatar_url

    lat = payload.latitude if payload.latitude is not None else payload.location_lat
    if lat is not None:
        current_user.latitude = lat

    lon = payload.longitude if payload.longitude is not None else payload.location_lon
    if lon is not None:
        current_user.longitude = lon

    loc_name = payload.location_name if payload.location_name is not None else payload.city
    if loc_name is not None:
        current_user.location_name = loc_name.strip()

    if "voice_spark_url" in update_data and payload.voice_spark_url is not None:
        _validate_user_media_ownership(payload.voice_spark_url, current_user.id, "voice_spark_url")
        current_user.voice_spark_url = payload.voice_spark_url

    if "voice_spark_duration" in update_data and payload.voice_spark_duration is not None:
        if payload.voice_spark_duration > 0:
            current_user.voice_spark_duration = Decimal(str(payload.voice_spark_duration))

    if "voice_spark_prompt" in update_data and payload.voice_spark_prompt is not None:
        current_user.voice_spark_prompt = payload.voice_spark_prompt.strip()

    if "contact_bridge_type" in update_data and payload.contact_bridge_type is not None:
        current_user.contact_bridge_type = payload.contact_bridge_type

    bridge_raw = (
        payload.contact_bridge_handle
        or payload.contact_bridge_raw
        or payload.contact_bridge
    )
    if bridge_raw and len(bridge_raw.strip()) >= 3:
        current_user.contact_bridge_encrypted = encrypt_contact_bridge(bridge_raw.strip())

    if "preferred_age_min" in update_data or "preferred_age_max" in update_data:
        candidate_min = (
            payload.preferred_age_min
            if ("preferred_age_min" in update_data and payload.preferred_age_min is not None)
            else current_user.preferred_age_min
        )
        candidate_max = (
            payload.preferred_age_max
            if ("preferred_age_max" in update_data and payload.preferred_age_max is not None)
            else current_user.preferred_age_max
        )
        if candidate_min is not None and candidate_max is not None and candidate_min > candidate_max:
            raise SanctuaryException(
                error_code="INVALID_AGE_RANGE",
                message="preferred_age_min cannot exceed preferred_age_max.",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        if "preferred_age_min" in update_data and payload.preferred_age_min is not None:
            current_user.preferred_age_min = candidate_min
        if "preferred_age_max" in update_data and payload.preferred_age_max is not None:
            current_user.preferred_age_max = candidate_max

    if "is_photo_veiled" in update_data and payload.is_photo_veiled is not None:
        current_user.is_photo_veiled = payload.is_photo_veiled

    if "discreet_mode" in update_data and payload.discreet_mode is not None:
        current_user.discreet_mode = payload.discreet_mode

    if "night_slumber" in update_data and payload.night_slumber is not None:
        current_user.night_slumber = payload.night_slumber

    if "passport_city" in update_data and payload.passport_city is not None:
        current_user.passport_city = payload.passport_city

    await db.commit()
    await db.refresh(current_user)

    return SanctuaryResponse(
        data={
            "id": str(current_user.id),
            "is_profile_completed": current_user.is_profile_completed,
            "full_name": current_user.full_name,
            "avatar_url": current_user.avatar_url,
            "bio": current_user.bio,
            "profession": current_user.profession,
            "education": current_user.education,
            "photos": current_user.photos,
            "gender": current_user.gender,
            "interested_in": current_user.interested_in,
            "contact_bridge_type": current_user.contact_bridge_type,
            "location_name": current_user.location_name,
            "latitude": float(current_user.latitude) if current_user.latitude is not None else None,
            "longitude": float(current_user.longitude) if current_user.longitude is not None else None,
            "voice_spark_url": current_user.voice_spark_url,
            "voice_spark_duration": float(current_user.voice_spark_duration) if current_user.voice_spark_duration is not None else None,
            "voice_spark_prompt": current_user.voice_spark_prompt,
            "preferred_age_min": current_user.preferred_age_min,
            "preferred_age_max": current_user.preferred_age_max,
            "is_photo_veiled": current_user.is_photo_veiled,
            "discreet_mode": current_user.discreet_mode,
            "night_slumber": current_user.night_slumber,
            "passport_city": current_user.passport_city,
        },
        message="Profile updated successfully.",
    )

