from fastapi import APIRouter
from .endpoints import auth, feed, health, kyc, media, revelation

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

