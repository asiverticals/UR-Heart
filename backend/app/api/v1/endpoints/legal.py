from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ....models.domain.user import User
from ....schemas.base_response import SanctuaryResponse
from ....schemas.legal import (
    DataNomineeRequest,
    NomineeResponse,
    GrievanceSubmitRequest,
    GrievanceResponse,
    GrievanceDossierItem,
    DataExportResponse,
)
from ....services.legal_vault_service import legal_vault_service
from ...deps import get_current_user, get_db

router = APIRouter()


@router.post("/nominee", response_model=SanctuaryResponse[NomineeResponse])
async def register_nominee(
    payload: DataNomineeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SanctuaryResponse[NomineeResponse]:
    """Registers or updates digital nominee under DPDP Act 2023 Section 14."""
    data = await legal_vault_service.register_or_update_nominee(current_user, payload, db)
    return SanctuaryResponse(
        data=NomineeResponse(**data),
        message="Digital nominee designated under DPDP Act 2023 Section 14.",
    )


@router.get("/nominee", response_model=SanctuaryResponse[Optional[NomineeResponse]])
async def get_nominee(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SanctuaryResponse[Optional[NomineeResponse]]:
    """Retrieves current digital nominee designation or null if unassigned."""
    data = await legal_vault_service.get_nominee(current_user, db)
    return SanctuaryResponse(
        data=NomineeResponse(**data) if data else None,
        message="Digital nominee record retrieved.",
    )


@router.post("/grievance", response_model=SanctuaryResponse[GrievanceResponse])
async def submit_grievance(
    payload: GrievanceSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SanctuaryResponse[GrievanceResponse]:
    """Submits a statutory grievance dossier under IT Rules 2021 Rule 3(2) & DPDP Act 2023."""
    data = await legal_vault_service.submit_grievance(current_user, payload, db)
    return SanctuaryResponse(
        data=GrievanceResponse(**data),
        message="Statutory grievance dossier acknowledged under IT Rules 2021 Rule 3(2).",
    )


@router.get("/grievances", response_model=SanctuaryResponse[List[GrievanceDossierItem]])
async def list_grievances(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SanctuaryResponse[List[GrievanceDossierItem]]:
    """Lists all grievances filed by the seeker with SLA countdown metrics."""
    data = await legal_vault_service.get_user_grievances(current_user, db)
    items = [GrievanceDossierItem(**g) for g in data]
    return SanctuaryResponse(
        data=items,
        message="Seeker statutory grievance dossiers loaded.",
    )


@router.post("/data-export", response_model=SanctuaryResponse[DataExportResponse])
async def export_personal_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SanctuaryResponse[DataExportResponse]:
    """Generates machine-readable Subject Access Request (SAR) export under DPDP Section 11."""
    data = await legal_vault_service.compile_data_portability_package(current_user, db)
    return SanctuaryResponse(
        data=DataExportResponse(**data),
        message="DPDP Act 2023 Section 11 machine-readable data export generated.",
    )
