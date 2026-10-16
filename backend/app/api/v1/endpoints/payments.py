import json
import logging
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.exceptions import SanctuaryException
from ....models.domain.user import User
from ....schemas.base_response import SanctuaryResponse
from ....schemas.monetization import (
    RazorpayOrderCreate,
    RazorpayOrderResponse,
    RazorpayPaymentVerify,
)
from ....services.payment_service import payment_service
from ...deps import get_current_user

logger = logging.getLogger("SanctuaryPayments")

router = APIRouter()


@router.post(
    "/create-order",
    response_model=SanctuaryResponse[RazorpayOrderResponse],
    status_code=status.HTTP_200_OK,
)
async def create_razorpay_order(
    payload: RazorpayOrderCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SanctuaryResponse[RazorpayOrderResponse]:
    """Generates server-side Razorpay order with integer subunit (paise) conversion."""
    order_data = await payment_service.create_razorpay_order(
        user=current_user,
        product_identifier=payload.product_identifier,
        session=session,
    )

    return SanctuaryResponse(
        data=RazorpayOrderResponse(**order_data),
        message="Razorpay order created successfully.",
    )


@router.post("/verify-checkout", status_code=status.HTTP_200_OK)
async def verify_checkout(
    payload: RazorpayPaymentVerify,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SanctuaryResponse[Dict[str, Any]]:
    """Cryptographically verifies client HMAC-SHA256 signature and provisions entitlements."""
    # 1. Verify HMAC signature in constant time
    is_valid = payment_service.verify_client_signature(
        order_id=payload.razorpay_order_id,
        payment_id=payload.razorpay_payment_id,
        signature=payload.razorpay_signature,
    )
    if not is_valid:
        raise SanctuaryException(
            error_code="INVALID_PAYMENT_SIGNATURE",
            message="Cryptographic payment signature mismatch.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # 2. Resolve product identifier with server-side precedence and ownership verification (SEC-05, SEC-06)
    cached_order = payment_service.get_cached_order(payload.razorpay_order_id)
    if cached_order:
        cached_user_id = str(cached_order.get("user_id"))
        if cached_user_id and cached_user_id != str(current_user.id):
            raise SanctuaryException(
                error_code="ORDER_OWNERSHIP_MISMATCH",
                message="You do not own this order intent.",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        if payload.product_identifier and cached_order.get("product_id") and payload.product_identifier != cached_order.get("product_id"):
            raise SanctuaryException(
                error_code="SKU_TAMPERING_DETECTED",
                message="Submitted product identifier does not match authorized order contract.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        product_identifier = cached_order.get("product_id") or payload.product_identifier
    else:
        product_identifier = payload.product_identifier

    if not product_identifier:
        raise SanctuaryException(
            error_code="INVALID_PRODUCT",
            message="Product identifier missing or unresolvable from order.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # 3. Idempotently process successful payment
    result = await payment_service.process_successful_payment(
        user_id=current_user.id,
        order_id=payload.razorpay_order_id,
        payment_id=payload.razorpay_payment_id,
        product_identifier=product_identifier,
        amount_gross=None,
        session=session,
    )

    return SanctuaryResponse(
        data={"success": True, "transaction_id": payload.razorpay_payment_id, "result": result},
        message="Payment verified and entitlements sealed.",
    )


@router.post("/webhook/razorpay", status_code=status.HTTP_200_OK)
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(None, alias="X-Razorpay-Signature"),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Public Razorpay webhook endpoint validating raw body HMAC signature against replay attacks."""
    if not x_razorpay_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-Razorpay-Signature header",
        )

    raw_body = await request.body()
    is_valid = payment_service.verify_webhook_signature(
        raw_body=raw_body,
        signature_header=x_razorpay_signature,
    )
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cryptographic webhook signature verification failed",
        )

    try:
        event_payload = json.loads(raw_body.decode("utf-8"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed JSON in webhook body",
        )

    event_type = event_payload.get("event")
    if event_type in ("order.paid", "payment.captured"):
        payload_data = event_payload.get("payload", {})
        payment_entity = payload_data.get("payment", {}).get("entity", {})
        order_entity = payload_data.get("order", {}).get("entity", {})

        payment_id = payment_entity.get("id") or event_payload.get("payment_id")
        order_id = payment_entity.get("order_id") or order_entity.get("id")

        notes = payment_entity.get("notes") or order_entity.get("notes") or event_payload.get("notes") or {}
        user_id_str = notes.get("user_id")
        product_identifier = notes.get("product_id") or notes.get("product_identifier")

        amount_paise = payment_entity.get("amount") or order_entity.get("amount")
        amount_gross = (
            Decimal(str(amount_paise)) / Decimal("100")
            if amount_paise is not None
            else None
        )

        if user_id_str and payment_id and product_identifier:
            try:
                user_uuid = UUID(user_id_str)
            except (ValueError, TypeError):
                logger.warning(
                    "Invalid UUID '%s' in Razorpay webhook notes; ignoring non-retryable event",
                    user_id_str,
                )
                return {"status": "ok"}

            try:
                await payment_service.process_successful_payment(
                    user_id=user_uuid,
                    order_id=order_id or "order_webhook",
                    payment_id=payment_id,
                    product_identifier=product_identifier,
                    amount_gross=amount_gross,
                    session=session,
                )
            except SanctuaryException as se:
                # If non-retryable client error (e.g. 404 user not found), acknowledge to stop retry storm
                if se.status_code and se.status_code < 500:
                    logger.warning(
                        "Non-retryable SanctuaryException in webhook for payment %s: %s",
                        payment_id,
                        se,
                    )
                    return {"status": "ok"}
                logger.error("Sanctuary error processing Razorpay webhook payment %s: %s", payment_id, se)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error processing payment webhook",
                )
            except Exception as err:
                # Do not swallow transient/database errors; return 500 so Razorpay retries delivery
                logger.error(
                    "Error processing Razorpay webhook payment %s: %s",
                    payment_id,
                    err,
                    exc_info=True,
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error processing payment webhook",
                )

    return {"status": "ok"}


# Note: UGX is zero-decimal in cash, but Stripe API requires amounts in cents (multiplied by 100), so it is excluded here.
ZERO_DECIMAL_CURRENCIES = {
    "BIF", "CLP", "DJF", "GNF", "JPY", "KMF", "KRW", "MGA",
    "PYG", "RWF", "VND", "VUV", "XAF", "XOF", "XPF",
}
THREE_DECIMAL_CURRENCIES = {"BHD", "JOD", "KWD", "OMR", "TND"}


def convert_stripe_amount(amount_subunits: Optional[int], currency: str) -> Optional[Decimal]:
    """Converts Stripe integer subunits to Decimal major units respecting currency decimal rules."""
    if amount_subunits is None:
        return None
    curr = (currency or "INR").upper()
    if curr in ZERO_DECIMAL_CURRENCIES:
        return Decimal(str(amount_subunits))
    if curr in THREE_DECIMAL_CURRENCIES:
        return Decimal(str(amount_subunits)) / Decimal("1000")
    return Decimal(str(amount_subunits)) / Decimal("100")


@router.post("/webhook/stripe", status_code=status.HTTP_200_OK)
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="Stripe-Signature"),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Stripe webhook endpoint validating signature against HMAC replay attacks."""
    raw_body = await request.body()
    if not payment_service.verify_stripe_signature(raw_body, stripe_signature or ""):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cryptographic Stripe signature mismatch",
        )

    try:
        event = json.loads(raw_body.decode("utf-8"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed JSON in Stripe webhook body",
        )

    event_type = event.get("type")
    if event_type in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
        obj = event.get("data", {}).get("object", {})
        if obj.get("payment_status") != "paid":
            return {"status": "ignored_unpaid"}

        metadata = obj.get("metadata") or {}
        user_id_str = metadata.get("user_id")
        product_id = metadata.get("product_id")
        payment_id = obj.get("payment_intent") or obj.get("id")

        if user_id_str and product_id and payment_id:
            try:
                user_uuid = UUID(user_id_str)
                amount_cents = obj.get("amount") or obj.get("amount_total")
                currency = (obj.get("currency") or "INR").upper()
                amount_gross = convert_stripe_amount(amount_cents, currency)
                await payment_service.process_successful_payment(
                    user_id=user_uuid,
                    order_id=obj.get("id", "stripe_order"),
                    payment_id=payment_id,
                    product_identifier=product_id,
                    amount_gross=amount_gross,
                    session=session,
                    store="stripe_web",
                    currency=currency,
                )
            except (ValueError, TypeError, ArithmeticError) as e:
                logger.warning("Invalid data in Stripe webhook; ignoring non-retryable event: %s", e)
            except SanctuaryException as se:
                if se.status_code and se.status_code < 500:
                    logger.warning("Non-retryable error in Stripe webhook: %s", se)
                else:
                    logger.error("Transient error in Stripe webhook: %s", se, exc_info=True)
                    raise HTTPException(status_code=500, detail="Error processing payment webhook")
            except Exception as e:
                logger.error("Unexpected error in Stripe webhook: %s", e, exc_info=True)
                raise HTTPException(status_code=500, detail="Error processing payment webhook")

    return {"status": "ok"}


@router.post("/webhook/revenuecat", status_code=status.HTTP_200_OK)
async def revenuecat_webhook(
    request: Request,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """RevenueCat webhook endpoint validating bearer secret and syncing subscription entitlements."""
    if not payment_service.verify_revenuecat_authorization(authorization):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid RevenueCat authorization header",
        )

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed JSON in RevenueCat webhook body",
        )

    event = body.get("event", {})
    if event.get("type") not in ("INITIAL_PURCHASE", "RENEWAL", "NON_RENEWING_PURCHASE"):
        return {"status": "ok"}

    app_user_id = event.get("app_user_id")
    product_id = event.get("product_id")
    tx_id = event.get("transaction_id")

    if app_user_id and product_id and tx_id:
        try:
            user_uuid = UUID(app_user_id)
        except (ValueError, TypeError):
            logger.info("RevenueCat webhook received purchase for non-UUID app_user_id '%s'; skipping unlinked purchase", app_user_id)
            return {"status": "skipped_unlinked_user"}

        try:
            price_usd = event.get("price_in_purchased_currency")
            amount_gross = Decimal(str(price_usd)) if price_usd is not None else Decimal("0.00")
            currency = (event.get("currency") or "INR").upper()
            await payment_service.process_successful_payment(
                user_id=user_uuid,
                order_id=tx_id,
                payment_id=tx_id,
                product_identifier=product_id,
                amount_gross=amount_gross,
                session=session,
                store="revenuecat_in_app",
                currency=currency,
            )
        except (ValueError, TypeError, ArithmeticError) as e:
            logger.warning("Invalid data in RevenueCat webhook; ignoring non-retryable event: %s", e)
        except SanctuaryException as se:
            if se.status_code and se.status_code < 500:
                logger.warning("Non-retryable error in RevenueCat webhook: %s", se)
            else:
                logger.error("Transient error in RevenueCat webhook: %s", se, exc_info=True)
                raise HTTPException(status_code=500, detail="Error processing payment webhook")
        except Exception as e:
            logger.error("Unexpected error in RevenueCat webhook: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail="Error processing payment webhook")

    return {"status": "ok"}


@router.post(
    "/claim-web-entitlement",
    response_model=SanctuaryResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
)
async def claim_web_entitlement(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SanctuaryResponse[Dict[str, Any]]:
    """Claims pending off-platform guest store purchases linked to seeker's verified email."""
    claimed_items = await payment_service.claim_web_entitlements(
        user=current_user,
        session=session,
    )

    return SanctuaryResponse(
        data={"claimed_items": claimed_items},
        message=f"Successfully claimed {len(claimed_items)} pending web entitlements.",
    )
