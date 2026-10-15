import hashlib
import hmac
import time
import uuid
from collections import OrderedDict
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.exceptions import SanctuaryException
from ..models.domain.monetization import InAppPurchase, PendingWebEntitlement
from ..models.domain.user import User
from .billing_entitlement_service import billing_entitlement_service

MAX_ORDER_CACHE_SIZE = 1000


class PaymentService:
    """Razorpay Order Lifecycle, HMAC-SHA256 Cryptographic Verification & Replay Defense Service."""

    def __init__(self, max_cache_size: int = MAX_ORDER_CACHE_SIZE) -> None:
        self.catalog_map: Dict[str, Dict[str, Any]] = {
            item["id"]: item for item in billing_entitlement_service.get_active_catalog()
        }
        self.max_cache_size = max_cache_size
        self.order_cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()

    async def create_razorpay_order(
        self,
        user: User,
        product_identifier: str,
        session: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """Creates a server-side Razorpay order with integer subunit (paise) conversion."""
        # Refresh catalog map if needed
        product = self.catalog_map.get(product_identifier)
        if not product:
            active_catalog = billing_entitlement_service.get_active_catalog()
            self.catalog_map = {item["id"]: item for item in active_catalog}
            product = self.catalog_map.get(product_identifier)

        if not product:
            raise SanctuaryException(
                error_code="INVALID_PRODUCT",
                message=f"Product '{product_identifier}' not found in active catalog",
                status_code=400,
            )

        amount_inr = float(product["inr_price"])
        amount_paise = int(round(amount_inr * 100))
        receipt_id = f"rcpt_{user.id}_{int(time.time())}"
        key_id = settings.RAZORPAY_KEY_ID or "rzp_test_urheart"
        key_secret = settings.RAZORPAY_KEY_SECRET or "mock_secret"

        order_data = {
            "amount": amount_paise,
            "currency": "INR",
            "receipt": receipt_id,
            "notes": {
                "user_id": str(user.id),
                "product_id": product_identifier,
            },
            "payment_capture": 1,
        }

        # Issue request to Razorpay Orders API
        order_id: Optional[str] = None
        # shortcut: mock order generation when mock credentials or offline test, upgrade when sandbox webhook live
        if key_id.startswith("mock_") or key_secret.startswith("mock_") or key_id == "rzp_test_urheart":
            order_id = f"order_{uuid.uuid4().hex[:14]}"
        else:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        "https://api.razorpay.com/v1/orders",
                        auth=(key_id, key_secret),
                        json=order_data,
                    )
                    if resp.status_code in (200, 201):
                        order_id = resp.json().get("id")
                    else:
                        raise SanctuaryException(
                            error_code="RAZORPAY_ORDER_FAILED",
                            message=f"Razorpay order creation failed: {resp.text}",
                            status_code=502,
                        )
            except httpx.RequestError as exc:
                raise SanctuaryException(
                    error_code="PAYMENT_GATEWAY_UNAVAILABLE",
                    message=f"Payment gateway unreachable: {str(exc)}",
                    status_code=503,
                )

        if not order_id:
            order_id = f"order_{uuid.uuid4().hex[:14]}"

        # Cache created order metadata with bounded LRU eviction
        # shortcut: bounded in-memory LRU cache (1000 orders), upgrade to Redis for distributed multi-process workers
        if order_id in self.order_cache:
            self.order_cache.move_to_end(order_id)
        else:
            if len(self.order_cache) >= self.max_cache_size:
                self.order_cache.popitem(last=False)
        self.order_cache[order_id] = {
            "user_id": str(user.id),
            "product_id": product_identifier,
            "amount_inr": amount_inr,
            "amount_paise": amount_paise,
        }

        return {
            "order_id": order_id,
            "amount": amount_inr,
            "amount_paise": amount_paise,
            "currency": "INR",
            "key_id": key_id,
        }

    def get_cached_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves order from bounded cache and touches LRU position."""
        if order_id in self.order_cache:
            self.order_cache.move_to_end(order_id)
            return self.order_cache[order_id]
        return None

    def verify_client_signature(self, order_id: str, payment_id: str, signature: str) -> bool:
        """Constant-time HMAC-SHA256 validation of client payment token."""
        if not settings.RAZORPAY_KEY_SECRET or not signature:
            return False
        payload = f"{order_id}|{payment_id}".encode("utf-8")
        secret = settings.RAZORPAY_KEY_SECRET.encode("utf-8")
        computed = hmac.new(secret, payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(computed, signature)

    def verify_webhook_signature(self, raw_body: bytes, signature_header: str) -> bool:
        """Constant-time HMAC-SHA256 validation of Razorpay webhook signature header."""
        if not settings.RAZORPAY_WEBHOOK_SECRET or not signature_header:
            return False
        secret = settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8")
        computed = hmac.new(secret, raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(computed, signature_header)

    async def process_successful_payment(
        self,
        user_id: UUID,
        order_id: str,
        payment_id: str,
        product_identifier: str,
        amount_gross: Optional[Decimal],
        session: AsyncSession,
    ) -> Dict[str, Any]:
        """Idempotently records payment and provisions entitlements with atomic replay protection."""
        # 1. Check existing transaction reference (Idempotency Defense)
        existing_res = await session.execute(
            select(InAppPurchase).where(InAppPurchase.transaction_reference == payment_id)
        )
        existing = existing_res.scalar_one_or_none()
        if existing:
            return {
                "status": "already_processed",
                "id": existing.id,
                "transaction_id": payment_id,
                "user_id": str(existing.user_id),
                "product_id": existing.product_identifier,
            }

        # 2. Resolve & Lock User for atomic balance updates
        user_stmt = select(User).where(User.id == user_id).with_for_update()
        user_res = await session.execute(user_stmt)
        user = user_res.scalar_one_or_none()
        if not user:
            raise SanctuaryException(
                error_code="USER_NOT_FOUND",
                message=f"User {user_id} not found",
                status_code=404,
            )

        # 3. Determine amount if missing
        if amount_gross is None or amount_gross <= Decimal("0.00"):
            product = self.catalog_map.get(product_identifier)
            if product:
                amount_gross = Decimal(str(product["inr_price"]))
            else:
                amount_gross = Decimal("0.00")

        # 4. Insert InAppPurchase & provision entitlements (canonical store: web_razorpay_india)
        purchase = InAppPurchase(
            user_id=user.id,
            transaction_reference=payment_id,
            product_identifier=product_identifier,
            store="web_razorpay_india",
            currency="INR",
            amount_gross=amount_gross,
            platform_fee=Decimal("0.00"),
            amount_net=amount_gross,
            status="completed",
        )

        try:
            session.add(purchase)
            await session.flush()
            # Provision entitlements to user model
            await billing_entitlement_service.provision_user_entitlements(
                user=user,
                product_identifier=product_identifier,
                session=session,
            )
            await session.commit()
        except IntegrityError:
            await session.rollback()
            existing_after_race = await session.execute(
                select(InAppPurchase).where(InAppPurchase.transaction_reference == payment_id)
            )
            winner = existing_after_race.scalar_one_or_none()
            if winner:
                return {
                    "status": "already_processed",
                    "id": winner.id,
                    "transaction_id": payment_id,
                    "user_id": str(winner.user_id),
                    "product_id": winner.product_identifier,
                }
            raise

        return {
            "status": "completed",
            "id": purchase.id,
            "transaction_id": payment_id,
            "user_id": str(user.id),
            "product_id": product_identifier,
        }

    async def claim_web_entitlements(self, user: User, session: AsyncSession) -> List[Dict[str, Any]]:
        """Reconciles out-of-app web store guest purchases linked to seeker's verified email."""
        if not user.email:
            return []

        query = select(PendingWebEntitlement).where(
            PendingWebEntitlement.email == user.email,
            PendingWebEntitlement.status == "paid_pending_claim",
        ).with_for_update()

        result = await session.execute(query)
        pending_items = result.scalars().all()
        claimed_items: List[Dict[str, Any]] = []

        now = datetime.now(timezone.utc)
        for item in pending_items:
            # Mark entitlement claimed before provisioning commit flushes
            item.status = "claimed"
            item.claimed_at = now
            item.claimed_by_user_id = user.id

            # Provision entitlements to seeker
            await billing_entitlement_service.provision_user_entitlements(
                user=user,
                product_identifier=item.product_identifier,
                session=session,
            )
            claimed_items.append({
                "id": item.id,
                "order_id": item.order_id,
                "product_identifier": item.product_identifier,
                "amount_gross": float(item.amount_gross),
                "claimed_at": now.isoformat(),
            })

        if claimed_items:
            await session.commit()

        return claimed_items


payment_service = PaymentService()


def get_payment_service() -> PaymentService:
    return payment_service
