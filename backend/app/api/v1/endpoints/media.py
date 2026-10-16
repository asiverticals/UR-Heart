import asyncio
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Path, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from ....core.config import settings
    from ....core.database import get_db
    from ....models.domain.user import User
    from ....schemas.media import (
        MAX_IMAGE_BYTES,
        MAX_VOICE_BYTES,
        PresignedUploadRequest,
        PresignedUploadResponse,
        MomentDeleteResponse,
    )
    from ....services.storage_service import (
        CloudflareR2StorageService,
        get_storage_service,
    )
    from ...deps import get_current_user
except (ImportError, ValueError):
    from backend.app.core.config import settings
    from backend.app.core.database import get_db
    from backend.app.models.domain.user import User
    from backend.app.schemas.media import (
        MAX_IMAGE_BYTES,
        MAX_VOICE_BYTES,
        PresignedUploadRequest,
        PresignedUploadResponse,
        MomentDeleteResponse,
    )
    from backend.app.services.storage_service import (
        CloudflareR2StorageService,
        get_storage_service,
    )
    from backend.app.api.deps import get_current_user

router = APIRouter()

@router.post(
    "/presigned-url",
    response_model=PresignedUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate S3v4 Presigned Direct Upload URL",
)
async def request_presigned_upload_url(
    req: PresignedUploadRequest,
    current_user: User = Depends(get_current_user),
    storage: CloudflareR2StorageService = Depends(get_storage_service),
) -> PresignedUploadResponse:
    """Generates an S3v4 Presigned PUT URL allowing clients to upload directly to Cloudflare R2."""
    if req.asset_type == "moment":
        object_key = f"users/{current_user.id}/moments/slot_{req.slot_number}.webp"
        max_bytes = MAX_IMAGE_BYTES
    elif req.asset_type == "avatar":
        object_key = f"users/{current_user.id}/avatar/primary.webp"
        max_bytes = MAX_IMAGE_BYTES
    else:  # voice_spark
        object_key = f"users/{current_user.id}/voice/spark.m4a"
        max_bytes = MAX_VOICE_BYTES

    upload_url = await asyncio.to_thread(
        storage.generate_presigned_put_url,
        key=object_key,
        content_type=req.content_type,
        content_length=req.file_size_bytes,
        expires_in=300,
    )
    cdn_url = storage.get_public_cdn_url(object_key)

    return PresignedUploadResponse(
        success=True,
        upload_url=upload_url,
        public_cdn_url=cdn_url,
        object_key=object_key,
        expires_in=300,
        max_bytes=max_bytes,
    )

@router.delete(
    "/moment/{slot_number}",
    response_model=MomentDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete a Moment Media Asset",
)
async def delete_moment_asset(
    slot_number: int = Path(..., ge=1, le=5, description="Moment slot to purge"),
    current_user: User = Depends(get_current_user),
    storage: CloudflareR2StorageService = Depends(get_storage_service),
    db: AsyncSession = Depends(get_db),
) -> MomentDeleteResponse:
    """Deletes a moment photo from Cloudflare R2 off the event loop and removes URL reference from the seeker profile."""
    object_key = f"users/{current_user.id}/moments/slot_{slot_number}.webp"

    # Offload blocking boto3 I/O to worker thread pool
    await asyncio.to_thread(storage.delete_object, object_key)

    if current_user.photos:
        target_substr = f"slot_{slot_number}.webp"
        updated_photos = [p for p in current_user.photos if target_substr not in p]
        if len(updated_photos) != len(current_user.photos):
            current_user.photos = updated_photos
            await db.commit()

    return MomentDeleteResponse(
        success=True,
        slot_number=slot_number,
        deleted=True,
    )

@router.get(
    "/voice/{user_id}/{filename}",
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    summary="Redirect to Cloudflare Edge CDN for Voice Spark Audio",
)
async def redirect_voice_spark(
    user_id: UUID,
    filename: str,
    current_user: User = Depends(get_current_user),
    storage: CloudflareR2StorageService = Depends(get_storage_service),
    session: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Performs HTTP 307 temporary redirect to access-controlled presigned URL for Voice Spark streaming."""
    # Authorization check: Seeker can access own voice spark; accessing another seeker's
    # voice spark requires an active mutual match.
    if current_user.id != user_id:
        from sqlalchemy import select, or_, and_
        try:
            from ....models.domain.match_and_chat import Match
        except (ImportError, ValueError):
            from backend.app.models.domain.match_and_chat import Match

        stmt = select(Match).where(
            or_(
                and_(Match.user1_id == current_user.id, Match.user2_id == user_id),
                and_(Match.user1_id == user_id, Match.user2_id == current_user.id),
            ),
            Match.is_active.is_(True),
        )
        res = await session.execute(stmt)
        if not res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized: You do not have permission to access this voice spark.",
            )

    # Restrict presigning strictly to legitimate spark.m4a object key (Issue #5)
    if filename != "spark.m4a":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid voice spark asset requested.",
        )

    try:
        url = await asyncio.to_thread(
            storage.generate_presigned_get_url,
            f"users/{user_id}/voice/spark.m4a",
            expires_in=300,
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate secure presigned URL for voice spark audio.",
        )
    return RedirectResponse(url=url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
