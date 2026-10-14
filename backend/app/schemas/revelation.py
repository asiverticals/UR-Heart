from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

class PhotoRevealRequest(BaseModel):
    """Payload to initiate unmasking of a blurred photo veil."""
    model_config = ConfigDict(extra="forbid")

    target_id: UUID = Field(..., description="Seeker whose photo veil unmasking is requested")

class PhotoRevealUnlockPerkRequest(BaseModel):
    """Payload to redeem micro-perk single profile unlock with optional purchase reference."""
    model_config = ConfigDict(extra="forbid")

    target_id: UUID = Field(..., description="Seeker whose photo veil unmasking is unlocked")
    purchase_reference: Optional[str] = Field(
        None,
        max_length=150,
        description="Verified store order ID, Razorpay payment ID, or sandbox transaction token",
    )

class PhotoRevealRespondRequest(BaseModel):
    """Payload to respond to an incoming photo veil unmasking request."""
    model_config = ConfigDict(extra="forbid")

    requester_id: UUID = Field(..., description="Seeker who initiated the photo reveal request")
    accept: bool = Field(..., description="True to accept and unmask photos, False to decline")

class PhotoRevealResponse(BaseModel):
    """Photo veil unmasking ritual consent status."""
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    target_id: UUID
    status: str = Field(..., description="Consent status: pending, accepted, declined, purchased_unlock, veiled")
    is_revealed: bool = Field(default=False, description="True if photo veil is unmasked")
    message: Optional[str] = Field(None, description="Ritual status explanatory message")

class PhotoRevealStatusResponse(BaseModel):
    """Current photo veil mask status between seekers."""
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    target_id: UUID = Field(..., description="Target seeker profile UUID")
    status: str = Field(..., description="Veil status: veiled, pending, accepted, purchased_unlock")
    is_revealed: bool = Field(..., description="True if photos are unmasked")
