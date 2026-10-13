from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from .api.v1.endpoints import health
from .api.v1.router import api_router
from .core.config import settings, validate_production_secrets
from .core.exceptions import SanctuaryException, sanctuary_exception_handler
from .core.limiter import limiter, rate_limit_exceeded_handler

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager validating production invariants on boot."""
    validate_production_secrets()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
)

# SlowAPI Rate Limiter setup
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Custom Unified Exception Handlers
app.add_exception_handler(SanctuaryException, sanctuary_exception_handler)

from fastapi.exceptions import RequestValidationError
from datetime import date, datetime, timedelta, timezone
from .models.domain.legal import UnderageQuarantineRegistry

@app.exception_handler(RequestValidationError)
async def custom_validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    if request.url.path.endswith("/auth/register-intent"):
        for err in exc.errors():
            msg = str(err.get("msg", ""))
            if "under 18 years of age" in msg.lower():
                age_val = None
                try:
                    body = await request.json()
                    fp = body.get("device_fingerprint")
                    dob_str = body.get("dob")
                    if fp and dob_str:
                        dob_val = date.fromisoformat(dob_str)
                        today = date.today()
                        age_val = today.year - dob_val.year - ((today.month, today.day) < (dob_val.month, dob_val.day))
                        from .core.database import get_db, AsyncSessionLocal
                        from .services.auth_service import auth_service
                        if get_db in app.dependency_overrides:
                            gen = app.dependency_overrides[get_db]()
                            async for session in gen:
                                await auth_service.record_underage_quarantine(fp, dob_val, age_val, session)
                                break
                        else:
                            async with AsyncSessionLocal() as session:
                                await auth_service.record_underage_quarantine(fp, dob_val, age_val, session)
                except Exception as err:
                    import logging
                    logging.getLogger(__name__).error("Failed to record quarantine write in validation handler: %s", err)

                return JSONResponse(
                    status_code=403,
                    content={
                        "success": False,
                        "error_code": "UNDERAGE_QUARANTINE_TRIGGERED",
                        "message": "Seeker is under the legal age threshold.",
                        "details": {"age": age_val},
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
    from fastapi.exception_handlers import request_validation_exception_handler
    return await request_validation_exception_handler(request, exc)


# CORS Policy
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://urheart.app",
        "https://media.urheart.app",
        "http://localhost:3000",
        "http://localhost:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# HTTP Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(self), microphone=(self)"
    return response

# Root Keep-Alive Sentinel for UptimeRobot
@app.api_route("/", methods=["GET", "HEAD"], status_code=200)
@limiter.exempt
async def root_sentinel(request: Request) -> Response:
    headers = {
        "X-Sanctuary-Alive": "true",
        "Cache-Control": "no-cache, no-store, must-revalidate",
    }
    if request.method == "HEAD":
        return Response(status_code=200, content=b"", headers=headers)
    return JSONResponse(
        status_code=200,
        content={"sanctuary": "active", "message": "UR-Heart Sanctuary Online"},
        headers=headers,
    )

# Mount Health router directly at root (/health) and under /api/v1
app.include_router(health.router)
app.include_router(api_router, prefix="/api/v1")
