from datetime import datetime, timezone
from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")

class SanctuaryResponse(BaseModel, Generic[T]):
    """Unified success envelope for UR-Heart Sanctuary API endpoints."""
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    success: bool = Field(default=True, description="Indicates operation success")
    data: Optional[T] = Field(default=None, description="Typed payload")
    message: Optional[str] = Field(default=None, description="Human readable contextual message")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="ISO 8601 UTC timestamp",
    )

class SanctuaryErrorResponse(BaseModel):
    """Unified structured error envelope preventing sensitive stack trace leaks."""
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    success: bool = Field(default=False, description="Always false for error states")
    error_code: str = Field(..., description="Machine-readable error identifier")
    message: str = Field(..., description="Human-readable safe explanation")
    details: Optional[dict[str, Any]] = Field(default=None, description="Optional safe structured context")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="ISO 8601 UTC timestamp",
    )
