import asyncio
from datetime import datetime, timedelta, timezone
import inspect
import re
from typing import Any, Dict, Optional, Set
import uuid
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Security, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
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

try:
    from ....core.limiter import limiter
except (ImportError, ValueError):
    from backend.app.core.limiter import limiter

security_bearer = HTTPBearer(auto_error=False)

# In-memory single-use audio token replay protection (VULN-MEDIA-06)
_consumed_audio_tokens: Set[str] = set()

async def get_media_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    token: Optional[str] = Query(None, description="Optional access token for audio players without header support"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Authenticates seeker via Bearer Authorization header, query parameter access token, or single-use audio token."""
    if get_current_user in request.app.dependency_overrides:
        override = request.app.dependency_overrides[get_current_user]
        if inspect.iscoroutinefunction(override):
            try:
                return await override()
            except TypeError:
                return await override(credentials, db)
        else:
            try:
                return override()
            except TypeError:
                return override(credentials, db)

    effective_credentials = credentials
    if (not effective_credentials or not effective_credentials.credentials) and token:
        # Check if single-use ephemeral audio token (VULN-MEDIA-06)
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
            if payload.get("type") == "media_audio":
                jti = payload.get("jti")
                if jti and jti in _consumed_audio_tokens:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Single-use audio token has already been consumed.",
                    )
                if jti:
                    _consumed_audio_tokens.add(jti)
                uid_str = payload.get("sub")
                if not uid_str:
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid audio token.")
                user_id = UUID(uid_str)
                user = await db.get(User, user_id)
                if not user or user.deleted_at is not None:
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Seeker inactive or deleted.")
                return user
        except (jwt.PyJWTError, ValueError):
            pass
        effective_credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    return await get_current_user(credentials=effective_credentials, db=db)

router = APIRouter()

@router.post(
    "/presigned-url",
    response_model=PresignedUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate S3v4 Presigned Direct Upload URL",
)
@limiter.limit("30/minute")
async def request_presigned_upload_url(
    request: Request,
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
    # Voice sparks are private audio assets protected by mutual match authorization; omit public CDN URL
    cdn_url = None if req.asset_type == "voice_spark" else storage.get_public_cdn_url(object_key)

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
    token: Optional[str] = Query(None, description="Optional access token for audio players without header support"),
    current_user: User = Depends(get_media_current_user),
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
    return RedirectResponse(
        url=url,
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        headers={
            "Referrer-Policy": "no-referrer",
            "Cache-Control": "no-store, private",
        },
    )


@router.post(
    "/voice/token",
    status_code=status.HTTP_200_OK,
    summary="Generate Ephemeral Single-Use Audio Streaming Token",
)
async def generate_voice_token(
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Issues a short-lived (60s) single-use audio streaming token to eliminate session JWT leakage in audio players (VULN-MEDIA-06)."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(current_user.id),
        "type": "media_audio",
        "jti": uuid.uuid4().hex,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=60)).timestamp()),
    }
    audio_token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return {
        "success": True,
        "token": audio_token,
        "expires_in": 60,
    }


@router.get(
    "/photo/{user_id}/{filename}",
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    summary="Access-Controlled Presigned Clear Photo Redirect",
)
async def redirect_clear_photo(
    user_id: UUID,
    filename: str,
    token: Optional[str] = Query(None, description="Optional access token"),
    current_user: User = Depends(get_media_current_user),
    storage: CloudflareR2StorageService = Depends(get_storage_service),
    session: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Redirects to ephemeral presigned GET URL for clear photo, requiring verified bilateral reveal consent (VULN-MEDIA-03)."""
    # 1. Filename validation
    if not re.fullmatch(r"slot_[1-5]\.webp|primary\.webp", filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid photo asset requested.",
        )

    # 2. Authorization: owner can access; peer requires bilateral photo reveal consent
    if current_user.id != user_id:
        try:
            from ....services.photo_reveal_service import get_photo_reveal_service
        except (ImportError, ValueError):
            from backend.app.services.photo_reveal_service import get_photo_reveal_service

        reveal_service = get_photo_reveal_service()
        reveal_status = await reveal_service.get_photo_reveal_status(current_user.id, user_id, session)
        if not reveal_status.get("is_revealed"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized: Bilateral photo reveal consent required to access clear photo.",
            )

    subpath = "moments" if filename.startswith("slot_") else "avatar"
    object_key = f"users/{user_id}/{subpath}/{filename}"

    try:
        url = await asyncio.to_thread(
            storage.generate_presigned_get_url,
            object_key,
            expires_in=300,
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate secure presigned URL for photo asset.",
        )

    return RedirectResponse(
        url=url,
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        headers={
            "Referrer-Policy": "no-referrer",
            "Cache-Control": "no-store, private",
        },
    )
