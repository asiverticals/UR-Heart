from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

SwipeAction = Literal["like", "pass", "superlike"]

class SwipeRequest(BaseModel):
    """Discovery deck swipe interaction payload."""
    model_config = ConfigDict(extra="forbid")

    target_id: UUID = Field(..., description="Target seeker profile UUID")
    action: SwipeAction = Field(..., description="Intent action: like, pass, or superlike")
    direct_letter_text: Optional[str] = Field(None, max_length=280, description="Encrypted letter note if applicable")

class SwipeResponse(BaseModel):
    """Result of swipe evaluation including mutual resonance status."""
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    is_match: bool = Field(..., description="True if a bilateral mutual match was ignited")
    match_id: Optional[UUID] = Field(None, description="Ignited match UUID if mutual like occurred")
    swipes_remaining: int = Field(..., description="Remaining daily quota balance")

class PhotoRevealRequest(BaseModel):
    """Request to initiate unmasking of a blurred photo veil."""
    model_config = ConfigDict(extra="forbid")

    target_id: UUID = Field(..., description="Seeker whose photo veil unmasking is requested")

class PhotoRevealResponse(BaseModel):
    """Photo veil unmasking ritual consent status."""
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    target_id: UUID
    status: Literal["pending", "accepted", "declined"]
