from datetime import date
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

class RegisterIntentRequest(BaseModel):
    """Initial onboarding intent declaring age and hardware anchor under DPDP safety mandate."""
    model_config = ConfigDict(extra="forbid")

    dob: date = Field(..., description="Declared Date of Birth")
    device_fingerprint: str = Field(..., min_length=32, max_length=64, description="SHA-256 hardware hash")


class GoogleSyncRequest(BaseModel):
    """Google OAuth2 RS256 ID Token exchange contract."""
    model_config = ConfigDict(extra="forbid")

    id_token: str = Field(..., min_length=50, description="RS256 Google JWT token")
    installation_uuid: Optional[str] = Field(None, max_length=64, description="Client hardware UUID")

class MagicLinkSendRequest(BaseModel):
    """Passwordless magic link dispatch request."""
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(..., description="Seeker destination email address")

class MagicLinkVerifyRequest(BaseModel):
    """Magic link single-use token verification payload."""
    model_config = ConfigDict(extra="forbid")

    token: str = Field(..., min_length=1, description="Single-use cryptographic magic token")

class TokenResponse(BaseModel):
    """Standard Bearer token bundle issued upon authentic session establishment."""
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    user_id: UUID
    is_profile_completed: bool
