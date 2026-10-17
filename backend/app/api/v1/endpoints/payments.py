import json
import logging
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from ....core.config import settings
from ....core.database import get_db
from ....core.exceptions import SanctuaryException
from ....models.domain.monetization import InAppPurchase, PendingWebEntitlement
from ....models.domain.user import User
from ....schemas.base_response import SanctuaryResponse
from ....schemas.monetization import (
    InAppPurchaseVerifyRequest,
    RazorpayOrderCreate,
    RazorpayOrderResponse,
    RazorpayPaymentVerify,
    WebRazorpayOrderCreate,
)
from ....services.billing_entitlement_service import CATALOG_PRODUCTS, billing_entitlement_service
from ....services.payment_service import LEGACY_CATALOG, payment_service
from ...deps import get_current_user
try:
    from ....core.limiter import limiter
except (ImportError, ValueError):
    from backend.app.core.limiter import limiter

logger = logging.getLogger("SanctuaryPayments")

router = APIRouter()


@router.post(
    "/create-order",
    response_model=SanctuaryResponse[RazorpayOrderResponse],
    status_code=status.HTTP_200_OK,
)
@limiter.limit("15/minute")
async def create_razorpay_order(
    request: Request,
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


@router.post(
    "/web-create-order",
    response_model=SanctuaryResponse[RazorpayOrderResponse],
    status_code=status.HTTP_200_OK,
)
@limiter.limit("15/minute")
async def create_web_razorpay_order(
    request: Request,
    payload: WebRazorpayOrderCreate,
    session: AsyncSession = Depends(get_db),
) -> SanctuaryResponse[RazorpayOrderResponse]:
    """Generates server-side Razorpay order for Web Store guest or registered seekers."""
    target_user: Optional[User] = None
    if payload.seeker_uuid:
        try:
            parsed_uuid = UUID(payload.seeker_uuid)
            user_res = await session.execute(select(User).where(User.id == parsed_uuid))
            target_user = user_res.scalar_one_or_none()
        except (ValueError, TypeError):
            pass
    clean_email = (payload.email or "").strip().lower()
    if not target_user and clean_email:
        user_res = await session.execute(select(User).where(func.lower(User.email) == clean_email))
        target_user = user_res.scalar_one_or_none()

    order_data = await payment_service.create_razorpay_order(
        user=target_user,
        product_identifier=payload.product_identifier,
        session=session,
        email=clean_email or payload.email,
    )
    return SanctuaryResponse(
        data=RazorpayOrderResponse(**order_data),
        message="Web store Razorpay order created successfully.",
    )



@router.post("/verify-checkout", status_code=status.HTTP_200_OK)
@limiter.limit("15/minute")
async def verify_checkout(
    request: Request,
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

    # 2. Resolve product identifier with server-side precedence and ownership verification (SEC-05, SEC-06, Issue #6)
    cached_order = payment_service.get_cached_order(payload.razorpay_order_id)
    if not cached_order:
        cached_order = await payment_service.fetch_order_from_razorpay(payload.razorpay_order_id)

    if cached_order:
        raw_user_id = cached_order.get("user_id")
        order_email = (cached_order.get("email") or "").strip().lower()

        if raw_user_id:
            if str(raw_user_id) != str(current_user.id):
                raise SanctuaryException(
                    error_code="ORDER_OWNERSHIP_MISMATCH",
                    message="You do not own this order intent.",
                    status_code=status.HTTP_403_FORBIDDEN,
                )
        elif order_email:
            user_email = (current_user.email or "").strip().lower()
            if not user_email or user_email != order_email:
                raise SanctuaryException(
                    error_code="ORDER_OWNERSHIP_MISMATCH",
                    message="Order email does not match your authenticated account email.",
                    status_code=status.HTTP_403_FORBIDDEN,
                )
        else:
            if not settings.TESTING:
                raise SanctuaryException(
                    error_code="ORDER_OWNERSHIP_MISMATCH",
                    message="Order has no bound account or email identifier.",
                    status_code=status.HTTP_403_FORBIDDEN,
                )
        authoritative_sku = cached_order.get("product_id")
        if not authoritative_sku:
            raise SanctuaryException(
                error_code="ORDER_PRODUCT_NOT_SPECIFIED",
                message="Authoritative order contract does not specify a valid product identifier.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        if payload.product_identifier and payload.product_identifier != authoritative_sku:
            raise SanctuaryException(
                error_code="SKU_TAMPERING_DETECTED",
                message="Submitted product identifier does not match authorized order contract.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        product_identifier = authoritative_sku
    else:
        if settings.TESTING:
            product_identifier = payload.product_identifier
        else:
            raise SanctuaryException(
                error_code="ORDER_RECORD_NOT_FOUND",
                message="Authoritative order contract not found. Payment cannot be verified.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

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


@router.post("/verify-in-app-purchase", status_code=status.HTTP_200_OK)
@limiter.limit("15/minute")
async def verify_in_app_purchase(
    request: Request,
    payload: InAppPurchaseVerifyRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SanctuaryResponse[Dict[str, Any]]:
    """Cryptographically verifies Apple StoreKit / Google Play Billing purchase token and provisions entitlement."""
    is_valid = await payment_service.verify_store_receipt(
        purchase_token=payload.purchase_token,
        expected_product_id=payload.product_identifier,
    )
    if not is_valid:
        raise SanctuaryException(
            error_code="INVALID_STORE_RECEIPT",
            message="Mobile in-app purchase verification failed.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    store = "apple_storekit" if "apple" in payload.order_id.lower() else "google_play"

    # FIND-PAY-06: Resolve authoritative gross amount from catalog instead of blind client trust
    catalog_item = payment_service.catalog_map.get(payload.product_identifier)
    if not catalog_item:
        active_catalog = billing_entitlement_service.get_active_catalog()
        payment_service.catalog_map = {item["id"]: item for item in active_catalog}
        catalog_item = payment_service.catalog_map.get(payload.product_identifier)
    if not catalog_item:
        catalog_item = LEGACY_CATALOG.get(payload.product_identifier)

    authoritative_amount = Decimal(str(catalog_item["inr_price"])) if catalog_item else payload.amount_gross

    result = await payment_service.process_successful_payment(
        user_id=current_user.id,
        order_id=payload.order_id,
        payment_id=payload.purchase_token,
        product_identifier=payload.product_identifier,
        amount_gross=authoritative_amount,
        session=session,
        store=store,
    )

    return SanctuaryResponse(
        data={"success": True, "transaction_id": payload.purchase_token, "result": result},
        message="In-app purchase receipt verified and entitlements sealed.",
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

        email_str = notes.get("email")
        if email_str:
            email_str = email_str.strip().lower()

        # FIND-PAY-03: Webhook price-to-SKU validation (strictly verify paid amount matches SKU catalog price)
        if product_identifier:
            cat_item = payment_service.catalog_map.get(product_identifier) or LEGACY_CATALOG.get(product_identifier)
            if not cat_item:
                active_catalog = billing_entitlement_service.get_active_catalog()
                payment_service.catalog_map = {item["id"]: item for item in active_catalog}
                cat_item = payment_service.catalog_map.get(product_identifier) or LEGACY_CATALOG.get(product_identifier)

            if cat_item:
                expected_price = Decimal(str(cat_item["inr_price"]))
                if amount_gross is not None and amount_gross < expected_price:
                    logger.warning(
                        "Underpayment detected in webhook for payment %s: paid %s, expected %s for %s",
                        payment_id,
                        amount_gross,
                        expected_price,
                        product_identifier,
                    )
                    return {"status": "ignored_underpayment"}

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
        elif not user_id_str and email_str and payment_id and product_identifier:
            try:
                # FIND-PAY-07: Normalize email matching (case-insensitive)
                user_res = await session.execute(
                    select(User).where(func.lower(User.email) == email_str)
                )
                existing_user = user_res.scalar_one_or_none()
                if existing_user:
                    await payment_service.process_successful_payment(
                        user_id=existing_user.id,
                        order_id=order_id or "order_webhook",
                        payment_id=payment_id,
                        product_identifier=product_identifier,
                        amount_gross=amount_gross,
                        session=session,
                    )
                else:
                    # FIND-PAY-04: Idempotent pending entitlement insertion
                    try:
                        existing_pending = await session.execute(
                            select(PendingWebEntitlement).where(PendingWebEntitlement.order_id == (order_id or payment_id))
                        )
                        if not existing_pending.scalar_one_or_none():
                            pending = PendingWebEntitlement(
                                order_id=order_id or payment_id,
                                email=email_str,
                                product_identifier=product_identifier,
                                payment_reference=payment_id,
                                amount_gross=amount_gross or Decimal("0.00"),
                                currency="INR",
                                status="paid_pending_claim",
                            )
                            session.add(pending)
                            await session.commit()
                    except IntegrityError:
                        await session.rollback()
                        logger.info("Concurrent webhook race for order %s handled idempotently", order_id or payment_id)
                        return {"status": "ok"}
            except Exception as err:
                logger.error(
                    "Error processing Web Guest Razorpay webhook payment %s: %s",
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
@limiter.limit("10/minute")
async def claim_web_entitlement(
    request: Request,
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
