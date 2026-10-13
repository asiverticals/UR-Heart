from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
try:
    from ....core.limiter import limiter
except (ImportError, ValueError):
    from backend.app.core.limiter import limiter

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
