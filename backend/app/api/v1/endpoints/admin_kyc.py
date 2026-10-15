import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.exceptions import SanctuaryException
from ....models.domain.user import User
from ....schemas.admin import (
    AdminKycDecisionRequest,
    AdminKycDecisionResponse,
    AdminKycEscalationItem,
)
from ....schemas.base_response import SanctuaryResponse
from ....services.admin_service import AdminService
from ....services.storage_service import UnifiedStorageService, get_storage_service
from ...deps import get_current_superadmin

logger = logging.getLogger("urheart.admin_kyc")

router = APIRouter()

def get_admin_service(
    storage_service: UnifiedStorageService = Depends(get_storage_service),
) -> AdminService:
    return AdminService(storage_service=storage_service)


@router.get(
    "/escalations",
    response_model=SanctuaryResponse[List[AdminKycEscalationItem]],
    summary="List pending biometric KYC escalations for manual superadmin adjudication",
)
async def list_pending_escalations(
    current_superadmin: User = Depends(get_current_superadmin),
    session: AsyncSession = Depends(get_db),
    admin_service: AdminService = Depends(get_admin_service),
) -> SanctuaryResponse[List[AdminKycEscalationItem]]:
    """Retrieves all pending borderline KYC escalations, generating 15-minute presigned review URLs."""
    items = await admin_service.get_pending_escalations(session)
    return SanctuaryResponse(
        data=items,
        message=f"Retrieved {len(items)} pending KYC escalations for adjudication.",
    )


@router.post(
    "/{escalation_id}/decide",
    response_model=SanctuaryResponse[AdminKycDecisionResponse],
    summary="Adjudicate pending biometric KYC escalation (approve or reject)",
)
async def decide_escalation(
    escalation_id: str,
    payload: AdminKycDecisionRequest,
    background_tasks: BackgroundTasks,
    current_superadmin: User = Depends(get_current_superadmin),
    session: AsyncSession = Depends(get_db),
    admin_service: AdminService = Depends(get_admin_service),
) -> SanctuaryResponse[AdminKycDecisionResponse]:
    """Manually adjudicates a borderline KYC escalation ticket.
    
    Approval sets user.kyc_status = True, while rejection sets it to False.
    Immediately dispatches DPDP Section 8 permanent purge of the ephemeral live capture frame.
    """
    result = await admin_service.decide_escalation(
        session=session,
        escalation_id=escalation_id,
        decision=payload.decision,
        reviewer=current_superadmin,
        background_tasks=background_tasks,
        notes=payload.reviewer_notes,
    )
    return SanctuaryResponse(
        data=result,
        message=result.message,
    )


@router.post(
    "/resolve",
    response_model=SanctuaryResponse[AdminKycDecisionResponse],
    summary="Legacy compatible resolve endpoint for biometric escalation",
)
async def resolve_escalation(
    payload: AdminKycDecisionRequest,
    background_tasks: BackgroundTasks,
    user_id: Optional[str] = None,
    current_superadmin: User = Depends(get_current_superadmin),
    session: AsyncSession = Depends(get_db),
    admin_service: AdminService = Depends(get_admin_service),
) -> SanctuaryResponse[AdminKycDecisionResponse]:
    target_id = user_id or payload.user_id
    if not target_id:
        raise SanctuaryException(
            error_code="INVALID_TARGET_SEEKER",
            message="Target user_id or escalation_id is required to resolve escalation.",
            status_code=400,
        )
    result = await admin_service.decide_escalation(
        session=session,
        escalation_id=str(target_id),
        decision=payload.decision,
        reviewer=current_superadmin,
        background_tasks=background_tasks,
        notes=payload.reviewer_notes,
    )
    return SanctuaryResponse(
        data=result,
        message=result.message,
    )
