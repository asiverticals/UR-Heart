from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from ....core.database import get_db
    from ....core.limiter import limiter
    from ....models.domain.user import User
    from ....schemas.auth import (
        GoogleSyncRequest,
        MagicLinkSendRequest,
        MagicLinkVerifyRequest,
        RefreshTokenRequest,
        RegisterIntentRequest,
        TokenResponse,
    )
    from ....schemas.base_response import SanctuaryResponse
    from ....services.auth_service import auth_service
    from ...deps import get_current_user
except (ImportError, ValueError):
    from backend.app.core.database import get_db
    from backend.app.core.limiter import limiter
    from backend.app.models.domain.user import User
    from backend.app.schemas.auth import (
        GoogleSyncRequest,
        MagicLinkSendRequest,
        MagicLinkVerifyRequest,
        RefreshTokenRequest,
        RegisterIntentRequest,
        TokenResponse,
    )
    from backend.app.schemas.base_response import SanctuaryResponse
    from backend.app.services.auth_service import auth_service
    from backend.app.api.deps import get_current_user


router = APIRouter()

@router.post(
    "/register-intent",
    response_model=SanctuaryResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Validate 18+ statutory age gate and device hardware quarantine",
)
async def register_intent(
    payload: RegisterIntentRequest,
    db: AsyncSession = Depends(get_db),
) -> SanctuaryResponse[Dict[str, Any]]:
    """Evaluates 18+ age criteria and intercepts quarantined hardware fingerprints."""
    res = await auth_service.verify_registration_eligibility(
        dob=payload.dob,
        device_fingerprint=payload.device_fingerprint,
        session=db,
    )
    return SanctuaryResponse(data=res, message=res.get("message", "Age criteria satisfied."))

@router.post(
    "/google-sync",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Exchange Google OAuth2 RS256 token for Sanctuary Bearer tokens",
)
async def google_sync(
    payload: GoogleSyncRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Verifies RS256 Google token, maps UUID v5 deterministically, and issues tokens."""
    return await auth_service.authenticate_google_user(
        id_token=payload.id_token,
        installation_uuid=payload.installation_uuid,
        session=db,
        dob=payload.dob,
    )

@router.post(
    "/send-magic-link",
    response_model=SanctuaryResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Issue passwordless single-use authentication magic link",
)
@limiter.limit("5/minute")
async def send_magic_link(
    request: Request,
    payload: MagicLinkSendRequest,
    db: AsyncSession = Depends(get_db),
) -> SanctuaryResponse[Dict[str, Any]]:
    """Generates a cryptographic 15-minute token and logs/dispatches the link."""
    await auth_service.send_magic_link_email(email=payload.email, session=db)
    return SanctuaryResponse(
        data={"dispatched": True},
        message="Magic link dispatched.",
    )

@router.post(
    "/verify-magic-link",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Exchange single-use magic link token for session tokens",
)
async def verify_magic_link(
    payload: MagicLinkVerifyRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Validates single-use token, provisions or retrieves seeker, and issues session tokens."""
    return await auth_service.verify_magic_link_token(token=payload.token, session=db)

@router.get(
    "/me",
    response_model=SanctuaryResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Retrieve authenticated seeker identity and profile status",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> SanctuaryResponse[Dict[str, Any]]:
    """Returns profile and identity data for the current authenticated seeker."""
    profile_data = {
        "id": str(current_user.id),
        "auth_id": str(current_user.auth_id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "is_profile_completed": current_user.is_profile_completed,
        "kyc_status": current_user.kyc_status,
        "streak_count": current_user.streak_count,
        "subscription_tier": current_user.subscription_tier,
    }
    return SanctuaryResponse(data=profile_data, message="Authenticated profile retrieved.")

@router.get(
    "/sync",
    response_model=SanctuaryResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Verify session validity and update client installation UUID",
)
async def sync_session(
    installation_uuid: Optional[str] = Query(None, max_length=64),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SanctuaryResponse[Dict[str, Any]]:
    """Performs session heartbeat and syncs client installation UUID."""
    if installation_uuid and current_user.last_installation_uuid != installation_uuid:
        current_user.last_installation_uuid = installation_uuid
        await db.commit()

    return SanctuaryResponse(
        data={
            "active": True,
            "user_id": str(current_user.id),
            "is_profile_completed": current_user.is_profile_completed,
        },
        message="Session active and synchronized.",
    )

@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh expired session tokens using a valid refresh token",
)
async def refresh_token(
    payload: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Validates incoming HS256 refresh token and issues fresh access and refresh tokens."""
    return await auth_service.refresh_user_token(
        refresh_token=payload.refresh_token,
        session=db,
    )

