1. Master Router Topology & Aggregation Architecture
UR-Heart Sanctuary's FastAPI application mounts 28 isolated router modules exposing 255 operations under the /api/v1 namespace, alongside SSR statutory portals mounted at root /, /statutory/, and /api/v1/statutory/.
MD

                                  ┌──────────────────────────────────────────────┐
                                  │           FastAPI Root Lifespan              │
                                  │            (backend/app/main.py)             │
                                  └──────────────────────┬───────────────────────┘
                                                         │
                        ┌────────────────────────────────┼────────────────────────────────┐
                        ▼                                ▼                                ▼
         ┌──────────────────────────────┐ ┌──────────────────────────────┐ ┌──────────────────────────────┐
         │     Statutory SSR Engine     │ │   Real-Time WebSocket Core   │ │     API v1 Master Router     │
         │  GET /, /privacy, /terms ... │ │      WS /ws/chat?ticket=     │ │          /api/v1/*           │
         │ (statutory_pages.py - 27 rts)│ │    (chat_websocket.py)       │ │  (backend/app/api/v1/router) │
         └──────────────────────────────┘ └──────────────────────────────┘ └──────────────┬───────────────┘
                                                                                          │
                        ┌────────────────────────────────┬────────────────────────────────┼─────────────────┐
                        ▼                                ▼                                ▼                 ▼
        ┌──────────────────────────────┐ ┌──────────────────────────────┐ ┌────────────────────────┐ ┌────────────────┐
        │  Auth & Identity (6 Routers) │ │ Kinship & Social (6 Routers) │ │Monetization & Ads(4 Rts)│ │Governance (12) │
        │  auth, preferences, profile, │ │ feed, resonances, chat_api,  │ │ billing_verification,  │ │ admin_portal,  │
        │  crypto_registry, telemetry, │ │ blind_date, moderation,      │ │ billing_webhook,       │ │ legal_vault,   │
        │  underage_quarantine         │ │ ws_ticket                    │ │ ads_ssv, web_store     │ │ kyc, health... │
        └──────────────────────────────┘ └──────────────────────────────┘ └────────────────────────┘ └────────────────┘

MD

Master Aggregator Implementation (backend/app/api/v1/router.py)
All modular routers are aggregated centrally with strictly typed prefixes and tags:
MD

Python

# backend/app/api/v1/router.py

from fastapi import APIRouter
from app.api.v1.endpoints import (
    account_incinerator, admin_kyc, admin_portal, ads_ssv,
    ai_cluster, ai_sanctuary, auth, billing_verification,
    billing_webhook, blind_date, chat_api, crypto_registry,
    feed, health, kyc_verification, legal_compliance,
    media, moderation, notifications, preferences,
    profile, resonances, statutory_pages, telemetry,
    underage_quarantine, web_store, ws_ticket
)

api_router = APIRouter()

# 1. Health & Sleepless Sentinel

api_router.include_router(health.router, tags=["HealthSentinel"])

# 2. Authentication, Identity & Hardware Quarantine

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(underage_quarantine.router, prefix="/auth", tags=["AgeGateQuarantine"])
api_router.include_router(account_incinerator.router, prefix="/auth", tags=["AccountIncineration"])

# 3. User Profile, Preferences & Telemetry

api_router.include_router(profile.router, prefix="/profile", tags=["Profile"])
api_router.include_router(preferences.router, prefix="/user/preferences", tags=["Preferences"])
api_router.include_router(telemetry.router, prefix="/telemetry", tags=["Telemetry"])
api_router.include_router(crypto_registry.router, prefix="/crypto", tags=["CryptoRegistry"])

# 4. Feed Discovery, Resonances & Moderation

api_router.include_router(feed.router, prefix="/feed", tags=["DiscoveryFeed"])
api_router.include_router(resonances.router, prefix="/resonances", tags=["Resonances"])
api_router.include_router(moderation.router, prefix="/moderation", tags=["Moderation"])

# 5. Dialogue Chamber, WebSockets & Notifications

api_router.include_router(chat_api.router, prefix="/chat", tags=["DialogueChamber"])
api_router.include_router(ws_ticket.router, prefix="/chat", tags=["WebSocketTicket"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])

# 6. Condition C1 Blind Date Subsystem

api_router.include_router(blind_date.router, prefix="/blind-date", tags=["BlindDateC1"])

# 7. AI Sanctuary, Companion & Wingman

api_router.include_router(ai_cluster.router, prefix="/ai", tags=["AICluster"])
api_router.include_router(ai_sanctuary.router, prefix="/ai/eva", tags=["AISanctuary"])

# 8. Media Storage & Ephemeral KYC

api_router.include_router(media.router, prefix="/media", tags=["MediaStorage"])
api_router.include_router(kyc_verification.router, prefix="/kyc", tags=["KYCVerification"])

# 9. Monetization, Ad SSV & Sovereign Store (Condition C2)

api_router.include_router(billing_verification.router, prefix="/billing", tags=["BillingVerification"])
api_router.include_router(billing_webhook.router, prefix="/billing/webhook", tags=["BillingWebhooks"])
api_router.include_router(ads_ssv.router, prefix="/ads", tags=["AdsSSVWaterfall"])
api_router.include_router(web_store.router, prefix="/store", tags=["WebSanctuaryStore"])

# 10. Legal Vault, DPDP Portability & Grievances

api_router.include_router(legal_compliance.router, prefix="/vault", tags=["LegalVaultDPDP"])

# 11. Administration & Escalations

api_router.include_router(admin_portal.router, prefix="/admin/portal", tags=["AdminPortal"])
api_router.include_router(admin_kyc.router, prefix="/admin/kyc", tags=["AdminKYC"])

MD

1. Dependency Injection, Security Guards & Rate Limiting Pipeline
All endpoints rely on reusable FastAPI dependencies located in backend/app/api/deps.py.
MD

2.1 Authentication & Role Dependency Contracts
Python

# backend/app/api/deps.py

from typing import AsyncGenerator
from uuid import UUID
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session_factory
from app.core.security import decode_access_token
from app.models.domain.user import User
from app.core.exceptions import SanctuaryException

security_bearer = HTTPBearer(auto_error=True)

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provides an isolated async database session per request."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security_bearer),
    session: AsyncSession = Depends(get_db_session)
) -> User:
    """Decodes JWT Bearer token and returns active non-deleted user."""
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise SanctuaryException(
            error_code="INVALID_TOKEN",
            message="Bearer session invalid or expired.",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    user_id = UUID(payload["sub"])
    user = await session.get(User, user_id)
    if not user or user.deleted_at is not None:
        raise SanctuaryException(
            error_code="USER_NOT_FOUND",
            message="Seeker account inactive or soft-deleted.",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    return user

async def require_superadmin(current_user: User = Depends(get_current_user)) -> User:
    """Enforces role = 'superadmin' access control."""
    if current_user.role != "superadmin":
        raise SanctuaryException(
            error_code="ACCESS_DENIED",
            message="Superadmin clearance required.",
            status_code=status.HTTP_403_FORBIDDEN
        )
    return current_user

MD

2.2 SlowAPI Rate Limiting Contracts
Injected via backend/app/core/limiter.py using client IP address keys:
MD

Global Default: 120/minute per IP address.
MD

Auth Endpoints: 10/minute per IP address (/auth/login, /auth/register-intent, /auth/send-magic-link).
MD

AI Endpoints: 20/minute per user/IP (/ai/eva/*, /ai/icebreakers, /ai/bio-polish).
MD

Ad Reward Claims: 30/minute per user, enforced with a strict 2.0-second server-side database cooldown.
MD

1. Granular Route Reference: All 28 Endpoint Modules
Module 1: account_incinerator.py
Irrevocably purges profile, biometric anchors, chat history, and relational data across database, Supabase Storage, and Supabase Auth under DPDP Act 2023 Section 12.
MD

DELETE /api/v1/auth/incinerate-account

MD

Auth: Depends(get_current_user)

MD

Payload: {"confirmation_text": "INCINERATE MY SANCTUARY PERMANENTLY"}

Response: 200 OK -> SanctuaryResponse[dict]

Operation: Sets deleted_at = NOW(), deletes files under users/{auth_id}/ in ur-heart-media, deletes record in auth.users, cascades dependent rows.
MD

Module 2: admin_kyc.py
Superadmin biometric verification queue management.
MD

GET /api/v1/admin/kyc/escalations

MD

Auth: Depends(require_superadmin)

MD

Query: page: int = 1, page_size: int = 20, status: str = "pending"

Response: 200 OK -> SanctuaryResponse[List[AdminKycEscalationResponse]]

GET /api/v1/admin/kyc/pending-queue

MD

Auth: Depends(require_superadmin)

MD

Response: 200 OK -> SanctuaryResponse[List[PendingKycQueueItem]]

POST /api/v1/admin/kyc/resolve

MD

Auth: Depends(require_superadmin)

MD

Payload: {"user_id": UUID, "action": "approve" | "reject", "reasoning": str}

Response: 200 OK -> SanctuaryResponse[dict]

GET /api/v1/admin/kyc/media/{user_id}/{media_type}

MD

Auth: Depends(require_superadmin)

MD

Params: media_type: "anchor" | "video"

Response: 200 OK -> StreamingResponse(image/webp or video/mp4)

MD

Module 3: admin_portal.py
Platform governance and metrics dashboard ([https://urheart.app/admin](https://urheart.app/admin)).
MD

GET /admin & GET /admin/portal: Serves admin dashboard web UI.
MD

POST /api/v1/admin/portal/auth/login: Admin password authentication -> TokenResponse.
MD

GET /api/v1/admin/portal/stats: Total seekers, KYC metrics, active matches, daily passes.
MD

GET /api/v1/admin/portal/users: Search and list users with pagination (page, query, tier).
MD

POST /api/v1/admin/portal/users/{user_id}/ban: Bans user and logs admin action in admin_audit_logs.
MD

POST /api/v1/admin/portal/users/{user_id}/unban: Restores banned user account.
MD

POST /api/v1/admin/portal/users/{user_id}/set-kyc: Overrides KYC verification status.
MD

GET /api/v1/admin/portal/config: Reads platform dynamic configuration flags.
MD

PUT /api/v1/admin/portal/config: Updates dynamic configuration in database.
MD

GET /api/v1/admin/portal/audit-logs: Streams paginated admin_audit_logs.
MD

Module 4: ads_ssv.py
5-Network Rewarded Ad Server-Side Verification (SSV) callback engine and user reward claiming.
MD

GET /api/v1/ads/verify-reward

MD

Auth: Public callback (SSV signature verified cryptographically)
MD

Query Params: Canonical SSV parameters (custom_data, transaction_id, signature, key_id)
MD

Networks: Google AdMob (ECDSA P-256), Meta, Unity, Chartboost, Liftoff (HMAC-SHA256)
MD

Response: 200 OK -> {"status": "verified", "transaction_id": str}

POST /api/v1/ads/claim-reward

MD

Auth: Depends(get_current_user)

MD

Rate Limit: Max 30/minute, mandatory 2.0s cooldown between user claims
MD

Payload: {"transaction_id": str, "ad_type": str, "network": str}

Response: 200 OK -> {"success": true, "reward_type": str, "credits_added": int, "new_balance": int}

GET /api/v1/ads/streak-status

MD

Auth: Depends(get_current_user)

MD

Response: 200 OK -> Streak count, night slumber multiplier (1.5x–2.0x), time until expiry.
MD

Module 5: ai_cluster.py
LLM reasoning cluster utilizing Groq Llama-3.3-70b and Groq Vision.
MD

POST /api/v1/ai/icebreakers

MD

Auth: Depends(get_current_user)

MD

Rate Limit: 20/minute

MD

Payload: {"target_profile_id": UUID}

Engine: Groq Llama-3.3-70b-versatile analyzing mutual values and bio prompts.
MD

Response: 200 OK -> {"icebreakers": [str, str, str]}

MD

POST /api/v1/ai/bio-polish

MD

Auth: Depends(get_current_user)

MD

Payload: {"raw_bio": str} (max 500 chars)

Response: 200 OK -> {"polished_bio": str} (poetic, authentic, non-superficial prose)
MD

POST /api/v1/ai/kyc-liveness

MD

Auth: Depends(get_current_user)

MD

Engine: Groq Vision comparing 3-second live selfie video against anchor photo.
MD

Response: 200 OK -> {"confidence_score": int, "match_passed": bool, "reasoning": str}

MD

Module 6: ai_sanctuary.py
Conversational companions Eva / Arjun and Wingman coaching.
MD

POST /api/v1/ai/eva/chat

MD

Auth: Depends(get_current_user)

MD

Rate Limit: 20/minute

MD

Payload: {"message": str, "persona": "eva" | "arjun"}

Enforcement: Roman Hindi / empathetic tone preservation.
MD

Response: 200 OK -> {"reply": str, "timestamp": ISO8601}

POST /api/v1/ai/eva/chat-sparks: Contextual prompt suggestions for kinship deepening.
MD

POST /api/v1/ai/eva/wingman

MD

Auth: Depends(get_current_user)

MD

Engine: Gemini 2.5 Flash analyzing active match dialogue thread.
MD

Payload: {"match_id": UUID, "last_messages_count": int}

Response: 200 OK -> {"suggestions": [str, str], "empathy_insight": str}

MD

POST /api/v1/ai/eva/grievance-assist: Guides user in drafting structured grievance dossiers under IT Rules 2021.
MD

POST /api/v1/ai/eva/feedback & POST /api/v1/feedback: Records bug reports and suggestions.
MD

Module 7: auth.py
Onboarding, passwordless login, and Google OAuth2 synchronization.
MD

POST /api/v1/auth/register-intent

MD

Payload: RegisterIntentRequest (dob: date, device_fingerprint: str)
MD

Behavior: Evaluates 18+ age gate; blocks and records into underage_quarantine_registry on violation.
MD

Response: 200 OK -> {"eligible": true} or 403 Forbidden (UNDERAGE_QUARANTINE_TRIGGERED)
MD

POST /api/v1/auth/login: Supabase GoTrue Auth password authentication -> TokenResponse.
MD

POST /api/v1/auth/send-magic-link: Generates cryptographic magic link email -> {"dispatched": true}.
MD

POST /api/v1/auth/verify-magic-link: Exchanges magic link token for session access & refresh tokens.
MD

GET /api/v1/auth/verify & GET /api/v1/auth/callback: Deep-linking landing redirects.
MD

GET /api/v1/auth/sync: Syncs installation UUID and performs zero-on-delete verification.
MD

POST /api/v1/auth/google-sync

MD

Payload: GoogleSyncRequest (id_token: str, installation_uuid: Optional[str])
MD

Behavior: Verifies RS256 certs against _google_oauth_keys_cache, checks aud == GOOGLE_SERVER_CLIENT_ID, maps RFC-4122 UUID v5 deterministically.
MD

Response: 200 OK -> TokenResponse

MD

GET /api/v1/auth/me & GET /api/v1/users/me: Returns profile of current authenticated user.
MD

GET /api/v1/auth/verification-status: Long-polling status check for magic link completion.
MD

Module 8: billing_verification.py
Google Play Developer API v3 receipt and order validation.
MD

POST /api/v1/billing/verify-purchase

MD

Auth: Depends(get_current_user)

MD

Payload: {"purchase_token": str, "product_id": str, "order_id": str}

Validation: Regex r"^GPA\.\d{4}-\d{4}-\d{4}-\d{5}$", validates against Google Play Developer API v3, logs 15% platform fee into in_app_purchases.
MD

Response: 200 OK -> {"verified": true, "entitlements_provisioned": [str]}

Module 9: billing_webhook.py
Webhooks from Razorpay and RevenueCat.
MD

POST /api/v1/billing/webhook/razorpay

MD

Header: X-Razorpay-Signature

MD

Verification: Raw body HMAC-SHA256 comparison via hmac.compare_digest with RAZORPAY_WEBHOOK_SECRET.
MD

Events: order.paid, payment.captured.
MD

Response: 200 OK -> {"status": "acknowledged"}

POST /api/v1/billing/webhook/revenuecat: Ingests RevenueCat lifecycle events.
MD

POST /api/v1/billing/purchase/audit: Audits transactions against public.in_app_purchases.
MD

Module 10: blind_date.py (Condition C1)
Anonymous 180s live dialogue subsystem.
MD

POST /api/v1/blind-date/queue/join

MD

Gate Check: Queries 30-day MAU:

SQL

SELECT count(id) FROM public.users
WHERE deleted_at IS NULL AND last_active_at >= NOW() - INTERVAL '30 days'

MD

If MAU < 1,000,000 and ENABLE_BLIND_DATE_OVERRIDE=false -> returns 403 Forbidden (milestone_locked).
MD

Payload: BlindDateQueueJoin

MD

Response: 200 OK -> {"status": "queued", "position": int}

POST /api/v1/blind-date/queue/cancel: Removes user from queue.
MD

GET /api/v1/blind-date/queue/status: Polls pairing status -> {"status": "paired", "session_id": UUID}.
MD

GET /api/v1/blind-date/session/{session_id}: Fetches active session, veil timers, and icebreaker prompt.
MD

POST /api/v1/blind-date/session/{session_id}/message: Ephemeral session message.
MD

GET /api/v1/blind-date/session/{session_id}/messages: Retrieves session chat history.
MD

POST /api/v1/blind-date/session/{session_id}/extend: Adds +3 minutes to session timer (max extension count).
MD

POST /api/v1/blind-date/session/{session_id}/resonate: Submits 'resonate' or 'pass'; provisions active match upon mutual resonance.
MD

GET /api/v1/blind-date/eligibility: Returns milestone progress toward 1,000,000 active souls and daily passes.
MD

POST /api/v1/blind-date/claim-ad-pass: Grants bonus session pass via rewarded ad.
MD

Module 11: chat_api.py
1:1 Encrypted kinship dialogue endpoints.
MD

GET /api/v1/chat/threads: Lists active match dialogues with unread counts.
MD

GET /api/v1/chat/threads/{match_id}/messages: Paginated dialogue history (before_id: int, limit: int = 50).
MD

POST /api/v1/chat/threads/{match_id}/messages: Sends encrypted message with client-side deduplication via client_id.
MD

POST /api/v1/chat/threads/{match_id}/read: Marks dialogue messages as read.
MD

GET /api/v1/chat/threads/{match_id}/peer: Returns peer profile.
MD

GET /api/v1/chat/threads/{match_id}/bridge: Returns Sacred Contact Bridge token status.
MD

POST /api/v1/chat/threads/{match_id}/bridge/consent: Submits affirmative consent for handle exchange.
MD

POST /api/v1/chat/threads/{match_id}/bridge/reveal: Consumes token/perk to reveal peer social handle.
MD

GET /api/v1/chat/sparks: Fetches conversational sparks.
MD

GET /api/v1/chat/threads/{match_id}/closure: Returns thread closure state.
MD

POST /api/v1/chat/threads/{match_id}/closure: Mindful closure protocol ("Pass with Grace") with template key.
MD

GET /api/v1/chat/closure-templates: Returns curated closure templates.
MD

Module 12: chat_websocket.py
WebSocket relay server at WS /ws/chat. Authenticated via single-use ticket; provides in-memory routing (<5ms delivery). Documented in .docs/06_WEBSOCKET_PROTOCOL_AND_NOTIFICATIONS.md.
MD

+ 2

Module 13: crypto_registry.py
Cryptographic public key exchange for client-side E2EE.
MD

POST /api/v1/crypto/rotate-key

MD

Auth: Depends(get_current_user)

MD

Payload: {"public_encryption_key": str} (64-byte hex string)
MD

Response: 200 OK -> {"rotated": true}

GET /api/v1/crypto/public-key/{user_id}: Retrieves public key for a seeker.
MD

Module 14: feed.py (Condition C3)
Discovery deck engine backed by public.discovery_profiles.
MD

GET /api/v1/feed

MD

Auth: Depends(get_current_user)

MD

Logic: Enforces reciprocal orientation filter, self-exclusion perimeter, and DPDP coordinate fuzzing (~1.1 km rounding).
MD

Response: 200 OK -> List[ProfilePublicResponse]

MD

POST /api/v1/swipes

MD

Auth: Depends(get_current_user)

MD

Payload: SwipeRequest (target_id: UUID, action: 'like' | 'pass' | 'superlike', optional direct_letter_text)
MD

Response: 200 OK -> {"is_match": bool, "match_id": Optional[UUID], "swipes_remaining": int}

GET /api/v1/swipes/passed: Retrieves profiles in Pass Vault.
MD

DELETE /api/v1/swipes/pass/{target_id}: Restores passed profile back to deck.
MD

POST /api/v1/feed/{target_id}/photo-reveal/request: Requests bilateral photo un-veiling.
MD

POST /api/v1/feed/{requester_id}/photo-reveal/respond: Accepts or declines photo reveal request.
MD

Module 15: health.py
Sleepless keep-alive sentinel for UptimeRobot monitoring.
MD

GET /api/v1/health & HEAD /api/v1/health: Returns headers X-Sanctuary-Alive: true and 0-byte body on HEAD request with 0ms database overhead.
MD

Module 16: kyc_verification.py
Multipart video selfie and anchor photo biometric verification.
MD

POST /api/v1/kyc/verify-live

MD

Auth: Depends(get_current_user)

MD

Files: anchor_photo: UploadFile, selfie_video: UploadFile

MD

Statutory Purge: Temporary video and frames are purged in
<
60
 seconds
<60 seconds post-verification.
MD

Response: 200 OK -> {"verified": bool, "escalated": bool}

MD

Module 17: legal_compliance.py
DPDP Act 2023 Sections 6, 11, 14, and IT Rules 2021 Rule 3(2).
MD

POST /api/v1/vault/grievance: Submits grievance dossier into public.grievance_dossiers.
MD

GET /api/v1/vault/grievances: Lists user-filed grievances.
MD

GET /api/v1/vault/grievance/track/{reference_id}: Tracks status and statutory 15-day resolution SLA.
MD

POST /api/v1/vault/export-data: Generates DPDP Section 11 data portability request.
MD

GET /api/v1/vault/export-status/{request_id}: Checks export preparation status.
MD

GET /api/v1/vault/export-pdf/{request_id}: Downloads cryptographically signed data export PDF.
MD

GET /api/v1/vault/nominee & POST /api/v1/vault/nominee: Manages digital nominee under DPDP Section 14.
MD

POST /api/v1/vault/block, GET /api/v1/vault/blocked, DELETE /api/v1/vault/blocked/{blocked_user_id}: Bilateral user blocking controls.
MD

Module 18: media.py
Storage adapter router with Cloudflare R2 presigned URLs and Supabase Storage fallback.
MD

POST /api/v1/media/presigned-url

MD

Auth: Depends(get_current_user)

MD

Payload: {"slot_number": int, "content_type": "image/webp"}

Response: 200 OK -> Cloudflare R2 S3v4 presigned PUT URL. If credentials absent, falls back to direct server upload.
MD

+ 1

PUT /api/v1/media/upload/{user_id}/{slot_number}: Fallback direct media upload route into Supabase Storage bucket ur-heart-media.
MD

GET /api/v1/media/voice/{user_id}/{filename}: Serves streamed voice spark audio with byte-range seeking.
MD

Module 19: moderation.py
Automated content moderation scanning.
MD

POST /api/v1/moderation/photo: OpenCV skin ratio check and Tesseract OCR contact leak detection.
MD

POST /api/v1/moderation/chat: NLP check scanning for off-platform financial solicitations or harassment.
MD

Module 20: notifications.py
FCM HTTP v1 background push notification lifecycle.
MD

GET /api/v1/notifications: Fetches in-app notification history.
MD

POST /api/v1/notifications/mark-read: Marks notifications as read.
MD

POST /api/v1/notifications/register-token: Registers active device FCM token in device_fcm_tokens.
MD

POST /api/v1/notifications/unregister-token: Deactivates device FCM token.
MD

POST /api/v1/notifications/test-push: Sends diagnostic test push notification.
MD

GET /api/v1/notifications/push-health: Verifies FCM delivery engine status.
MD

Module 21: preferences.py
User privacy and discovery preferences.
MD

GET /api/v1/user/preferences: Returns incognito, discreet mode, night slumber, and contact bridge flags.
MD

PUT /api/v1/user/preferences: Updates user privacy settings.
MD

Module 22: profile.py
Onboarding and seeker persona operations.
MD

POST /api/v1/profile/create: Onboarding profile setup.
MD

GET /api/v1/profile/me: Returns detailed authenticated profile.
MD

PUT /api/v1/profile/me: Updates profile details.
MD

GET /api/v1/profile/{user_id}: Returns sanitized public seeker profile.
MD

POST /api/v1/profile/voice-spark: Uploads voice intro recording.
MD

DELETE /api/v1/profile/voice-spark: Deletes voice recording.
MD

PATCH /api/v1/profile/slumber-mode: Toggles night slumber silence mode.
MD

POST /api/v1/profile/referral/redeem: Redeems referral invitation code.
MD

Module 23: resonances.py
Mutual matches and incoming likes.
MD

GET /api/v1/resonances/incoming: Lists seekers who liked the user.
MD

GET /api/v1/resonances/mutual: Returns confirmed mutual matches.
MD

Module 24: statutory_pages.py
8 Statutory Legal Portals + 19 Aliases (27 distinct SSR HTML routes). Covered in Section 6 below.
MD

+ 1

Module 25: telemetry.py
Presence tracking and location approximation.
MD

POST /api/v1/telemetry/activity: Ingests lightweight heartbeat pings for online presence tracking.
MD

GET /api/v1/telemetry/resolve-location: Resolves IP-based city approximation.
MD

Module 26: underage_quarantine.py
Hardware device lockout under POCSO Act 2012 / child safety rules.
MD

POST /api/v1/auth/quarantine-device: Hashes device hardware identifiers and creates 180-day quarantine record in underage_quarantine_registry.
MD

GET /api/v1/auth/check-quarantine/{device_fingerprint}: Checks if device is currently quarantined.
MD

Module 27: web_store.py (Condition C2)
Web Sanctuary Store ([https://urheart.app/store](https://urheart.app/store)) and entitlement claiming.
MD

GET /store, GET /store/checkout, GET /store/catalogue: Public web store portal.
MD

POST /api/v1/store/verify-user: Validates target user email before payment.
MD

POST /api/v1/store/create-order: Initializes Razorpay order.
MD

POST /api/v1/store/verify-razorpay-payment: Verifies payment signature and provisions passes or records guest checkout in public.pending_web_entitlements.
MD

POST /api/v1/store/complete-order: Finalizes order status.
MD

GET /api/v1/store/orders/{order_id}: Fetches order status.
MD

POST /api/v1/store/claim-pending: Auto-claims pending entitlements upon mobile app login.
MD

POST /api/v1/store/admin/approve-order: Manual approval for bank transfer orders.
MD

Module 28: ws_ticket.py
WebSocket authentication ticket issuer.
MD

POST /api/v1/chat/ws-ticket

MD

Auth: Depends(get_current_user)

MD

Behavior: Issues single-use 32-byte cryptographic token valid for 60 seconds.
MD

Response: 200 OK -> WsTicketResponse

MD

1. Cloudflare R2 Presigned vs. Supabase Storage Fallback Controller
Implemented in backend/app/services/storage_service.py to preserve the Zero-Card Deployment invariant:
MD

Python

# backend/app/services/storage_service.py

import boto3
from botocore.config import Config
from app.core.config import settings

class StorageAdapter:
    def __init__(self):
        self.r2_enabled = bool(
            settings.CLOUDFLARE_ACCOUNT_ID and
            settings.R2_ACCESS_KEY_ID and
            settings.R2_SECRET_ACCESS_KEY
        )
        if self.r2_enabled:
            self.s3_client = boto3.client(
                "s3",
                endpoint_url=f"https://{settings.CLOUDFLARE_ACCOUNT_ID}.r2.cloudflarestorage.com",
                aws_access_key_id=settings.R2_ACCESS_KEY_ID,
                aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
                config=Config(signature_version="s3v4")
            )
        else:
            self.s3_client = None

    def generate_upload_url(self, user_id: str, slot_number: int) -> dict:
        object_key = f"users/{user_id}/moments/slot_{slot_number}.webp"
        
        # 1. Primary: Cloudflare R2 Presigned S3v4 URL
        if self.r2_enabled and self.s3_client:
            url = self.s3_client.generate_presigned_url(
                ClientMethod="put_object",
                Params={
                    "Bucket": settings.R2_BUCKET_NAME,
                    "Key": object_key,
                    "ContentType": "image/webp",
                },
                ExpiresIn=300
            )
            return {"provider": "cloudflare_r2", "upload_url": url, "object_key": object_key}
        
        # 2. Zero-Card Default: Direct upload route forwarded to Supabase Storage
        return {
            "provider": "supabase_fallback",
            "upload_url": f"/api/v1/media/upload/{user_id}/{slot_number}",
            "object_key": object_key
        }

MD

1. Multi-Engine AI Reasoning Routing
Three specialized AI engines handle distinct tasks, avoiding vendor lock-in and minimizing costs:
MD

Engine Model Router Endpoints Operational Scope
Groq Engine 1 llama-3.3-70b-versatile 
/api/v1/ai/icebreakers

/api/v1/ai/bio-polish

Bio refinement and contextual icebreakers.
MD

Groq Engine 2 llama-3.2-11b-vision-preview 
/api/v1/ai/kyc-liveness

/api/v1/kyc/verify-live

Liveness verification and photo-to-video facial matching.
MD

Gemini Engine gemini-2.5-flash /api/v1/ai/eva/wingman 
Conversational Wingman analyzing active dialogue.
MD

Synthetic Local Dynamic Hindi / Roman NLP /api/v1/ai/eva/chat 
Empathetic dialogue companion (Eva/Arjun).
MD

MD

1. Statutory Pages Multi-Mount Routing (statutory_pages.py)
To ensure crawling compatibility across Google Play Console reviewers, payment aggregators, and court filings, the 8 statutory portals and 19 aliases are mounted across three route patterns:
MD

Root Level: GET /{page} (e.g., [https://urheart.app/privacy](https://urheart.app/privacy))
MD

Statutory Directory: GET /statutory/{page} (e.g., [https://urheart.app/statutory/privacy](https://urheart.app/statutory/privacy))
MD

API Documentation: GET /api/v1/statutory/{page}

MD

Python

# backend/app/main.py (Statutory Mount Configuration)

from app.api.v1.endpoints.statutory_pages import statutory_router

# Multi-mount registration in main application

app.include_router(statutory_router, prefix="", tags=["StatutorySSRRoot"])
app.include_router(statutory_router, prefix="/statutory", tags=["StatutorySSRDirectory"])
app.include_router(statutory_router, prefix="/api/v1/statutory", tags=["StatutorySSRAPIV1"])

MD

1. Verification & Endpoint Testing Suite
FastAPI router integrity is validated through automated test suites:
MD

Bash

# 1. Verify Authentication, JWT, and Age Gate

pytest backend/tests/test_sec01_jwt_verification.py backend/tests/test_auth_signin_loop.py

# 2. Verify Feed Self-Exclusion & Coordinate Fuzzing

pytest backend/tests/test_feed_self_exclusion.py

# 3. Verify Razorpay Payments & Webhook Signatures

pytest backend/tests/test_razorpay_production.py

# 4. Verify 5-Network Ad SSV Waterfall & Anti-Bot Cooldown

pytest backend/tests/test_ads_dynamic_auction_and_antiban.py

# 5. Verify All 27 Statutory SSR Routes (240 Automated Assertions)

pytest backend/tests/test_statutory_pages_complete.py
