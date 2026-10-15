from fastapi import APIRouter
from .endpoints import auth, chat_closure, chat_ws, feed, health, kyc, media, notifications, payments, revelation, store, streak

api_router = APIRouter()

# 1. Health & Sleepless Sentinel
api_router.include_router(health.router, tags=["HealthSentinel"])

# 2. Authentication & Identity
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# 3. Cloudflare R2 Media Storage
api_router.include_router(media.router, prefix="/media", tags=["MediaStorage"])

# 4. Biometric KYC Verification
api_router.include_router(kyc.router, prefix="/kyc", tags=["KYCVerification"])

# 5. Discovery Feed & Swipe Interactions
api_router.include_router(feed.router, prefix="/feed", tags=["DiscoveryFeed"])

# 6. Revelation & Photo Veil Handshake
api_router.include_router(revelation.router, prefix="/revelation", tags=["Revelation"])

# 7. Mindful Streak & Slumber Harvest
api_router.include_router(streak.router, prefix="/streak", tags=["MindfulStreak"])

# 8. Real-time Dialogue & WebSocket Relay & Mindful Closure
api_router.include_router(chat_ws.router, prefix="/chat", tags=["Chat"])
api_router.include_router(chat_closure.router, prefix="/chat", tags=["Chat"])

# 9. Background Push Notifications (FCM HTTP v1)
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])

# 10. Sovereign Store & Monetization Catalog (Condition C2)
api_router.include_router(store.router, prefix="/store", tags=["Store"])

# 11. Razorpay Payment Gateway & Webhook Ingestion
api_router.include_router(payments.router, prefix="/payments", tags=["Payments"])



