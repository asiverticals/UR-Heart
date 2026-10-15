import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.exceptions import SanctuaryException
from ..models.domain.admin_telemetry import DeviceFcmToken
from ..models.domain.legal import (
    BlockedUser,
    ConsentAuditLog,
    DataExportRequest,
    DataNominee,
    GrievanceDossier,
    WebDeletionToken,
)
from ..models.domain.match_and_chat import Match, Message, Swipe
from ..models.domain.monetization import AdRewardLedger, InAppPurchase, ProcessedAdTransaction
from ..models.domain.revelation import PhotoRevealConsent
from ..models.domain.user import User
from .email_service import email_service
from .storage_service import CloudflareR2StorageService, storage_service

logger = logging.getLogger("urheart.account_incineration")


class AccountIncinerationService:
    """Domain service enforcing DPDP Act 2023 Section 12 Statutory Erasure and Cloudflare R2 cascade purges."""

    def __init__(self, storage: Optional[CloudflareR2StorageService] = None):
        self.storage = storage or storage_service

    async def deactivate_mutual_matches(self, user_id: UUID, session: AsyncSession) -> int:
        """Deactivates active matches and permanently expunges all dialogue messages in those matches."""
        # Purge all dialogue messages across matches involving this seeker (both sender and counterpart messages)
        subq = select(Match.id).where((Match.user1_id == user_id) | (Match.user2_id == user_id))
        await session.execute(delete(Message).where(Message.match_id.in_(subq)))

        # Mark counterpart's matches inactive with closure_status 'peer_incinerated'
        stmt = (
            update(Match)
            .where((Match.user1_id == user_id) | (Match.user2_id == user_id))
            .values(is_active=False, closure_status="peer_incinerated")
        )
        res = await session.execute(stmt)
        return res.rowcount

    async def execute_account_incineration(
        self,
        user_id: UUID,
        session: AsyncSession,
    ) -> Dict[str, Any]:
        """Irrevocably expunges all seeker personal data across storage and relational tables.

        DPDP Act 2023 Section 12 Statutory Erasure Invariant:
        Zero fake soft-delete retaining PII. Photos, voice sparks, matches, FCM tokens, and identities
        are permanently expunged, while statutory audit trails are scrubbed/anonymized.
        """
        user = await session.get(User, user_id)
        if not user:
            raise SanctuaryException(
                error_code="USER_NOT_FOUND",
                message="Seeker identity does not exist in sanctuary.",
                status_code=404,
            )

        # Step 1: Cascade database deletion across child relations
        # Push notification tokens
        await session.execute(delete(DeviceFcmToken).where(DeviceFcmToken.user_id == user_id))

        # Digital nominees (DPDP Section 14)
        await session.execute(delete(DataNominee).where(DataNominee.user_id == user_id))

        # Photo veil consent handshakes
        await session.execute(
            delete(PhotoRevealConsent).where(
                (PhotoRevealConsent.requester_id == user_id)
                | (PhotoRevealConsent.target_id == user_id)
            )
        )

        # Swipes (both incoming and outgoing to ensure symmetry)
        await session.execute(
            delete(Swipe).where((Swipe.actor_id == user_id) | (Swipe.target_id == user_id))
        )

        # Mutual blocking records
        await session.execute(
            delete(BlockedUser).where(
                (BlockedUser.blocker_id == user_id) | (BlockedUser.blocked_id == user_id)
            )
        )

        # Rewarded ad ledgers & processed transactions
        await session.execute(delete(AdRewardLedger).where(AdRewardLedger.user_id == user_id))
        await session.execute(
            delete(ProcessedAdTransaction).where(ProcessedAdTransaction.user_id == user_id)
        )

        # Data export requests & audit logs
        await session.execute(delete(DataExportRequest).where(DataExportRequest.user_id == user_id))
        await session.execute(delete(ConsentAuditLog).where(ConsentAuditLog.user_id == user_id))
        await session.execute(delete(WebDeletionToken).where(WebDeletionToken.user_id == user_id))

        # Matches & messages
        await self.deactivate_mutual_matches(user_id, session)

        # Step 2: Redact or scrub statutory audit tables (DPDP Section 12 legal obligation exceptions)
        # Grievance dossiers: Decouple seeker IDs and redact personal narrative text
        await session.execute(
            update(GrievanceDossier)
            .where(GrievanceDossier.reporter_id == user_id)
            .values(reporter_id=None, evidence_text="[INCINERATED_PURSUANT_TO_DPDP_SECTION_12]")
        )
        await session.execute(
            update(GrievanceDossier)
            .where(GrievanceDossier.reported_user_id == user_id)
            .values(reported_user_id=None, evidence_text="[INCINERATED_PURSUANT_TO_DPDP_SECTION_12]")
        )

        # Financial transactions: Retain payment IDs and gross amounts for 7-year statutory tax compliance, decouple user_id
        await session.execute(
            update(InAppPurchase)
            .where(InAppPurchase.user_id == user_id)
            .values(user_id=None)
        )

        # Step 3: Delete the core user record
        await session.execute(delete(User).where(User.id == user_id))

        # Step 4: Commit database transaction to guarantee ACID persistence before storage deletion
        await session.commit()

        # Step 5: Cloudflare R2 Media Prefix Cascade Purge
        # Executed post-commit to ensure database state integrity before external storage mutation.
        # Failures bubble up to prevent false statutory certification.
        self.storage.delete_objects_by_prefix(f"users/{user_id}/")
        self.storage.delete_objects_by_prefix(f"kyc_temp/{user_id}/")

        certificate_token = f"DPDP-INCINERATE-{secrets.token_hex(8).upper()}"
        iso_now = datetime.now(timezone.utc).isoformat()
        logger.info(
            f"[DPDP-SECTION-12] Seeker {user_id} completely incinerated. "
            f"R2 assets and DB rows permanently purged. Certificate: {certificate_token}"
        )

        return {
            "success": True,
            "incinerated_at": iso_now,
            "certificate": certificate_token,
        }

    async def send_web_deletion_email(self, email: str, confirmation_url: str) -> bool:
        """Dispatches statutory account incineration confirmation link to the seeker's email."""
        return await email_service.send_incineration_confirmation(email, confirmation_url)

    async def dispatch_web_deletion_magic_link(
        self,
        email: str,
        session: AsyncSession,
        reason: Optional[str] = None,
    ) -> bool:
        """Dispatches an out-of-app web deletion magic link pursuant to store policies."""
        email_clean = email.lower().strip()
        ident_hash = hashlib.sha256(email_clean.encode("utf-8")).hexdigest()[:12]

        stmt = select(User).where(func.lower(User.email) == email_clean)
        res = await session.execute(stmt)
        user = res.scalar_one_or_none()

        # Anti-enumeration invariant: Always return True even if user does not exist
        if not user:
            logger.info(f"[WEB-INCINERATION] Web deletion requested for unregistered identifier: {ident_hash}")
            return True

        # Per-email rate throttling: Prevent spamming link requests within 60 seconds
        recent_cutoff = datetime.now(timezone.utc) - timedelta(minutes=1)
        recent_stmt = select(WebDeletionToken).where(
            WebDeletionToken.user_id == user.id,
            WebDeletionToken.created_at >= recent_cutoff,
        )
        recent_res = await session.execute(recent_stmt)
        if recent_res.scalars().first() is not None:
            logger.info(f"[WEB-INCINERATION] Web deletion request throttled for identifier: {ident_hash}")
            return True

        # Generate cryptographic 15-minute verification token and store SHA-256 hash
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

        web_del = WebDeletionToken(
            token=token_hash,
            email=user.email,
            user_id=user.id,
            reason=reason,
            expires_at=expires_at,
        )
        session.add(web_del)
        await session.commit()

        confirmation_url = f"https://urheart.app/delete-account?token={token}"
        dispatched = await self.send_web_deletion_email(user.email, confirmation_url)
        if not dispatched:
            logger.warning(
                f"[WEB-INCINERATION] Email dispatch failed for verification identifier: {ident_hash}"
            )
            await session.delete(web_del)
            await session.commit()
        else:
            logger.info(
                f"[WEB-INCINERATION] Dispatched statutory verification link for identifier: {ident_hash}"
            )

        return True

    async def confirm_web_deletion(
        self,
        token: str,
        session: AsyncSession,
    ) -> Dict[str, Any]:
        """Validates the web deletion magic link by hash and triggers complete account incineration."""
        token_hash = hashlib.sha256(token.strip().encode("utf-8")).hexdigest()
        stmt = select(WebDeletionToken).where(WebDeletionToken.token == token_hash)
        res = await session.execute(stmt)
        token_record = res.scalar_one_or_none()

        if not token_record:
            raise SanctuaryException(
                error_code="INVALID_OR_EXPIRED_TOKEN",
                message="The statutory deletion link is invalid or has expired.",
                status_code=400,
            )

        expires_at = token_record.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at < datetime.now(timezone.utc):
            raise SanctuaryException(
                error_code="INVALID_OR_EXPIRED_TOKEN",
                message="The statutory deletion link is invalid or has expired.",
                status_code=400,
            )

        user_id = token_record.user_id
        # Delete token record before incinerating user to prevent reuse
        await session.delete(token_record)
        await session.flush()

        return await self.execute_account_incineration(user_id, session)


account_incineration_service = AccountIncinerationService()


def get_account_incineration_service() -> AccountIncinerationService:
    """Dependency provider returning singleton AccountIncinerationService."""
    return account_incineration_service
