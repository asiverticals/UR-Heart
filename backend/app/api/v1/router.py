from fastapi import APIRouter
from .endpoints import health

api_router = APIRouter()

# 1. Health & Sleepless Sentinel
api_router.include_router(health.router, tags=["HealthSentinel"])
