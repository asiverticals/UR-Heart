import hashlib
from typing import List, Optional
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ....models.domain.legal import ConsentAuditLog
from ....models.domain.user import User
from ....schemas.base_response import SanctuaryResponse
from ....schemas.legal import (
    ConsentRecordRequest,
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


@router.post("/consent-record", response_model=SanctuaryResponse[dict])
async def record_statutory_consent(
    payload: ConsentRecordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SanctuaryResponse[dict]:
    """Records immutable affirmative consent audit log entry under DPDP Act 2023 Section 6."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    ip_hash = hashlib.sha256(client_ip.encode("utf-8")).hexdigest()
    installation_uuid = payload.installation_uuid or getattr(current_user, "last_installation_uuid", None) or "web_client"

    log_entry = ConsentAuditLog(
        user_id=current_user.id,
        consent_purpose_id=payload.consent_purpose_id,
        ip_hash=ip_hash,
        installation_uuid=installation_uuid,
    )
    db.add(log_entry)
    await db.commit()

    return SanctuaryResponse(
        data={"recorded": True, "purpose_id": payload.consent_purpose_id},
        message="Statutory affirmative consent logged under DPDP Act 2023 Section 6.",
    )


@router.get("/terms", response_model=SanctuaryResponse[dict])
async def get_terms_of_service() -> SanctuaryResponse[dict]:
    """Returns statutory Master Terms of Service metadata under IT Rules 2021 Rule 3(1)."""
    return SanctuaryResponse(
        data={
            "document": "Master Terms of Service",
            "entity": "ASI Verticals Private Limited",
            "jurisdiction": "Republic of India",
            "effective_date": "2026-10-15",
            "version": "1.0",
            "age_requirement": "18+",
            "dispute_venue": "New Delhi, India",
            "url": "https://urheart.app/terms",
        },
        message="Master Terms of Service metadata retrieved.",
    )


@router.get("/privacy", response_model=SanctuaryResponse[dict])
async def get_privacy_policy() -> SanctuaryResponse[dict]:
    """Returns statutory Privacy Policy & DPDP Data Notice under DPDP Act 2023 Sections 5 & 6."""
    return SanctuaryResponse(
        data={
            "document": "Privacy Policy & Statutory Data Notice",
            "fiduciary": "ASI Verticals Private Limited",
            "jurisdiction": "Republic of India",
            "effective_date": "2026-10-15",
            "version": "1.0",
            "data_retention_days": "Active account lifespan; financial 7 yrs (IT Act § 44AB); grievances 1 yr (IT Rules)",
            "languages_supported": [
                "English", "Hindi", "Bengali", "Telugu", "Marathi",
                "Tamil", "Gujarati", "Kannada", "Malayalam", "Odia", "Punjabi",
            ],
            "url": "https://urheart.app/privacy",
        },
        message="Privacy Policy and DPDP statutory notice retrieved.",
    )


@router.get("/grievance-officer", response_model=SanctuaryResponse[dict])
async def get_grievance_officer() -> SanctuaryResponse[dict]:
    """Returns designated Resident Grievance Officer details under IT Rules 2021 Rule 3(2)(a)."""
    return SanctuaryResponse(
        data={
            "title": "Resident Grievance Officer & Legal Counsel",
            "entity": "ASI Verticals Private Limited",
            "email": "grievance@urheart.app",
            "redressal_desk_email": "legal@urheart.app",
            "telephone": "+91-120-4567890",
            "hours": "Mon-Fri 10:00 AM - 6:00 PM IST",
            "emergency_takedown_sla_hours": 24,
            "general_resolution_sla_days": 15,
            "appellate_portal": "https://gac.gov.in",
        },
        message="Resident Grievance Officer contact particulars retrieved.",
    )


@router.get("/refund-policy", response_model=SanctuaryResponse[dict])
async def get_refund_policy() -> SanctuaryResponse[dict]:
    """Returns Refund, Cancellation & Micro-Transaction Policy under Consumer Protection Rules 2020."""
    return SanctuaryResponse(
        data={
            "document": "Refund, Cancellation & Micro-Transaction Policy",
            "entity": "ASI Verticals Private Limited",
            "effective_date": "2026-10-15",
            "processing_window_hours": 48,
            "settlement_window_days": "5-7 business days",
            "billing_email": "billing@urheart.app",
            "url": "https://urheart.app/refund",
        },
        message="Refund and cancellation policy retrieved.",
    )

