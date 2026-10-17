import logging
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

import hmac
from .api.v1.endpoints import health, chat_ws
from .api.v1.router import api_router
from .api.web_pages import web_router
from .api.admin_portal import (
    router as admin_router,
    SESSION_COOKIE_NAME,
    verify_admin_session_token,
    SUPERADMIN_EMAIL_CANONICAL,
)
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

logger = logging.getLogger("urheart.main")

class UvicornAccessNoiseFilter(logging.Filter):
    """
    Suppresses noisy automated scanner probes (404s for wp-*, .env, etc.)
    and repetitive UptimeRobot keep-alive health pings from flooding Render logs.
    """
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        # Suppress repetitive UptimeRobot HEAD / 200 keep-alive pings
        if '"HEAD / HTTP/' in msg and ' 200 ' in msg:
            return False
        # Suppress repetitive scanner 404 probe noise
        if any(probe in msg for probe in (
            "/wp-", "/wordpress", "/blog", "/cms", "/site", "/news", "/press",
            "/.env", "/.git", "/xmlrpc", "/favicon.ico", "rest_route="
        )) and (' 404 ' in msg or ' 204 ' in msg):
            return False
        return True

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager validating production invariants on boot."""
    validate_production_secrets()

    # Clean up uvicorn.access logger so Render logs stay noise-free
    access_logger = logging.getLogger("uvicorn.access")
    access_logger.addFilter(UvicornAccessNoiseFilter())

    if settings.SENTRY_DSN:
        try:
            import sentry_sdk
            sentry_sdk.init(
                dsn=settings.SENTRY_DSN,
                environment=settings.ENVIRONMENT,
                traces_sample_rate=0.1,
                send_default_pii=False,
            )
            logger.info("Sentry monitoring initialized successfully")
        except Exception as exc:
            logger.warning("Sentry init failed: %s", exc)
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

# Known malicious scanner probe path prefixes and exact paths
SCANNER_PROBE_PREFIXES = (
    "/wp-", "/wordpress", "/xmlrpc.php", "/.env", "/.git", "/.aws",
    "/phpmyadmin", "/pma", "/eval-stdin", "/actuator", "/vendor",
    "/blog/", "/wp/", "/site/", "/news/", "/cms/", "/press/",
)

# Automated Scanner Probe Shield Middleware
@app.middleware("http")
async def scanner_probe_shield_middleware(request: Request, call_next):
    raw_path = request.url.path.lower()
    
    # Reject known CMS and exploit probe paths immediately with clean 404 and long cache
    if any(raw_path.startswith(prefix) for prefix in SCANNER_PROBE_PREFIXES) or raw_path.endswith((".php", ".asp", ".aspx")):
        return Response(
            status_code=404,
            content=b"Not Found",
            headers={"Cache-Control": "public, max-age=86400", "X-Sanctuary-Shield": "blocked"},
        )
        
    return await call_next(request)

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
    # If scanner probes WordPress REST route (e.g. /?rest_route=/), reject with 404
    if "rest_route" in request.query_params:
        return Response(
            status_code=404,
            content=b"Not Found",
            headers={"Cache-Control": "public, max-age=86400"},
        )

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

# Static Well-Known Web Endpoints (/robots.txt, /sitemap.xml, /favicon.ico)
@app.get("/robots.txt", status_code=200)
@limiter.exempt
async def robots_txt() -> Response:
    content = "User-agent: *\nDisallow: /admin/\nDisallow: /api/\nAllow: /\nSitemap: https://urheart.app/sitemap.xml\n"
    return Response(
        content=content,
        media_type="text/plain",
        headers={"Cache-Control": "public, max-age=86400"},
    )

@app.get("/sitemap.xml", status_code=200)
@limiter.exempt
async def sitemap_xml() -> Response:
    content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://urheart.app/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>
  <url><loc>https://urheart.app/store</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>
  <url><loc>https://urheart.app/emergency-takedown</loc><changefreq>monthly</changefreq><priority>0.5</priority></url>
  <url><loc>https://urheart.app/grievance</loc><changefreq>monthly</changefreq><priority>0.5</priority></url>
  <url><loc>https://urheart.app/refund</loc><changefreq>monthly</changefreq><priority>0.5</priority></url>
  <url><loc>https://urheart.app/delete-account</loc><changefreq>monthly</changefreq><priority>0.5</priority></url>
  <url><loc>https://urheart.app/contact</loc><changefreq>monthly</changefreq><priority>0.5</priority></url>
</urlset>"""
    return Response(
        content=content,
        media_type="application/xml",
        headers={"Cache-Control": "public, max-age=86400"},
    )

@app.get("/favicon.ico", status_code=204)
@limiter.exempt
async def favicon_ico() -> Response:
    return Response(
        status_code=204,
        headers={"Cache-Control": "public, max-age=604800"},
    )

# Mount Health router directly at root (/health) and under /api/v1
app.include_router(health.router)
app.include_router(api_router, prefix="/api/v1")
# Mount WebSocket relay directly at root (/ws/chat)
app.include_router(chat_ws.ws_router)
# Mount Production Web Portals directly at root (/store, /emergency-takedown, /grievance, /refund, /delete-account, /contact)
app.include_router(web_router)
# Mount Production Web Admin Portal directly at root (/admin, /admin/login, /admin/api/*)
app.include_router(admin_router)

# Superadmin Gatekeeper Middleware for /admin routes
@app.middleware("http")
async def admin_gatekeeper_middleware(request: Request, call_next):
    path = request.url.path
    if path == "/admin" or path.startswith("/admin/"):
        # Explicitly allow public authentication entry points
        if path in ("/admin/login", "/admin/api/login"):
            return await call_next(request)

        # 1. Check session cookie
        cookie_token = request.cookies.get(SESSION_COOKIE_NAME)
        admin_email = verify_admin_session_token(cookie_token) if cookie_token else None

        # 2. Check Bearer token
        if not admin_email:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                admin_email = verify_admin_session_token(auth_header[7:].strip())

        # 3. Check X-Superadmin-Key header
        if not admin_email:
            admin_key = request.headers.get("X-Superadmin-Key", "").strip()
            expected_secret = (settings.SUPERADMIN_SECRET_KEY or "").strip()
            if admin_key and expected_secret and hmac.compare_digest(admin_key, expected_secret):
                admin_email = SUPERADMIN_EMAIL_CANONICAL

        if not admin_email:
            # If API request under /admin/api/*, return HTTP 401
            if path.startswith("/admin/api/"):
                return JSONResponse(
                    status_code=401,
                    content={
                        "success": False,
                        "error_code": "ADMIN_UNAUTHORIZED",
                        "message": "Admin authentication required.",
                        "detail": "Admin authentication required.",
                    },
                )
            # If web portal request under /admin or /admin/*, redirect to /admin/login
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url="/admin/login", status_code=303)

    return await call_next(request)


