from fastapi import APIRouter
from .endpoints import auth, health, media

api_router = APIRouter()

# 1. Health & Sleepless Sentinel
api_router.include_router(health.router, tags=["HealthSentinel"])

# 2. Authentication & Identity
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# 3. Cloudflare R2 Media Storage
api_router.include_router(media.router, prefix="/media", tags=["MediaStorage"])

