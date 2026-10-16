import hashlib
import json
import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.exceptions import SanctuaryException
from ..models.domain.user import User
from ..models.domain.legal import (
    DataNominee,
    GrievanceDossier,
    ConsentAuditLog,
    DataExportRequest,
)
from ..models.domain.match_and_chat import Match
from ..models.domain.monetization import InAppPurchase
from ..schemas.legal import (
    DataNomineeRequest,
    GrievanceSubmitRequest,
)

logger = logging.getLogger("SanctuaryLegalVault")


class LegalVaultService:
    """Domain service orchestrating DPDP Act 2023 & IT Rules 2021 statutory rights."""

    @staticmethod
    def generate_dossier_reference() -> str:
        """Generates unique, tamper-evident reference: URH-GRV-{YYYYMMDD}-{HEX6}."""
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        hex_suffix = secrets.token_hex(3).upper()
        return f"URH-GRV-{date_str}-{hex_suffix}"

    async def register_or_update_nominee(
        self,
        user: User,
        payload: DataNomineeRequest,
        session: AsyncSession,
    ) -> Dict[str, Any]:
        """Registers or idempotently updates seeker's Digital Nominee (DPDP Section 14)."""
        name = payload.nominee_name.strip()
        contact = payload.nominee_contact.strip()
        relationship = payload.relationship.strip()

        if len(name) < 2 or len(relationship) < 2 or len(contact) < 5:
            raise SanctuaryException(
                error_code="INVALID_NOMINEE_PAYLOAD",
                message="Nominee attributes fail statutory length and format boundaries.",
                status_code=422,
            )

        stmt = select(DataNominee).where(DataNominee.user_id == user.id)
        result = await session.execute(stmt)
        nominee = result.scalar_one_or_none()
        now = datetime.now(timezone.utc)

        if nominee:
            nominee.nominee_name = name
            nominee.nominee_contact = contact
            nominee.relationship = relationship
            nominee.updated_at = now
        else:
            nominee = DataNominee(
                user_id=user.id,
                nominee_name=name,
                nominee_contact=contact,
                relationship=relationship,
                designated_at=now,
                updated_at=now,
                verification_status="designated",
            )
            session.add(nominee)

        await session.commit()
        await session.refresh(nominee)

        assigned_at_dt = getattr(nominee, "designated_at", None) or getattr(nominee, "updated_at", now)
        return {
            "nominee_name": nominee.nominee_name,
            "nominee_contact": nominee.nominee_contact,
            "relationship": nominee.relationship,
            "assigned_at": assigned_at_dt.isoformat() if assigned_at_dt else now.isoformat(),
            "verification_status": getattr(nominee, "verification_status", "designated"),
        }

    async def get_nominee(
        self,
        user: User,
        session: AsyncSession,
    ) -> Optional[Dict[str, Any]]:
        """Retrieves seeker's active Digital Nominee designation or None."""
        stmt = select(DataNominee).where(DataNominee.user_id == user.id)
        result = await session.execute(stmt)
        nominee = result.scalar_one_or_none()
        if not nominee:
            return None

        assigned_at_dt = getattr(nominee, "designated_at", None) or getattr(nominee, "updated_at", None)
        return {
            "nominee_name": nominee.nominee_name,
            "nominee_contact": nominee.nominee_contact,
            "relationship": nominee.relationship,
            "assigned_at": assigned_at_dt.isoformat() if assigned_at_dt else datetime.now(timezone.utc).isoformat(),
            "verification_status": getattr(nominee, "verification_status", "designated"),
        }

    async def submit_grievance(
        self,
        reporter: User,
        payload: GrievanceSubmitRequest,
        session: AsyncSession,
    ) -> Dict[str, Any]:
        """Submits a statutory grievance dossier with mandatory 15-day resolution SLA."""
        if reporter.id == payload.reported_user_id:
            raise SanctuaryException(
                error_code="INVALID_GRIEVANCE_TARGET",
                message="Seeker cannot file statutory grievance against themselves.",
                status_code=400,
            )

        dossier_ref = self.generate_dossier_reference()
        ack_time = datetime.now(timezone.utc)
        # IT Rules 2021 Rule 3(2)(a) 15-day general resolution SLA
        resolution_due_at = ack_time + timedelta(days=15)

        # IT Rules 2021 Rule 3(2)(b) mandatory 24-hour statutory emergency takedown SLA
        emergency_takedown_due_at = None
        if payload.violation_category in ("explicit_content", "impersonation", "underage", "ncii"):
            emergency_takedown_due_at = ack_time + timedelta(hours=24)
            sla_deadline_at = emergency_takedown_due_at
        else:
            sla_deadline_at = resolution_due_at

        evidence = payload.evidence_text.strip()
        dossier = GrievanceDossier(
            dossier_reference_id=dossier_ref,
            reporter_id=reporter.id,
            reported_user_id=payload.reported_user_id,
            violation_category=payload.violation_category,
            evidence_text=evidence,
            statutory_notes=evidence,
            status="acknowledged",
            acknowledgment_sent_at=ack_time,
            statutory_resolution_due_at=resolution_due_at,
            sla_deadline_at=sla_deadline_at,
        )
        session.add(dossier)
        await session.commit()
        await session.refresh(dossier)

        ack_sent = dossier.acknowledgment_sent_at
        if ack_sent.tzinfo is None:
            ack_sent = ack_sent.replace(tzinfo=timezone.utc)

        res_due = dossier.statutory_resolution_due_at
        if res_due and res_due.tzinfo is None:
            res_due = res_due.replace(tzinfo=timezone.utc)

        return {
            "dossier_reference_id": dossier.dossier_reference_id,
            "status": dossier.status,
            "acknowledgment_sent_at": ack_sent.isoformat(),
            "statutory_resolution_due_at": res_due.isoformat() if res_due else resolution_due_at.isoformat(),
            "emergency_takedown_due_at": emergency_takedown_due_at.isoformat() if emergency_takedown_due_at else None,
        }

    async def get_user_grievances(
        self,
        user: User,
        session: AsyncSession,
    ) -> List[Dict[str, Any]]:
        """Queries all statutory grievances filed by the seeker with SLA status."""
        stmt = (
            select(GrievanceDossier)
            .where(GrievanceDossier.reporter_id == user.id)
            .order_by(GrievanceDossier.created_at.desc())
        )
        result = await session.execute(stmt)
        dossiers = result.scalars().all()

        items = []
        for d in dossiers:
            ack_dt = d.acknowledgment_sent_at or d.created_at
            if ack_dt and ack_dt.tzinfo is None:
                ack_dt = ack_dt.replace(tzinfo=timezone.utc)

            due_dt = d.statutory_resolution_due_at
            if due_dt and due_dt.tzinfo is None:
                due_dt = due_dt.replace(tzinfo=timezone.utc)

            emergency_due = None
            if d.violation_category in ("explicit_content", "impersonation", "underage", "ncii"):
                emergency_due = d.sla_deadline_at
                if emergency_due and emergency_due.tzinfo is None:
                    emergency_due = emergency_due.replace(tzinfo=timezone.utc)

            created_dt = d.created_at
            if created_dt and created_dt.tzinfo is None:
                created_dt = created_dt.replace(tzinfo=timezone.utc)

            items.append({
                "dossier_reference_id": d.dossier_reference_id,
                "violation_category": d.violation_category,
                "evidence_text": d.evidence_text or d.statutory_notes or "",
                "status": d.status,
                "acknowledgment_sent_at": ack_dt.isoformat() if ack_dt else "",
                "statutory_resolution_due_at": due_dt.isoformat() if due_dt else "",
                "emergency_takedown_due_at": emergency_due.isoformat() if emergency_due else None,
                "created_at": created_dt.isoformat() if created_dt else "",
            })
        return items

    async def compile_data_portability_package(
        self,
        user: User,
        session: AsyncSession,
    ) -> Dict[str, Any]:
        """Compiles machine-readable Subject Access Request (SAR) JSON archive under DPDP Section 11."""
        now = datetime.now(timezone.utc)

        # 1. User Profile Attributes (Sanitized - Zero passwords or secret keys)
        user_profile = {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "dob": user.dob.isoformat() if user.dob else None,
            "gender": user.gender,
            "bio": user.bio,
            "profession": user.profession,
            "education": user.education,
            "location_name": user.location_name,
            "latitude": float(user.latitude) if user.latitude is not None else None,
            "longitude": float(user.longitude) if user.longitude is not None else None,
            "streak_count": user.streak_count,
            "kyc_status": user.kyc_status,
            "subscription_tier": user.subscription_tier,
            "created_at": user.created_at.isoformat() if getattr(user, "created_at", None) else None,
        }

        # 2. Media Assets
        media_assets = {
            "photos": list(user.photos) if user.photos else [],
            "avatar_url": user.avatar_url,
            "voice_spark_url": user.voice_spark_url,
            "voice_spark_prompt": user.voice_spark_prompt,
        }

        # 3. Matches & Dialogues Metadata (Counterparty Privacy Preservation)
        match_stmt = select(Match).where(or_(Match.user1_id == user.id, Match.user2_id == user.id))
        match_res = await session.execute(match_stmt)
        matches = match_res.scalars().all()
        connections_metadata = [
            {
                "match_id": str(m.id),
                "matched_at": (getattr(m, "matched_at", None) or getattr(m, "created_at", None) or now).isoformat(),
                "is_active": m.is_active,
                "closure_status": m.closure_status,
                "privacy_notice": "Dialogue transcript omitted to protect counterparty statutory privacy under DPDP Section 11.",
            }
            for m in matches
        ]

        # 4. Consent Audit Trail
        consent_stmt = select(ConsentAuditLog).where(ConsentAuditLog.user_id == user.id)
        consent_res = await session.execute(consent_stmt)
        consent_trail = [
            {
                "consent_purpose_id": c.consent_purpose_id,
                "installation_uuid": c.installation_uuid,
                "consented_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in consent_res.scalars().all()
        ]

        # 5. Financial Transactions
        iap_stmt = select(InAppPurchase).where(InAppPurchase.user_id == user.id)
        iap_res = await session.execute(iap_stmt)
        financial_transactions = [
            {
                "transaction_reference": p.transaction_reference,
                "store": p.store,
                "product_identifier": p.product_identifier,
                "amount_gross": str(p.amount_gross),
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in iap_res.scalars().all()
        ]

        # 6. Statutory Grievances Filed
        grievances = await self.get_user_grievances(user, session)

        # 7. Digital Nominee Record
        digital_nominee = await self.get_nominee(user, session)

        # 8. Statutory Seal
        compliance_seal = {
            "act": "Digital Personal Data Protection Act 2023 (Sections 11, 12 & 14)",
            "statutory_rules": "Information Technology (Intermediary Guidelines and Digital Media Ethics Code) Rules 2021",
            "data_fiduciary": "UR-Heart Sanctuary (ASI Verticals)",
            "export_version": "1.0",
            "sanitized": True,
            "secrets_redacted": True,
            "passwords_and_hashes_omitted": True,
            "keystore_secrets_omitted": True,
        }

        export_package = {
            "compliance_seal": compliance_seal,
            "user_profile": user_profile,
            "media_assets": media_assets,
            "connections_metadata": connections_metadata,
            "consent_audit_trail": consent_trail,
            "financial_transactions": financial_transactions,
            "statutory_dossiers": grievances,
            "digital_nominee": digital_nominee,
        }

        # Record DataExportRequest audit entry
        try:
            payload_str = json.dumps(export_package, sort_keys=True)
            checksum = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
            export_record = DataExportRequest(
                user_id=user.id,
                status="ready",
                checksum_sha256=checksum,
                created_at=now,
                expires_at=now + timedelta(days=7),
            )
            session.add(export_record)
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("Failed to record DataExportRequest audit entry")

        return {
            "export_data": export_package,
            "generated_at": now.isoformat(),
        }


legal_vault_service = LegalVaultService()
