import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.exceptions import SanctuaryException
from ..models.domain.legal import BlockedUser
from ..models.domain.monetization import InAppPurchase
from ..models.domain.revelation import PhotoRevealConsent
from ..models.domain.user import User
from .payment_service import payment_service

class PhotoRevealService:
    """Core domain service orchestrating the Modesty-First 35px Photo Blur Veil and Bilateral Reveal Handshake."""

    async def request_photo_reveal(
        self,
        requester_id: uuid.UUID,
        target_id: uuid.UUID,
        session: AsyncSession,
    ) -> Dict[str, Any]:
        """Initiates a photo veil unmasking request or auto-accepts if reciprocal request exists."""
        # 1. Self-request prevention
        if requester_id == target_id:
            raise SanctuaryException(
                error_code="CANNOT_REVEAL_SELF",
                message="Cannot request photo reveal for own profile.",
                status_code=400,
            )

        # 2. Assert target exists and is not soft-deleted
        target_stmt = select(User).where(User.id == target_id)
        target = (await session.execute(target_stmt)).scalar_one_or_none()
        if not target:
            raise SanctuaryException(
                error_code="TARGET_NOT_FOUND",
                message="Target seeker does not exist.",
                status_code=404,
            )

        # 3. Bilateral block validation
        blocked_stmt = select(BlockedUser).where(
            ((BlockedUser.blocker_id == requester_id) & (BlockedUser.blocked_id == target_id))
            | ((BlockedUser.blocker_id == target_id) & (BlockedUser.blocked_id == requester_id))
        )
        if (await session.execute(blocked_stmt)).scalar_one_or_none():
            raise SanctuaryException(
                error_code="SEEKER_BLOCKED",
                message="Cannot interact with a blocked seeker profile.",
                status_code=403,
            )

        # 4. Check if reciprocal record exists where target already requested reveal from requester
        reciprocal_stmt = select(PhotoRevealConsent).where(
            PhotoRevealConsent.requester_id == target_id,
            PhotoRevealConsent.target_id == requester_id,
        )
        reciprocal = (await session.execute(reciprocal_stmt)).scalar_one_or_none()

        if reciprocal:
            if reciprocal.status == "accepted":
                return {
                    "target_id": target_id,
                    "status": "accepted",
                    "is_revealed": True,
                    "message": "Mutual resonance unmasked the veil.",
                }
            elif reciprocal.status == "pending":
                # Mutual cross-request fulfilled! Auto-accept both sides
                reciprocal.status = "accepted"
                reciprocal.updated_at = datetime.now(timezone.utc)

                own_stmt = select(PhotoRevealConsent).where(
                    PhotoRevealConsent.requester_id == requester_id,
                    PhotoRevealConsent.target_id == target_id,
                )
                own = (await session.execute(own_stmt)).scalar_one_or_none()
                if own:
                    own.status = "accepted"
                    own.updated_at = datetime.now(timezone.utc)
                else:
                    session.add(
                        PhotoRevealConsent(
                            requester_id=requester_id,
                            target_id=target_id,
                            status="accepted",
                        )
                    )

                await session.commit()
                return {
                    "target_id": target_id,
                    "status": "accepted",
                    "is_revealed": True,
                    "message": "Mutual resonance unmasked the veil.",
                }

        # 5. Check if own record already exists
        own_stmt = select(PhotoRevealConsent).where(
            PhotoRevealConsent.requester_id == requester_id,
            PhotoRevealConsent.target_id == target_id,
        )
        own = (await session.execute(own_stmt)).scalar_one_or_none()

        if own:
            if own.status == "accepted":
                return {
                    "target_id": target_id,
                    "status": "accepted",
                    "is_revealed": True,
                    "message": "Mutual resonance unmasked the veil.",
                }
            elif own.status == "pending":
                return {
                    "target_id": target_id,
                    "status": "pending",
                    "is_revealed": False,
                    "message": "Reveal request already pending.",
                }
            elif own.status == "declined":
                # Re-request after previous decline resets to pending
                own.status = "pending"
                own.updated_at = datetime.now(timezone.utc)
                await session.commit()
                return {
                    "target_id": target_id,
                    "status": "pending",
                    "is_revealed": False,
                    "message": "Photo reveal request sent.",
                }

        # 6. Insert new pending consent record with savepoint concurrency guard
        try:
            async with session.begin_nested():
                new_consent = PhotoRevealConsent(
                    requester_id=requester_id,
                    target_id=target_id,
                    status="pending",
                )
                session.add(new_consent)
                await session.flush()
        except IntegrityError:
            # Concurrent duplicate request caught
            own = (await session.execute(own_stmt)).scalar_one_or_none()
            if own:
                return {
                    "target_id": target_id,
                    "status": own.status,
                    "is_revealed": own.status == "accepted",
                    "message": "Reveal request already pending."
                    if own.status == "pending"
                    else "Photo reveal request processed.",
                }
            raise

        await session.commit()
        return {
            "target_id": target_id,
            "status": "pending",
            "is_revealed": False,
            "message": "Photo reveal request sent.",
        }

    async def respond_to_photo_reveal(
        self,
        target_id: uuid.UUID,
        requester_id: uuid.UUID,
        accept: bool,
        session: AsyncSession,
    ) -> Dict[str, Any]:
        """Responds to a pending photo reveal request from another seeker."""
        # Bilateral block check: blocked seekers cannot respond to reveal requests (VULN-MEDIA-04)
        blocked_stmt = select(BlockedUser).where(
            ((BlockedUser.blocker_id == requester_id) & (BlockedUser.blocked_id == target_id))
            | ((BlockedUser.blocker_id == target_id) & (BlockedUser.blocked_id == requester_id))
        )
        if (await session.execute(blocked_stmt)).scalar_one_or_none():
            raise SanctuaryException(
                error_code="SEEKER_BLOCKED",
                message="Cannot respond to photo reveal for a blocked seeker.",
                status_code=403,
            )

        stmt = select(PhotoRevealConsent).where(
            PhotoRevealConsent.requester_id == requester_id,
            PhotoRevealConsent.target_id == target_id,
            PhotoRevealConsent.status == "pending",
        )
        record = (await session.execute(stmt)).scalar_one_or_none()

        if not record:
            raise SanctuaryException(
                error_code="REVEAL_REQUEST_NOT_FOUND",
                message="No pending reveal request found from this seeker.",
                status_code=404,
            )

        new_status = "accepted" if accept else "declined"
        record.status = new_status
        record.updated_at = datetime.now(timezone.utc)

        if accept:
            # Reciprocate consent so both seekers see unveiled photos
            recip_stmt = select(PhotoRevealConsent).where(
                PhotoRevealConsent.requester_id == target_id,
                PhotoRevealConsent.target_id == requester_id,
            )
            reciprocal = (await session.execute(recip_stmt)).scalar_one_or_none()
            if reciprocal:
                reciprocal.status = "accepted"
                reciprocal.updated_at = datetime.now(timezone.utc)
            else:
                session.add(
                    PhotoRevealConsent(
                        requester_id=target_id,
                        target_id=requester_id,
                        status="accepted",
                    )
                )

        await session.commit()
        return {
            "target_id": requester_id,
            "status": new_status,
            "is_revealed": accept,
            "message": "Photo reveal accepted." if accept else "Photo reveal declined.",
        }

    async def get_photo_reveal_status(
        self,
        user_a: uuid.UUID,
        user_b: uuid.UUID,
        session: AsyncSession,
    ) -> Dict[str, Any]:
        """Computes current veil unmasking status between two seekers."""
        # 0. Check bilateral block between seekers
        block_stmt = select(BlockedUser).where(
            ((BlockedUser.blocker_id == user_a) & (BlockedUser.blocked_id == user_b))
            | ((BlockedUser.blocker_id == user_b) & (BlockedUser.blocked_id == user_a))
        )
        if (await session.execute(block_stmt)).scalars().first():
            return {"target_id": user_b, "status": "veiled", "is_revealed": False}

        # 1. Bilateral mutual consent accepted
        consent_stmt = select(PhotoRevealConsent).where(
            ((PhotoRevealConsent.requester_id == user_a) & (PhotoRevealConsent.target_id == user_b))
            | ((PhotoRevealConsent.requester_id == user_b) & (PhotoRevealConsent.target_id == user_a)),
            PhotoRevealConsent.status == "accepted",
        )
        if (await session.execute(consent_stmt)).scalars().first():
            return {"target_id": user_b, "status": "accepted", "is_revealed": True}

        # 2. Pending request initiated by user_a (BNS § 77: modesty veil remains strictly masked)
        pending_stmt = select(PhotoRevealConsent).where(
            PhotoRevealConsent.requester_id == user_a,
            PhotoRevealConsent.target_id == user_b,
            PhotoRevealConsent.status == "pending",
        )
        if (await session.execute(pending_stmt)).scalars().first():
            return {"target_id": user_b, "status": "pending", "is_revealed": False}

        # 3. Default veiled state
        return {"target_id": user_b, "status": "veiled", "is_revealed": False}

    async def unlock_photo_with_perk(
        self,
        user_id: uuid.UUID,
        target_id: uuid.UUID,
        session: AsyncSession,
        purchase_reference: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Redeems a single profile unlock micro-perk (INR 39 / USD 1.49) to instantly unmask photos."""
        if user_id == target_id:
            raise SanctuaryException(
                error_code="CANNOT_REVEAL_SELF",
                message="Cannot unlock photos for own profile.",
                status_code=400,
            )

        target_stmt = select(User).where(User.id == target_id)
        if not (await session.execute(target_stmt)).scalar_one_or_none():
            raise SanctuaryException(
                error_code="TARGET_NOT_FOUND",
                message="Target seeker does not exist.",
                status_code=404,
            )

        # Bilateral block check: blocked users cannot unlock photos
        block_stmt = select(BlockedUser).where(
            ((BlockedUser.blocker_id == user_id) & (BlockedUser.blocked_id == target_id))
            | ((BlockedUser.blocker_id == target_id) & (BlockedUser.blocked_id == user_id))
        )
        if (await session.execute(block_stmt)).scalars().first():
            raise SanctuaryException(
                error_code="SEEKER_BLOCKED",
                message="Cannot unlock photos for a blocked seeker.",
                status_code=403,
            )

        if settings.ENVIRONMENT not in ("development", "test") and not settings.TESTING:
            raise SanctuaryException(
                error_code="STORE_VERIFICATION_UNAVAILABLE",
                message="In-app store profile unlock verification is temporarily unavailable in production.",
                status_code=503,
            )

        # Validate purchase reference and guard against replay attacks
        if purchase_reference:
            existing_tx = await session.execute(
                select(InAppPurchase).where(InAppPurchase.transaction_reference == purchase_reference)
            )
            if existing_tx.scalars().first():
                raise SanctuaryException(
                    error_code="PURCHASE_REFERENCE_ALREADY_USED",
                    message="Purchase reference has already been redeemed.",
                    status_code=400,
                )
            receipt_valid = await payment_service.verify_store_receipt(
                purchase_token=purchase_reference,
                expected_product_id="profile_unlock_single",
            )
            if not receipt_valid:
                raise SanctuaryException(
                    error_code="INVALID_STORE_RECEIPT",
                    message="App store receipt verification failed.",
                    status_code=400,
                )
            tx_ref = purchase_reference
        else:
            if settings.TESTING or settings.ENVIRONMENT in ("development", "test"):
                tx_ref = f"sandbox_unlock_{user_id}_{target_id}_{uuid.uuid4().hex[:12]}"
            else:
                raise SanctuaryException(
                    error_code="PAYMENT_REFERENCE_REQUIRED",
                    message="A verified store purchase reference or payment ID is required.",
                    status_code=400,
                )

        iap = InAppPurchase(
            user_id=user_id,
            transaction_reference=tx_ref,
            product_identifier="profile_unlock_single",
            store="google_play",
            currency="INR",
            amount_gross=Decimal("39.00"),
            platform_fee=Decimal("5.85"),
            amount_net=Decimal("33.15"),
            status="completed",
        )
        session.add(iap)

        # BNS 2023 § 77 & § 45: Paid micro-perk converts into an Expedited Bilateral Reveal Invitation.
        # It NEVER strips the modesty veil unilaterally without the target seeker's reciprocal consent.
        # 1. Check if target seeker already has an active or pending request toward user_id
        reciprocal_stmt = select(PhotoRevealConsent).where(
            PhotoRevealConsent.requester_id == target_id,
            PhotoRevealConsent.target_id == user_id,
        )
        reciprocal = (await session.execute(reciprocal_stmt)).scalar_one_or_none()

        if reciprocal and reciprocal.status in ("accepted", "pending"):
            # Target already expressed affirmative consent: unmask veil mutually
            reciprocal.status = "accepted"
            reciprocal.updated_at = datetime.now(timezone.utc)

            own_stmt = select(PhotoRevealConsent).where(
                PhotoRevealConsent.requester_id == user_id,
                PhotoRevealConsent.target_id == target_id,
            )
            own = (await session.execute(own_stmt)).scalar_one_or_none()
            if own:
                own.status = "accepted"
                own.updated_at = datetime.now(timezone.utc)
            else:
                session.add(
                    PhotoRevealConsent(
                        requester_id=user_id,
                        target_id=target_id,
                        status="accepted",
                    )
                )
            await session.commit()
            return {
                "target_id": target_id,
                "status": "accepted",
                "is_revealed": True,
                "message": "Mutual resonance unmasked the veil.",
            }

        # 2. No target consent yet: record or escalate own request to pending
        own_stmt = select(PhotoRevealConsent).where(
            PhotoRevealConsent.requester_id == user_id,
            PhotoRevealConsent.target_id == target_id,
        )
        own = (await session.execute(own_stmt)).scalar_one_or_none()
        if own:
            own.status = "pending"
            own.updated_at = datetime.now(timezone.utc)
        else:
            session.add(
                PhotoRevealConsent(
                    requester_id=user_id,
                    target_id=target_id,
                    status="pending",
                )
            )

        await session.commit()

        return {
            "target_id": target_id,
            "status": "pending",
            "is_revealed": False,
            "message": "Expedited bilateral reveal invitation dispatched. Modesty veil remains protected until target seeker accepts.",
        }

    async def get_secure_photo_urls(
        self,
        viewer_id: uuid.UUID,
        target_id: uuid.UUID,
        target_photos: Optional[list],
        storage_service: Any,
        session: AsyncSession,
    ) -> list:
        """Returns signed/presigned photo URLs for revealed photos, or empty list if veiled (VULN-MEDIA-03)."""
        status_res = await self.get_photo_reveal_status(viewer_id, target_id, session)
        if not status_res.get("is_revealed") or not target_photos:
            return []

        secure_urls = []
        for p in target_photos:
            if not p:
                continue
            if "users/" in p:
                key = "users/" + p.split("users/", 1)[1]
                try:
                    presigned = storage_service.generate_presigned_get_url(key, expires_in=3600)
                    secure_urls.append(presigned)
                except Exception:
                    secure_urls.append(p)
            else:
                secure_urls.append(p)
        return secure_urls

photo_reveal_service = PhotoRevealService()

def get_photo_reveal_service() -> PhotoRevealService:
    """Dependency provider returning the singleton PhotoRevealService instance."""
    return photo_reveal_service
