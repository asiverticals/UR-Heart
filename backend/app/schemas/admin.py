from datetime import date, datetime
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class AdminKycEscalationItem(BaseModel):
    """Pending biometric KYC escalation record enriched with presigned review assets."""
    id: str = Field(..., description="Escalation ticket UUID or ID string")
    user_id: str = Field(..., description="Seeker user UUID")
    full_name: str = Field(..., description="Seeker full name")
    declared_dob: Optional[date] = Field(None, description="Seeker declared date of birth")
    declared_age: Optional[int] = Field(None, description="Calculated age in solar years")
    groq_match_score: float = Field(..., description="Groq LPU / Vision confidence score (0.0 to 100.0)")
    anchor_photo_url: str = Field(..., description="Presigned GET URL for verified anchor portrait")
    live_frame_url: str = Field(..., description="Presigned GET URL for ephemeral live capture frame (15m expiry)")
    status: str = Field(default="pending", description="Status of escalation ticket")
    created_at: datetime = Field(..., description="Ticket creation timestamp")


class AdminKycDecisionRequest(BaseModel):
    """Superadmin manual adjudication decision payload."""
    decision: Literal["approve", "reject"] = Field(..., description="Adjudication decision")
    reviewer_notes: Optional[str] = Field(None, max_length=500, description="Optional administrative reasoning")
    user_id: Optional[str] = Field(None, description="Optional target user or escalation UUID for compatibility")


class AdminKycDecisionResponse(BaseModel):
    """Result of manual KYC adjudication decision."""
    success: bool
    user_id: str
    status: str
    message: str
