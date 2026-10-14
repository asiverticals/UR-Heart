from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

class MorningHarvestClaimRequest(BaseModel):
    """Payload to claim morning slumber harvest rewards."""
    model_config = ConfigDict(extra="forbid")

    sleep_duration_hours: float = Field(
        ...,
        ge=0.0,
        le=24.0,
        description="Hours of restful nocturnal sleep detected via accelerometer stillness",
    )
    is_verified: bool = Field(
        default=False,
        description="True if nocturnal stillness was verified via accelerometer hardware sensor; unverified claims are capped at base tier (1.0x) as a deliberate anti-cheat product constraint",
    )

class StreakStatusResponse(BaseModel):
    """Current mindful streak and circadian rhythm status."""
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    streak_count: int = Field(..., description="Active consecutive days of intentional rhythm")
    boost_points: int = Field(..., description="Accumulated mindful boost points")
    streak_expires_at: Optional[datetime] = Field(None, description="Expiration timestamp for active streak")
    is_active: bool = Field(..., description="True if streak has not decayed to 0")
    remaining_seconds: int = Field(..., description="Seconds remaining before streak decays")
    morning_harvest_available: bool = Field(..., description="True if slumber harvest is currently claimable")

class HarvestClaimResponse(BaseModel):
    """Rewards awarded from restful morning harvest."""
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    sleep_duration_hours: float = Field(..., description="Clamped sleep duration in hours")
    multiplier: float = Field(..., description="Nocturnal rest multiplier: 1.0x, 1.5x, or 2.0x")
    swipes_awarded: int = Field(..., description="Intentional discovery swipes credited")
    boost_points_awarded: int = Field(..., description="Boost points credited")
    direct_letters_awarded: int = Field(..., description="Direct letters credited")
    new_streak_count: int = Field(..., description="Updated streak count after harvest")
    new_boost_points: int = Field(..., description="Updated boost points balance")
    new_swipes_remaining: int = Field(..., description="Updated swipes remaining balance")
    new_direct_letters_count: int = Field(..., description="Updated direct letters balance")
    message: str = Field(..., description="Celebratory blessing message")
