from datetime import datetime, timezone, timedelta
import hashlib
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.exceptions import SanctuaryException
from ....models.domain.legal import ConsentAuditLog, GrievanceDossier
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
    EmergencyTakedownRequest,
    EmergencyTakedownResponse,
)
from ....services.legal_vault_service import legal_vault_service
from ...deps import get_current_user, get_db
try:
    from ....core.limiter import limiter
except (ImportError, ValueError):
    from backend.app.core.limiter import limiter

router = APIRouter()


@router.post("/nominee", response_model=SanctuaryResponse[NomineeResponse])
async def register_nominee(
    payload: DataNomineeRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SanctuaryResponse[NomineeResponse]:
    """Registers or updates digital nominee under DPDP Act 2023 Section 14."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    data = await legal_vault_service.register_or_update_nominee(
        current_user, payload, db, client_ip=client_ip
    )
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


@router.post("/emergency-takedown", response_model=SanctuaryResponse[EmergencyTakedownResponse])
@limiter.limit("10/minute")
async def emergency_takedown(
    request: Request,
    payload: EmergencyTakedownRequest,
    db: AsyncSession = Depends(get_db),
) -> SanctuaryResponse[EmergencyTakedownResponse]:
    """Public emergency 24-hour takedown portal under IT Rules 2021 Rule 3(2)(b) for NCII and explicit content."""
    # VULN-DPDP-05: Handle non-existent target user gracefully (404 instead of 500)
    if payload.reported_user_id:
        target = await db.get(User, payload.reported_user_id)
        if not target:
            raise SanctuaryException(
                error_code="TARGET_USER_NOT_FOUND",
                message="The reported seeker account does not exist.",
                status_code=404,
            )

    now = datetime.now(timezone.utc)
    takedown_deadline = now + timedelta(hours=24)
    dossier_ref = f"NCII-EMG-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

    narrative = (
        f"EMERGENCY 24-HR TAKEDOWN COMPLAINT [IT Rules 2021 Rule 3(2)(b)]\n"
        f"Complainant: {payload.complainant_name} <{payload.complainant_email}>\n"
        f"Phone: {payload.complainant_phone or 'Not Provided'}\n"
        f"Reported Handle/Name: {payload.reported_handle_or_name or 'N/A'}\n"
        f"Offending Media URL: {payload.evidence_media_url or 'N/A'}\n"
        f"Statement: {payload.evidence_text.strip()}"
    )

    dossier = GrievanceDossier(
        dossier_reference_id=dossier_ref,
        reporter_id=None,
        reported_user_id=payload.reported_user_id,
        violation_category=payload.violation_category,
        evidence_text=payload.evidence_text.strip(),
        statutory_notes=narrative,
        status="acknowledged",
        acknowledgment_sent_at=now,
        statutory_resolution_due_at=takedown_deadline,
        sla_deadline_at=takedown_deadline,
    )
    db.add(dossier)
    await db.commit()

    return SanctuaryResponse(
        data=EmergencyTakedownResponse(
            dossier_reference_id=dossier_ref,
            status="acknowledged",
            statutory_sla_hours=24,
            emergency_takedown_due_at=takedown_deadline.isoformat(),
            message="Emergency 24-hour takedown complaint registered. Takedown review initiated immediately pursuant to Rule 3(2)(b).",
        ),
        message="Emergency statutory complaint acknowledged. Action required within 24 hours.",
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
@limiter.limit("2/minute")
async def export_personal_data(
    request: Request,
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
            "name": "Anubhav Singh",
            "title": "Resident Grievance Officer & Legal Counsel",
            "entity": "ASI Verticals Private Limited",
            "physical_address": "Chambers of Resident Legal Counsel, Ayodhya District Court, Ayodhya, Uttar Pradesh 224001, India",
            "email": "asiverticals@gmail.com",
            "redressal_desk_email": "asiverticals@gmail.com",
            "telephone": None,
            "hours": "Mon-Fri 10:00 AM - 6:00 PM IST",
            "emergency_takedown_sla_hours": 24,
            "general_resolution_sla_days": 15,
            "appellate_portal": "https://gac.gov.in",
        },
        message="Resident Grievance Officer contact particulars retrieved.",
    )


@router.get("/refund-policy", response_model=SanctuaryResponse[dict])
async def get_refund_policy() -> SanctuaryResponse[dict]:
    """Returns Strict No-Refund & Digital Consumable Finality Policy under Consumer Protection Rules 2020."""
    return SanctuaryResponse(
        data={
            "document": "Strict No-Refund & Digital Consumable Finality Policy",
            "entity": "ASI Verticals Private Limited",
            "effective_date": "2026-10-15",
            "policy_type": "no_refund",
            "terms": "All purchases of digital consumables, sparks, roses, revelation passes, and sanctuary micro-transactions are final, immediate, and non-refundable once credited to seeker vault.",
            "billing_email": "asiverticals@gmail.com",
            "support_email": "asiverticals@gmail.com",
            "url": "https://urheart.app/refund",
        },
        message="Strict no-refund policy retrieved.",
    )


