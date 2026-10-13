1. Monetization Topology & Statutory Compliance Framework
UR-Heart Sanctuary enforces an intentional, anti-predatory monetization model governed by Condition C2. The platform rejects infinite auto-renewing paywalls and algorithmic loneliness traps, deploying a dual economic pipeline: Indian Rupee (INR ₹) Micro-Perks & Passes as primary live billing, paired with a 5-Network Rewarded Video Ad Waterfall with cryptographic Server-Side Verification (SSV).
MD

+ 1

                                  ┌──────────────────────────────────────────────┐
                                  │           PAYMENT & REWARD INGESTION         │
                                  └──────────────────────┬───────────────────────┘
                                                         │
                        ┌────────────────────────────────┴────────────────────────────────┐
                        ▼                                                                 ▼
         ┌──────────────────────────────┐                                  ┌──────────────────────────────┐
         │     DIRECT MONETIZATION      │                                  │     MINDFUL REWARDED ADS     │
         │  (INR Primary / USD Gated)   │                                  │   (5-Network SSV Waterfall)  │
         └──────────────┬───────────────┘                                  └──────────────┬───────────────┘
                        │                                                                 │
         ┌──────────────┴──────────────┐                                   ┌──────────────┴──────────────┐
         ▼                             ▼                                   ▼                             ▼
  ┌──────────────┐              ┌──────────────┐                    ┌──────────────┐              ┌──────────────┐
  │  Razorpay /  │              │ Google Play  │                    │ Google AdMob │              │ Non-Google   │
  │   Cashfree   │              │ Billing (IAP)│                    │ (ECDSA P-256)│              │ (HMAC-SHA256)│
  │ (Web Store)  │              │(Native App)  │                    │ Priority #1  │              │ Unity/Meta...│
  └──────┬───────┘              └──────┬───────┘                    └──────┬───────┘              └──────┬───────┘
         │                             │                                   │                             │
         ▼                             ▼                                   ▼                             ▼
  ┌────────────────────────────────────────────┐                    ┌────────────────────────────────────────────┐
  │  Idempotent Verification & Platform Fees   │                    │ 2.0s Cooldown Guard & Anti-Bot Validator   │
  │  (HMAC / RSA / GPA Validation)             │                    │ (public.processed_ad_transactions)         │
  └─────────────────────┬──────────────────────┘                    └─────────────────────┬──────────────────────┘
                        │                                                                 │
                        ▼                                                                 ▼
  ┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
  │                           LEDGER DURABILITY & ATOMIC ENTITLEMENT PROVISIONING                                │
  │                           (public.in_app_purchases, public.ad_reward_ledger)                                 │
  └──────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

MD

Statutory Regulatory Mandates
Consumer Protection (E-Commerce) Rules 2020 & RBI Payment Aggregator Guidelines: Full merchant disclosure, non-refundable digital goods transparency, RBI-mandated T+5 calendar day automatic reversals for failed UPI debit transactions, and 5–7 business day refund SLAs for verified technical double-debits.
MD

India DPDP Act 2023: Financial audit logs in public.in_app_purchases and public.ad_reward_ledger are isolated from soft-deletion incinerators under statutory tax accounting exceptions.
MD

Google Play Store Policy: Native Android purchases route via Google Play Billing with 15% platform tier fee deduction recorded; Web Store checkout (/store) is completely separated from native Play binaries.
MD

1. Product Catalog & Pricing Matrix (Condition C2)
Monetization is configured in backend/app/core/config.py via ENABLE_GLOBAL_USD_BILLING=false. The database schemas and billing validators maintain full dual-currency support, but international USD tiers remain hidden on the client until the flag is enabled.
MD

+ 1

Product Identifier Product Class INR Price (₹) USD Price ($) (Gated) Entitlement Scope & Ledger Yield
direct_letter_single Micro-Perk ₹29 $0.99 
+1 Direct Letter; bypasses deck, creates dialogue in public.matches.
MD

profile_unlock_single Micro-Perk ₹39 $1.49 
Unveils 35px photo blur veil for a single admired seeker.
MD

super_like_pack_3 Micro-Perk ₹49 $1.99 
+3 High-resonance Super Likes with top deck placement.
MD

spotlight_boost_24h Micro-Perk ₹79 $2.99 
24-hour priority discovery placement (+100 Boost Points).
MD

sacred_bridge_instant Micro-Perk ₹99 $3.99 
Instantly reveals WhatsApp/Instagram contact without 3-ad ritual.
MD

pass_sovereign_weekly Sovereign Pass ₹299 $9.99 
7 Days: Unlimited Swipes, Ad-Free UI, +5 Direct Letters.
MD

pass_sovereign_monthly Sovereign Pass ₹999 $29.99 
30 Days: Full Sanctuary Pass, +25 Letters, Voice Verification Badge.
MD

pass_sovereign_quarter Sovereign Pass ₹2,499 $49.99 
90 Days: Complete Access, Priority AI Wingman coaching.
MD

MD

1. Dual Payment Gateway Adapter Pattern
Implemented in backend/app/services/ using an abstract interface allowing dynamic switching via PAYMENT_GATEWAY=razorpay | cashfree in .env.
MD

  Payment Gateway Factory (PAYMENT_GATEWAY)
         │
         ├─────────────────────────────────────────┐
         ▼                                         ▼
  RazorpayAdapter                           CashfreeAdapter
  • Order Creation (Subunit: Paise)          • Order Creation (v2023-08-01 API)
  • HMAC-SHA256 (order_id|payment_id)        • HMAC-SHA256 (timestamp + raw_body)
  • Webhook Verification                     • Webhook Verification

MD

3.1 Razorpay India Adapter (backend/app/services/razorpay_service.py)
Handles order creation in integer subunits (paise) and validates payment signatures using constant-time comparison.
MD

Python

# backend/app/services/razorpay_service.py

import hmac
import hashlib
import razorpay
from typing import Dict, Any
from app.core.config import settings
from app.core.exceptions import SanctuaryException

class RazorpayService:
    def __init__(self):
        self.client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )

    def create_order(self, amount_inr: float, receipt_id: str, notes: Dict[str, str]) -> Dict[str, Any]:
        """Creates order with integer subunit conversion (paise)."""
        amount_paise = int(round(amount_inr * 100))
        data = {
            "amount": amount_paise,
            "currency": "INR",
            "receipt": receipt_id,
            "notes": notes,
            "payment_capture": 1  # Auto-capture
        }
        try:
            order = self.client.order.create(data=data)
            return order
        except Exception as e:
            raise SanctuaryException(
                error_code="RAZORPAY_ORDER_FAILED",
                message=f"Order creation failed: {str(e)}",
                status_code=502
            )

    def verify_payment_signature(self, order_id: str, payment_id: str, signature: str) -> bool:
        """Verifies HMAC-SHA256(order_id + '|' + payment_id) with constant-time comparison."""
        payload = f"{order_id}|{payment_id}".encode("utf-8")
        generated_signature = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
            payload,
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(generated_signature, signature):
            raise SanctuaryException(
                error_code="INVALID_PAYMENT_SIGNATURE",
                message="Cryptographic payment signature mismatch.",
                status_code=400
            )
        return True

    def verify_webhook_signature(self, raw_body: bytes, signature_header: str) -> bool:
        """Verifies Razorpay webhook header against raw body bytes."""
        generated_signature = hmac.new(
            settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
            raw_body,
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(generated_signature, signature_header):
            raise SanctuaryException(
                error_code="INVALID_WEBHOOK_SIGNATURE",
                message="Webhook signature verification failed.",
                status_code=400
            )
        return True

razorpay_service = RazorpayService()

MD

3.2 Cashfree Adapter Specification (backend/app/services/cashfree_service.py)
Provides seamless failover to Cashfree PG via API v2023-08-01.
MD

Python

# backend/app/services/cashfree_service.py

import hmac
import hashlib
import httpx
from typing import Dict, Any
from app.core.config import settings
from app.core.exceptions import SanctuaryException

class CashfreeService:
    def __init__(self):
        self.base_url = "https://api.cashfree.com/pg" if settings.ENVIRONMENT == "production" else "https://sandbox.cashfree.com/pg"
        self.headers = {
            "x-client-id": settings.CASHFREE_CLIENT_ID,
            "x-client-secret": settings.CASHFREE_SECRET_KEY,
            "x-api-version": "2023-08-01",
            "Content-Type": "application/json"
        }

    async def create_order(self, order_id: str, amount_inr: float, customer_id: str, customer_email: str) -> Dict[str, Any]:
        url = f"{self.base_url}/orders"
        payload = {
            "order_id": order_id,
            "order_amount": float(amount_inr),
            "order_currency": "INR",
            "customer_details": {
                "customer_id": customer_id,
                "customer_email": customer_email,
                "customer_phone": "9999999999"  # Fallback for compliance
            },
            "order_meta": {
                "return_url": f"https://urheart.app/store/orders/{order_id}"
            }
        }
        async with httpx.AsyncClient() as client:
            res = await client.post(url, json=payload, headers=self.headers, timeout=10.0)
            if res.status_code != 200:
                raise SanctuaryException(
                    error_code="CASHFREE_ORDER_FAILED",
                    message=f"Cashfree order initialization failed: {res.text}",
                    status_code=502
                )
            return res.json()

    def verify_webhook_signature(self, timestamp: str, raw_body: str, signature: str) -> bool:
        """Verifies Base64 HMAC-SHA256 signature across f'{timestamp}{raw_body}' using CASHFREE_SECRET_KEY."""
        import base64
        data_to_sign = f"{timestamp}{raw_body}".encode("utf-8")
        computed_sig = base64.b64encode(
            hmac.new(
                settings.CASHFREE_SECRET_KEY.encode("utf-8"),
                data_to_sign,
                hashlib.sha256
            ).digest()
        ).decode("utf-8")

        return hmac.compare_digest(computed_sig, signature)

cashfree_service = CashfreeService()

MD

1. Google Play In-App Billing v3 (billing_verification.py)
Handles native in-app purchases through the Google Play Developer API v3, parsing Google Play Order syntax and deducting statutory platform fees.
MD

  Client Submit (purchase_token, product_id, order_id)
                         │
                         ▼
  Regex Syntax Validation: r"^GPA\.\d{4}-\d{4}-\d{4}-\d{5}$"
                         │
                         ▼
  Google Play Developer API v3 Validation:
  purchases.products.get(packageName, productId, token)
                         │
                         ▼
  Calculate Net: amount_net = amount_gross * 0.85 (15% platform fee deduction)
                         │
                         ▼
  Insert public.in_app_purchases & Credit Entitlements Atomically

MD

Implementation Reference (backend/app/api/v1/endpoints/billing_verification.py)
Python

# backend/app/api/v1/endpoints/billing_verification.py

import re
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, get_db_session
from app.core.config import settings
from app.core.catalog import MONETIZATION_CATALOG
from app.models.domain.user import User
from app.models.domain.monetization import InAppPurchase
from app.schemas.monetization import InAppPurchaseVerifyRequest
from app.services.billing_entitlement_service import provision_user_entitlements
from app.services.google_play_service import google_play_service
from app.core.exceptions import SanctuaryException

router = APIRouter()
GPA_ORDER_REGEX = re.compile(r"^GPA\.\d{4}-\d{4}-\d{4}-\d{5}$")

@router.post("/verify-purchase", status_code=status.HTTP_200_OK)
async def verify_google_play_purchase(
    request: InAppPurchaseVerifyRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    # 1. Validate GPA Order ID syntax
    if not GPA_ORDER_REGEX.match(request.order_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error_code": "INVALID_GPA_ORDER_SYNTAX", "message": "Malformed Google Play order ID."}
        )

    # 2. Check Idempotency Replay (Order ID and Purchase Token)
    existing_purchases_res = await session.execute(
        select(InAppPurchase).where(
            (InAppPurchase.transaction_reference == request.order_id) |
            (InAppPurchase.purchase_token == request.purchase_token)
        )
    )
    matches = existing_purchases_res.scalars().all()
    if len(matches) > 1:
        # Split identifiers matching different historical purchases
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"success": False, "error_code": "IDEMPOTENCY_IDENTIFIER_CONFLICT", "message": "Order ID and purchase token resolve to different historical purchases."}
        )
    elif len(matches) == 1:
        matched = matches[0]
        if matched.transaction_reference == request.order_id and matched.purchase_token == request.purchase_token:
            if matched.user_id != current_user.id or matched.product_identifier != request.product_identifier:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={"success": False, "error_code": "PURCHASE_OWNER_OR_PRODUCT_MISMATCH", "message": "Purchase belongs to a different account or product."}
                )
            return {"success": True, "message": "Transaction already verified.", "status": "idempotent_ok"}
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"success": False, "error_code": "PURCHASE_IDENTIFIER_MISMATCH", "message": "Purchase identifier conflict with existing transaction."}
            )

    # 3. Cryptographically Verify Google Play API v3 Receipt
    # Validates token & package with Google Play Developer API (purchases.products.get)
    verified_product = await google_play_service.verify_purchase_token(
        package_name="com.urheart.app",
        product_id=request.product_identifier,
        token=request.purchase_token
    )
    if not verified_product or verified_product.get("purchaseState") != 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error_code": "PLAY_PURCHASE_UNVERIFIED", "message": "Google Play purchase verification failed."}
        )

    # Bind verification to Google's authoritative order ID
    google_order_id = verified_product.get("orderId")
    if google_order_id and google_order_id != request.order_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error_code": "ORDER_ID_MISMATCH", "message": "Request order ID does not match Google Play verified order."}
        )

    # Fail closed on catalog lookup (prevent client-supplied amount manipulation)
    catalog_item = MONETIZATION_CATALOG.get(request.product_identifier)
    if not catalog_item:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "error_code": "PRODUCT_NOT_IN_CATALOG", "message": "Unknown product identifier."}
        )
    amount_gross = Decimal(str(catalog_item["inr"]))
    play_fee_rate = Decimal(str(getattr(settings, "GOOGLE_PLAY_FEE_RATE", "0.15")))  # Tiered 15% rate under $1M ARR program
    platform_fee = (amount_gross * play_fee_rate).quantize(Decimal("0.01"))
    amount_net = amount_gross - platform_fee

    try:
        # 4. Insert Audit Ledger (Enforces UNIQUE purchase_token constraint atomically)
        purchase = InAppPurchase(
            user_id=current_user.id,
            transaction_reference=request.order_id,
            purchase_token=request.purchase_token,
            product_identifier=request.product_identifier,
            store="google_play",
            currency="INR",
            amount_gross=amount_gross,
            platform_fee=platform_fee,
            amount_net=amount_net,
            status="completed"
        )
        session.add(purchase)
        await session.flush()

        # 5. Provision Entitlements Atomically
        await provision_user_entitlements(current_user, request.product_identifier, session)
        await session.commit()
    except IntegrityError:
        await session.rollback()
        # Confirm matching purchase exists from a concurrent worker; re-raise if unrelated error
        existing = await session.execute(
            select(InAppPurchase).where(
                InAppPurchase.purchase_token == request.purchase_token,
                InAppPurchase.transaction_reference == request.order_id,
                InAppPurchase.user_id == current_user.id,
                InAppPurchase.product_identifier == request.product_identifier
            )
        )
        if existing.scalar_one_or_none():
            return {"success": True, "message": "Transaction already verified.", "status": "idempotent_ok"}
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"success": False, "error_code": "PURCHASE_INTEGRITY_CONFLICT", "message": "Purchase integrity constraint violation."}
        )

    return {
        "success": True,
        "product_identifier": request.product_identifier,
        "entitlements_provisioned": True
    }

MD

1. Web Store Guest Checkout & Zero-Loss Entitlements (web_store.py)
The Web Sanctuary Store ([https://urheart.app/store](https://urheart.app/store)) enables guest checkout over UPI or card, logging purchases to public.pending_web_entitlements. Entitlements are automatically claimed when the user signs in to the mobile application.
MD

+ 1

  GUEST CHECKOUT FLOW:
  1. Guest visits <https://urheart.app/store> (No app login required)
  2. Enters target email: <seeker@example.com>
  3. Completes payment via Razorpay UPI intent
  4. Webhook records entitlement in public.pending_web_entitlements
     (status: 'paid_pending_claim')
                         │
                         ▼
  ZERO-LOSS CLAIMING UPON APP LOGIN:
  5. Seeker authenticates in mobile client with <seeker@example.com>
  6. Client triggers POST /api/v1/store/claim-pending
  7. claim_pending_web_store_entitlements() executes atomically:
     • Queries public.pending_web_entitlements WHERE email = current_user.email
     • Provisions micro-perks, passes, and credits to user row
     • Updates status to 'claimed', setting claimed_by_user_id = current_user.id

MD

Atomic Entitlement Claiming Implementation
Python

# backend/app/services/web_store_service.py

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.domain.user import User
from app.models.domain.monetization import PendingWebEntitlement
from app.services.billing_entitlement_service import provision_user_entitlements

async def claim_pending_web_store_entitlements(user: User, session: AsyncSession) -> int:
    """Finds and claims all pending entitlements for user's email atomically."""
    if not user.email:
        return 0

    query = select(PendingWebEntitlement).where(
        PendingWebEntitlement.email == user.email,
        PendingWebEntitlement.status == "paid_pending_claim"
    ).with_for_update()

    result = await session.execute(query)
    entitlements = result.scalars().all()
    claimed_count = 0

    for ent in entitlements:
        # Provision entitlements to user model
        await provision_user_entitlements(user, ent.product_identifier, session)
        
        # Mark entitlement claimed
        ent.status = "claimed"
        ent.claimed_by_user_id = user.id
        claimed_count += 1

    if claimed_count > 0:
        await session.commit()

    return claimed_count

MD

1. 5-Network Rewarded Ad Mediation Waterfall & Cryptographic SSV
UR-Heart implements a client-mediated waterfall across 5 ad networks, backed by cryptographic server verification (SSV).
MD

┌────────────────────────────────────────────────────────────────────────┐
│               5-NETWORK WATERFALL MEDIATION CASCADE                     │
├────────────────────────────────────────────────────────────────────────┤
│ 1. Google AdMob (Priority 1: ECDSA P-256 Public Key Verification)      │
│ 2. Unity Ads    (Priority 2: HMAC-SHA256 Secret Verification)          │
│ 3. Meta Network (Priority 3: HMAC-SHA256 Secret Verification)          │
│ 4. Chartboost   (Priority 4: HMAC-SHA256 Secret Verification)          │
│ 5. Liftoff      (Priority 5: Remnant Demand / 99.9% Fill Safety Net)   │
└────────────────────────────────────────────────────────────────────────┘

MD

6.1 Cryptographic SSV Verification Engine (ads_ssv.py)
Google AdMob (ECDSA P-256 Verification):

Fetches Google public keys from [https://www.gstatic.com/admob/reward/verifier-keys.json](https://www.gstatic.com/admob/reward/verifier-keys.json) (cached 24 hours).
MD

Reconstructs the canonical query string excluding signature and key_id.
MD

Decodes Base64URL ASN.1 DER signature and verifies against Google's public key with SHA-256.
MD

Non-Google HMAC-SHA256 Verification:

Evaluates query strings for Meta, Unity, Chartboost, and Liftoff callbacks using pre-shared secrets.
MD

Python

# backend/app/services/ads_ssv_service.py

import base64
import hashlib
import hmac
import json
import httpx
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import load_der_public_key
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from app.core.config import settings
from app.core.exceptions import SanctuaryException

ADMOB_KEYS_CACHE = {}

async def fetch_admob_public_keys(force_refresh: bool = False) -> dict:
    global ADMOB_KEYS_CACHE
    if ADMOB_KEYS_CACHE and not force_refresh:
        return ADMOB_KEYS_CACHE
    url = "https://www.gstatic.com/admob/reward/verifier-keys.json"
    async with httpx.AsyncClient() as client:
        res = await client.get(url, timeout=5.0)
        ADMOB_KEYS_CACHE = {
            str(key["keyId"]): key["pem"]
            for key in res.json().get("keys", [])
            if "keyId" in key and "pem" in key
        }
        return ADMOB_KEYS_CACHE

async def verify_admob_ssv(query_params: dict) -> bool:
    """Verifies AdMob ECDSA P-256 ASN.1 DER signature."""
    signature_b64 = query_params.get("signature")
    key_id = query_params.get("key_id")
    if not signature_b64 or not key_id:
        return False

    # Canonical query string construction (sorted, excluding signature & key_id)
    filtered = {k: v for k, v in query_params.items() if k not in ("signature", "key_id")}
    canonical_qs = "&".join(f"{k}={filtered[k]}" for k in sorted(filtered.keys()))

    try:
        # Move decoding inside guarded block with padding normalization
        padded_b64 = signature_b64 + "=" * ((4 - len(signature_b64) % 4) % 4)
        raw_sig = base64.urlsafe_b64decode(padded_b64)

        # Refresh cache on miss or key rotation
        key_pem = ADMOB_KEYS_CACHE.get(str(key_id))
        if not key_pem:
            await fetch_admob_public_keys(force_refresh=True)
            key_pem = ADMOB_KEYS_CACHE.get(str(key_id))
        if not key_pem:
            return False

        from cryptography.hazmat.primitives.serialization import load_pem_public_key
        public_key = load_pem_public_key(key_pem.encode("utf-8"))
        public_key.verify(raw_sig, canonical_qs.encode("utf-8"), ec.ECDSA(hashes.SHA256()))
        return True
    except Exception:
        return False

def verify_hmac_ssv(canonical_qs: str, signature: str, secret: str) -> bool:
    """Verifies non-Google SSV callbacks (Meta, Unity, Chartboost, Liftoff)."""
    expected = hmac.new(secret.encode("utf-8"), canonical_qs.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)

MD

6.2 SSV Custom Data Contract & Rewards
Custom data payload syntax: {user_id}:{ad_type}:{target_id}.
MD

  quick_reflection       ──► +10 Swipes, +10 Boost Points (10s video)
  deep_resonance         ──► +1 Direct Letter, +25 Boost Points (20s video)
  sacred_bridge_reveal   ──► Advances Bridge counter +1/3 (30s video)
  morning_harvest_unlock ──► Scaled by sleep multiplier (1.5x - 2.0x)
  daily_streak_boost     ──► Extends mindful streak by 24 hours

MD

Mandatory Rate Limiting & Cooldown Guard
Claims are throttled via SlowAPI (30/minute) and enforce a mandatory 2.0-second database-level cooldown between claims to eliminate automated replay attacks:
MD

Python

# Cooldown assertion snippet in ads_ssv.py

if user.last_streak_ad_at and (datetime.now(timezone.utc) - user.last_streak_ad_at).total_seconds() < 2.0:
    raise SanctuaryException(
        error_code="AD_CLAIM_COOLDOWN_ACTIVE",
        message="Please pause mindfully. 2.0-second pause required between claims.",
        status_code=429
    )

MD

6.3 Web/PWA Parity: WebMindfulSponsorDialog
For web and iOS PWA clients where native mobile ad SDKs (AdMob, Unity) are unsupported, the client presents a 15-second mindful reflection dialog with breathing exercises, preserving reward parity without runtime crashes.
MD

Dart

// lib/core/ads/web_mindful_sponsor_dialog.dart
import 'dart:async';
import 'package:flutter/material.dart';
import '../theme/glass_tokens.dart';
import '../theme/widgets/sanctuary_glass_container.dart';

class WebMindfulSponsorDialog extends StatefulWidget {
  final VoidCallback onCompleted;

  const WebMindfulSponsorDialog({super.key, required this.onCompleted});

  @override
  State<WebMindfulSponsorDialog> createState() => _WebMindfulSponsorDialogState();
}

class _WebMindfulSponsorDialogState extends State<WebMindfulSponsorDialog> {
  int _secondsLeft = 15;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(const Duration(seconds: 1), (t) {
      if (_secondsLeft > 1) {
        setState(() => _secondsLeft--);
      } else {
        t.cancel();
        widget.onCompleted();
        Navigator.pop(context);
      }
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: Colors.transparent,
      child: SanctuaryGlassContainer(
        borderRadius: 24,
        blurSigma: 24,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.self_improvement, size: 48, color: SanctuaryGlassTokens.brandPine),
            const SizedBox(height: 16),
            const Text(
              "Mindful Reflection Moment",
              style: TextStyle(fontFamily: 'PlayfairDisplay', fontSize: 18, fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 8),
            const Text(
              "Breathe deeply. Your reward unlocks in peace.",
              textAlign: TextAlign.center,
              style: TextStyle(fontFamily: 'PlusJakartaSans', fontSize: 13),
            ),
            const SizedBox(height: 20),
            CircularProgressIndicator(
              value: (15 -_secondsLeft) / 15.0,
              color: SanctuaryGlassTokens.brandSacredGold,
            ),
            const SizedBox(height: 12),
            Text("$_secondsLeft s", style: const TextStyle(fontWeight: FontWeight.bold)),
          ],
        ),
      ),
    );
  }
}

MD

1. Verification & Automated Test Suites
Monetization, signature validation, and auction flows are validated via the test suite below:
MD

Bash

# 1. Verify Razorpay order creation, payment signatures, and webhooks

pytest backend/tests/test_razorpay_production.py

# 2. Verify 5-Network Ad SSV Waterfall, cryptographic signatures & 2.0s cooldown

pytest backend/tests/test_ads_dynamic_auction_and_antiban.py

# 3. Verify monetization catalog and entitlement provisions

pytest backend/tests/test_phase5_monetization.py

# 4. Verify Flutter client sleep multipliers and auction state

flutter test test/dynamic_slumber_auction_antiban_test.dart
