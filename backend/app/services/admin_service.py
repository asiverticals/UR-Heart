import logging
from datetime import date, datetime, timezone
from typing import List, Literal, Optional
from uuid import UUID

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.exceptions import SanctuaryException
from ..models.domain.admin_telemetry import AdminKycEscalation
from ..models.domain.user import User
from ..schemas.admin import AdminKycDecisionResponse, AdminKycEscalationItem
from .storage_service import UnifiedStorageService, get_storage_service

logger = logging.getLogger("urheart.admin")


class AdminService:
    """Superadmin biometric KYC adjudication desk engine."""

    def __init__(self, storage_service: Optional[UnifiedStorageService] = None) -> None:
        self.storage_service = storage_service or get_storage_service()

    async def get_pending_escalations(
        self,
        session: AsyncSession,
    ) -> List[AdminKycEscalationItem]:
        """Queries pending KYC escalations, joining with seeker profile and generating 15-minute presigned review URLs."""
        stmt = (
            select(AdminKycEscalation, User)
            .join(User, AdminKycEscalation.user_id == User.id)
            .where(AdminKycEscalation.status == "pending")
            .order_by(AdminKycEscalation.created_at.asc())
        )
        result = await session.execute(stmt)
        rows = result.all()

        items: List[AdminKycEscalationItem] = []
        today = date.today()

        for escalation, user in rows:
            # 1. Calculate age in solar years
            dob = escalation.declared_dob or user.dob
            age = (today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))) if dob else None

            # 2. Generate 15-minute presigned GET URLs
            live_frame_url = self._resolve_review_url(escalation.selfie_storage_url, expires_in=900)
            anchor_photo_url = self._resolve_review_url(
                escalation.id_card_storage_url or (user.photos[0] if user.photos else ""),
                expires_in=900,
            )

            # 3. Format Groq score to 0 - 100 percentage
            raw_score = float(escalation.groq_match_score)
            score_pct = round(raw_score * 100.0, 1) if raw_score <= 1.0 else round(raw_score, 1)

            items.append(
                AdminKycEscalationItem(
                    id=str(escalation.id),
                    user_id=str(user.id),
                    full_name=user.full_name,
                    declared_dob=dob,
                    declared_age=age,
                    groq_match_score=score_pct,
                    anchor_photo_url=anchor_photo_url,
                    live_frame_url=live_frame_url,
                    status=escalation.status,
                    created_at=escalation.created_at,
                )
            )

        return items

    async def decide_escalation(
        self,
        session: AsyncSession,
        escalation_id: str,
        decision: Literal["approve", "reject"],
        reviewer: User,
        background_tasks: Optional[BackgroundTasks] = None,
        notes: Optional[str] = None,
        ip_address: Optional[str] = "127.0.0.1",
    ) -> AdminKycDecisionResponse:
        """Atomically adjudicates a KYC escalation, updates user status, and purges the ephemeral biometric frame."""
        # 1. Fetch escalation ticket by integer ID or user UUID with row lock
        escalation: Optional[AdminKycEscalation] = None
        if str(escalation_id).isdigit():
            stmt_id = select(AdminKycEscalation).where(AdminKycEscalation.id == int(escalation_id)).with_for_update()
            escalation = (await session.execute(stmt_id)).scalar_one_or_none()
        else:
            try:
                target_uuid = UUID(str(escalation_id))
                stmt_user = (
                    select(AdminKycEscalation)
                    .where(
                        AdminKycEscalation.user_id == target_uuid,
                        AdminKycEscalation.status == "pending",
                    )
                    .order_by(AdminKycEscalation.created_at.desc())
                    .with_for_update()
                )
                escalation = (await session.execute(stmt_user)).scalars().first()
            except (ValueError, TypeError):
                pass

        if not escalation:
            raise SanctuaryException(
                error_code="ESCALATION_NOT_FOUND",
                message="KYC escalation record not found.",
                status_code=404,
            )

        if escalation.status != "pending":
            raise SanctuaryException(
                error_code="ESCALATION_ALREADY_DECIDED",
                message="KYC escalation has already been adjudicated.",
                status_code=409,
            )

        # 2. Fetch corresponding seeker
        user = await session.get(User, escalation.user_id)
        if not user:
            raise SanctuaryException(
                error_code="SEEKER_NOT_FOUND",
                message="Seeker account associated with escalation was not found.",
                status_code=404,
            )

        # 3. Apply decision logic
        if decision == "approve":
            user.kyc_status = True
            escalation.status = "approved"
        else:
            user.kyc_status = False
            escalation.status = "rejected"

        escalation.reviewed_at = datetime.now(timezone.utc)
        escalation.reviewed_by = reviewer.email or str(reviewer.id)

        # 4. Centralized Admin Audit Trail
        from .admin_audit_service import log_admin_action
        reviewer_email = reviewer.email or (getattr(reviewer, "id", None) and str(reviewer.id)) or "asiverticals@gmail.com"
        await log_admin_action(
            session=session,
            admin_email=reviewer_email,
            action=f"kyc_{decision}",
            target_type="kyc_escalation",
            target_id=str(escalation.id),
            details={
                "user_id": str(user.id),
                "decision": decision,
                "notes": notes or "",
                "score": float(escalation.groq_match_score) if escalation.groq_match_score is not None else None,
            },
            ip_address=ip_address or "127.0.0.1",
        )

        # 5. DPDP Section 8 mandatory biometric ephemeral asset purge (captured before commit)
        raw_ephemeral_key = escalation.selfie_storage_url
        ephemeral_key: Optional[str] = raw_ephemeral_key
        if ephemeral_key and "://" in ephemeral_key:
            import urllib.parse
            ephemeral_key = urllib.parse.urlparse(ephemeral_key).path.lstrip("/")

        await session.commit()
        await session.refresh(user)

        if ephemeral_key:
            if background_tasks:
                background_tasks.add_task(self._safe_delete_asset, ephemeral_key)
            else:
                self._safe_delete_asset(ephemeral_key)

        logger.info(
            "Admin %s adjudicated KYC escalation %s for seeker %s as %s",
            reviewer.email,
            escalation.id,
            user.id,
            decision,
        )

        return AdminKycDecisionResponse(
            success=True,
            user_id=str(user.id),
            status=escalation.status,
            message=f"KYC escalation successfully adjudicated as {decision}.",
        )

    def _resolve_review_url(self, key_or_url: str, expires_in: int = 900) -> str:
        """Generates presigned GET URL for private asset. Never falls back to public CDN for biometrics."""
        if not key_or_url:
            return ""
        if key_or_url.startswith("http://") or key_or_url.startswith("https://"):
            return key_or_url
        try:
            return self.storage_service.generate_presigned_get_url(key_or_url, expires_in=expires_in)
        except Exception as e:
            logger.error("Failed to generate presigned GET url for private asset %s: %s", key_or_url, e)
            return ""

    def _safe_delete_asset(self, key: str) -> None:
        """Safely purges object from storage without bubbling non-critical errors."""
        try:
            self.storage_service.delete_object(key)
            logger.info("Purged ephemeral KYC biometric asset: %s", key)
        except Exception as e:
            logger.error("Failed to purge biometric asset %s: %s", key, e)
