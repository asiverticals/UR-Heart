import time
from typing import Optional
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.exceptions import SanctuaryException
from ....core.limiter import limiter
from ....core.security import decode_access_token
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
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    incineration_service: AccountIncinerationService = Depends(get_account_incineration_service),
) -> SanctuaryResponse[dict]:
    """Irrevocably incinerates the authenticated seeker's persona, moments, and data.

    Enforces mandatory confirmation phrase 'PERMANENTLY INCINERATE', step-up re-authentication
    (fresh token or reauth header), and triggers Cloudflare R2 cascade deletion and relational
    row purge under DPDP Act 2023 Section 12.
    """
    # VULN-DPDP-02: Step-up re-authentication invariant
    # Require fresh token (< 300s since issuance) or step-up re-auth header
    auth_header = request.headers.get("authorization", "")
    raw_token = auth_header.split(" ", 1)[1].strip() if " " in auth_header else ""
    token_payload = decode_access_token(raw_token) if raw_token else None

    is_fresh = False
    if token_payload:
        iat = token_payload.get("iat")
        if iat is not None and (time.time() - iat) <= 300 and token_payload.get("fresh") is not False:
            is_fresh = True

    if not is_fresh:
        # Check step-up header (X-Reauth-Token or X-Step-Up-Token or X-Reauth-Password)
        reauth_token = (
            request.headers.get("x-reauth-token")
            or request.headers.get("x-step-up-token")
            or request.headers.get("x-reauth-password")
        )
        if reauth_token:
            reauth_payload = decode_access_token(reauth_token)
            if reauth_payload and str(reauth_payload.get("sub")) == str(current_user.id):
                reauth_iat = reauth_payload.get("iat")
                if reauth_iat and (time.time() - reauth_iat) <= 300:
                    is_fresh = True

        if not is_fresh:
            raise SanctuaryException(
                error_code="STEP_UP_REAUTH_REQUIRED",
                message="Step-up re-authentication required before account incineration. Please confirm credentials.",
                status_code=403,
            )

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
