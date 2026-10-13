from datetime import datetime, timezone
from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
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
