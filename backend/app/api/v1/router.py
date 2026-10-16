from fastapi import APIRouter
from .endpoints import (
    admin_kyc,
    ads,
    ai,
    auth,
    blind_date,
    blocking,
    chat_closure,
    chat_ws,
    eva,
    feed,
    health,
    incineration,
    kyc,
    legal,
    media,
    notifications,
    payments,
    profile,
    resonances,
    revelation,
    store,
    streak,
)

api_router = APIRouter()

# 1. Health & Sleepless Sentinel
api_router.include_router(health.router, tags=["HealthSentinel"])

# 2. Authentication & Identity
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# 3. AI Sanctuary, Wingman & Voice Transcriptions
api_router.include_router(ai.router, prefix="/ai", tags=["AISanctuary"])

# 4. Eva AI Profile Reflection Engine
api_router.include_router(eva.router, prefix="/eva", tags=["EvaAI"])

# 5. Media Storage (Supabase & Cloudflare R2)
api_router.include_router(media.router, prefix="/media", tags=["MediaStorage"])

# 6. Biometric KYC Verification
api_router.include_router(kyc.router, prefix="/kyc", tags=["KYCVerification"])

# 7. Superadmin KYC Escalation Desk
api_router.include_router(admin_kyc.router, prefix="/admin/kyc", tags=["AdminKYC"])

# 8. Discovery Feed & Swipe Interactions
api_router.include_router(feed.router, prefix="/feed", tags=["DiscoveryFeed"])

# 9. Revelation & Photo Veil Handshake
api_router.include_router(revelation.router, prefix="/revelation", tags=["Revelation"])

# 10. Mindful Streak & Slumber Harvest
api_router.include_router(streak.router, prefix="/streak", tags=["MindfulStreak"])

# 11. Real-time Dialogue & WebSocket Relay & Mindful Closure
api_router.include_router(chat_ws.router, prefix="/chat", tags=["Chat"])
api_router.include_router(chat_closure.router, prefix="/chat", tags=["Chat"])

# 12. Background Push Notifications (FCM HTTP v1)
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])

# 13. Sovereign Store & Monetization Catalog (Condition C2)
api_router.include_router(store.router, prefix="/store", tags=["Store"])

# 14. Payment Gateways & Webhook Ingestion (Razorpay, Stripe, RevenueCat)
api_router.include_router(payments.router, prefix="/payments", tags=["Payments"])

# 15. 5-Network Ad SSV Waterfall & Anti-Bot Cooling
api_router.include_router(ads.router, prefix="/ads", tags=["RewardedAds"])

# 16. DPDP Act 2023 Legal Vault & Statutory Grievance Dossier
api_router.include_router(legal.router, prefix="/legal", tags=["LegalVault"])
api_router.include_router(legal.router, prefix="/vault", tags=["LegalVault"])
api_router.include_router(incineration.router, prefix="/legal", tags=["AccountIncineration"])
api_router.include_router(incineration.router, prefix="/vault", tags=["AccountIncineration"])

# 17. Seeker Profile Lifecycle & Onboarding
api_router.include_router(profile.router, prefix="/profile", tags=["Profile"])

# 18. Resonances & Bilateral Matches
api_router.include_router(resonances.router, prefix="/resonances", tags=["Resonances"])

# 19. Blind Date Speed Dating (Condition C1 Gated)
api_router.include_router(blind_date.router, prefix="/blind-date", tags=["BlindDate"])

# 20. User Blocking & Safety Interventions (Apple Guideline 1.2 & Google Play UGC)
api_router.include_router(blocking.router, prefix="/users", tags=["Blocking"])
