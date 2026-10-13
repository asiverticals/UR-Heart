from datetime import datetime, timezone
from typing import Any, Dict, Optional
from fastapi import Request
from fastapi.responses import JSONResponse

class SanctuaryException(Exception):
    """Base domain exception for UR-Heart Sanctuary yielding the unified error schema."""
    def __init__(
        self,
        error_code: str,
        message: str,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

async def sanctuary_exception_handler(request: Request, exc: SanctuaryException) -> JSONResponse:
    """FastAPI exception handler for SanctuaryException routing unified error responses."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
