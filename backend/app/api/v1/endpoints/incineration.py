from typing import Optional
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.limiter import limiter
from ....models.domain.user import User
from ....schemas.base_response import SanctuaryResponse
from ....schemas.legal import (
    AccountIncinerateRequest,
    MagicLinkVerifyRequest,
    WebAccountDeletionRequest,
)
from ....services.account_incineration_service import (
    AccountIncinerationService,
    get_account_incineration_service,
)
from ...deps import get_current_user, get_db

router = APIRouter()


@router.delete(
    "/account",
    response_model=SanctuaryResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Cryptographic Account Incineration under DPDP Act 2023 Section 12",
)
async def incinerate_account(
    payload: AccountIncinerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    incineration_service: AccountIncinerationService = Depends(get_account_incineration_service),
) -> SanctuaryResponse[dict]:
    """Irrevocably incinerates the authenticated seeker's persona, moments, and data.

    Enforces mandatory confirmation phrase 'PERMANENTLY INCINERATE' and triggers
    Cloudflare R2 cascade deletion and relational row purge under DPDP Act 2023 Section 12.
    """
    result = await incineration_service.execute_account_incineration(
        current_user.id,
        db,
    )
    return SanctuaryResponse(
        data={
            "status": "incinerated",
            "message": "Sacred identity permanently erased from sanctuary.",
            "certificate": result["certificate"],
            "incinerated_at": result["incinerated_at"],
        },
        message="Sacred identity permanently erased from sanctuary.",
    )


@router.post(
    "/web-account-deletion",
    response_model=SanctuaryResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Out-of-app web account deletion initiation (Apple Guideline 5.1.1(v) & Google Play Policy)",
)
@limiter.limit("5/15minute")
async def request_web_account_deletion(
    request: Request,
    payload: WebAccountDeletionRequest,
    db: AsyncSession = Depends(get_db),
    incineration_service: AccountIncinerationService = Depends(get_account_incineration_service),
) -> SanctuaryResponse[dict]:
    """Dispatches a statutory 15-minute verification link to the seeker's registered email."""
    await incineration_service.dispatch_web_deletion_magic_link(
        payload.email,
        db,
        reason=payload.reason,
    )
    return SanctuaryResponse(
        data={
            "dispatched": True,
            "message": "Statutory verification link dispatched to your email.",
        },
        message="Statutory verification link dispatched to your email.",
    )


@router.post(
    "/web-account-deletion/confirm",
    response_model=SanctuaryResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Confirm statutory web account deletion via magic link token",
)
async def confirm_web_account_deletion(
    payload: MagicLinkVerifyRequest,
    db: AsyncSession = Depends(get_db),
    incineration_service: AccountIncinerationService = Depends(get_account_incineration_service),
) -> SanctuaryResponse[dict]:
    """Validates the web verification token and executes complete account incineration."""
    result = await incineration_service.confirm_web_deletion(
        payload.token,
        db,
    )
    return SanctuaryResponse(
        data={
            "status": "incinerated",
            "message": "Account incinerated via web statutory verification.",
            "certificate": result["certificate"],
            "incinerated_at": result["incinerated_at"],
        },
        message="Account incinerated via web statutory verification.",
    )
