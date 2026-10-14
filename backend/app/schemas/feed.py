from typing import List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from .profile import ProfilePublicResponse

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

class DiscoveryFeedResponse(BaseModel):
    """Discovery deck feed payload with fuzzed profile cards and quota balance."""
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    profiles: List[ProfilePublicResponse] = Field(..., description="Candidate seeker profiles matching self-exclusion perimeter")
    swipes_remaining: int = Field(..., description="Current available swipe quota")

class SwipesRemainingResponse(BaseModel):
    """Daily swipe quota, active mindful streak, and refresh countdown."""
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    swipes_remaining: int = Field(..., description="Available swipes remaining today")
    streak_count: int = Field(..., description="Active mindfulness day streak")
    seconds_until_refresh: int = Field(..., description="Seconds remaining until daily midnight reset")

class PhotoRevealRequest(BaseModel):
    """Request to initiate unmasking of a blurred photo veil."""
    model_config = ConfigDict(extra="forbid")

    target_id: UUID = Field(..., description="Seeker whose photo veil unmasking is requested")

class PhotoRevealResponse(BaseModel):
    """Photo veil unmasking ritual consent status."""
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    target_id: UUID
    status: Literal["pending", "accepted", "declined"]
