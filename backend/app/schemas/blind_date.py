from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator

class BlindDateQueueJoin(BaseModel):
    """Payload to enter the 180-second Blind Date speed kinship matchmaking pool."""
    model_config = ConfigDict(extra="forbid")

    preferred_age_min: int = Field(default=18, ge=18, le=99)
    preferred_age_max: int = Field(default=35, ge=18, le=100)
    is_fast_track: bool = Field(default=False)

    @model_validator(mode="after")
    def validate_age_range(self) -> "BlindDateQueueJoin":
        if self.preferred_age_min > self.preferred_age_max:
            raise ValueError("preferred_age_min cannot exceed preferred_age_max")
        return self

class BlindDateSessionResponse(BaseModel):
    """Active ephemeral blind date session metadata and icebreaker prompt."""
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    session_id: UUID
    peer_gender: str
    peer_age: int
    icebreaker_prompt: str
    started_at: datetime
    expires_at: datetime
    extension_count: int
    session_status: str

class BlindDateDecisionRequest(BaseModel):
    """Post-dialogue blind date continuation verdict."""
    model_config = ConfigDict(extra="forbid")

    decision: Literal["resonate", "pass"]
