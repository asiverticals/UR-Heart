from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
try:
    from ....core.config import settings
    from ....core.limiter import limiter
    from ..deps import get_superadmin
except (ImportError, ValueError):
    from backend.app.core.config import settings
    from backend.app.core.limiter import limiter
    from backend.app.api.deps import get_superadmin

router = APIRouter()

HEALTH_HEADERS = {
    "X-Sanctuary-Alive": "true",
    "Cache-Control": "no-cache, no-store, must-revalidate",
}

@router.api_route("/health", methods=["GET", "HEAD"], status_code=200)
@limiter.exempt
async def health_sentinel(request: Request) -> Response:
    """Sleepless Keep-Alive Sentinel endpoint for UptimeRobot monitoring.

    Returns HTTP 200 with header X-Sanctuary-Alive: true.
    HEAD returns a 0-byte body to minimize bandwidth on 5-minute pings.
    GET returns status payload with 0ms database overhead.
    """
    if request.method == "HEAD":
        return Response(status_code=200, content=b"", headers=HEALTH_HEADERS)

    return JSONResponse(
        status_code=200,
        content={
            "status": "alive",
            "sanctuary": "active",
            "db_overhead_ms": 0,
        },
        headers=HEALTH_HEADERS,
    )

@router.get("/sentinel", status_code=200)
async def superadmin_sentinel_diagnostics(
    authorized: bool = Depends(get_superadmin),
) -> JSONResponse:
    """Superadmin Sentinel Gate: Diagnostic summary of all connected services."""
    return JSONResponse(
        status_code=200,
        content={
            "app_name": settings.PROJECT_NAME,
            "environment": settings.ENVIRONMENT,
            "debug": settings.DEBUG,
            "services": {
                "supabase": bool(settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY),
                "groq_lpu": bool(settings.GROQ_API_KEY and not settings.GROQ_API_KEY.startswith("placeholder_")),
                "groq_whisper": bool(
                    (settings.GROQ_VOICE_API_KEY and not settings.GROQ_VOICE_API_KEY.startswith("placeholder_"))
                    or (settings.GROQ_API_KEY and not settings.GROQ_API_KEY.startswith("placeholder_"))
                ),
                "openrouter": bool(settings.OPENROUTER_API_KEY and not settings.OPENROUTER_API_KEY.startswith("placeholder_")),
                "gemini": bool(settings.GEMINI_API_KEY and not settings.GEMINI_API_KEY.startswith("placeholder_")),
                "firebase": bool(settings.FIREBASE_PROJECT_ID),
                "resend": bool(settings.RESEND_API_KEY and not settings.RESEND_API_KEY.startswith("placeholder_")),
                "smtp": bool(settings.SMTP_USER and not settings.SMTP_USER.startswith("placeholder_")),
                "brevo": bool(settings.BREVO_API_KEY and not settings.BREVO_API_KEY.startswith("placeholder_")),
                "razorpay": bool(settings.RAZORPAY_KEY_ID),
                "stripe": bool(settings.STRIPE_WEBHOOK_SECRET),
                "revenuecat": bool(settings.REVENUECAT_WEBHOOK_SECRET),
                "sentry": bool(settings.SENTRY_DSN),
            },
        },
    )

