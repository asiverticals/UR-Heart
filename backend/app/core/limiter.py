from datetime import datetime, timezone
from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

import ipaddress
from .config import settings

def _is_trusted_proxy(ip_str: str) -> bool:
    if not ip_str:
        return False
    trusted_raw = getattr(settings, "TRUSTED_PROXIES", "127.0.0.1,::1")
    trusted_list = [p.strip() for p in trusted_raw.split(",") if p.strip()]
    if ip_str in trusted_list:
        return True
    try:
        ip = ipaddress.ip_address(ip_str)
        if ip.is_loopback:
            return True
        for t in trusted_list:
            if "/" in t and ip in ipaddress.ip_network(t, strict=False):
                return True
    except ValueError:
        pass
    return False

def get_trusted_client_ip(request: Request) -> str:
    """Extracts true client IP honoring trusted reverse proxy headers only when request originates from a trusted proxy."""
    direct_ip = get_remote_address(request)
    if _is_trusted_proxy(direct_ip):
        candidate = None
        cf_ip = request.headers.get("CF-Connecting-IP")
        if cf_ip:
            candidate = cf_ip.strip()
        else:
            x_forwarded_for = request.headers.get("X-Forwarded-For")
            if x_forwarded_for:
                candidate = x_forwarded_for.split(",")[0].strip()
            else:
                x_real_ip = request.headers.get("X-Real-IP")
                if x_real_ip:
                    candidate = x_real_ip.strip()

        if candidate:
            try:
                ipaddress.ip_address(candidate)
                return candidate
            except ValueError:
                pass
    return direct_ip

limiter = Limiter(
    key_func=get_trusted_client_ip,
    default_limits=["120/minute"],
)

async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Custom SlowAPI rate limit exceeded handler yielding unified Sanctuary error schema."""
    return JSONResponse(
        status_code=429,
        content={
            "success": False,
            "error_code": "RATE_LIMIT_EXCEEDED",
            "message": "Too many requests. Please slow down and embrace serenity.",
            "details": {"retry_after": str(exc.detail)},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
