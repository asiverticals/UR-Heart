from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from datetime import datetime, timezone
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .api.v1.endpoints import health, chat_ws
from .api.v1.router import api_router
from .core.config import settings, validate_production_secrets
from .core.exceptions import SanctuaryException, sanctuary_exception_handler
from .core.limiter import limiter, rate_limit_exceeded_handler

from fastapi.encoders import jsonable_encoder

async def request_validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    encoded_errors = jsonable_encoder(exc.errors())
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error_code": "VALIDATION_ERROR",
            "message": "Request validation failed.",
            "detail": encoded_errors,
            "details": {"errors": encoded_errors},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else "HTTP error encountered"
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_code": f"HTTP_{exc.status_code}",
            "message": detail,
            "detail": exc.detail,
            "details": exc.detail if isinstance(exc.detail, dict) else {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        headers=getattr(exc, "headers", None),
    )

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager validating production invariants on boot."""
    validate_production_secrets()
    if settings.SENTRY_DSN:
        try:
            import sentry_sdk
            sentry_sdk.init(
                dsn=settings.SENTRY_DSN,
                environment=settings.ENVIRONMENT,
                traces_sample_rate=0.1,
                send_default_pii=False,
            )
            logging.getLogger("urheart.main").info("Sentry monitoring initialized successfully")
        except Exception as exc:
            logging.getLogger("urheart.main").warning("Sentry init failed: %s", exc)
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
app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, starlette_http_exception_handler)



# CORS Policy
cors_origins = [
    "https://urheart.app",
    "https://media.urheart.app",
]
if settings.ENVIRONMENT != "production":
    cors_origins.extend(["http://localhost:3000", "http://localhost:8080"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"^https://([a-zA-Z0-9-]+\.)*urheart\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# HTTP Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
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
# Mount WebSocket relay directly at root (/ws/chat)
app.include_router(chat_ws.ws_router)

