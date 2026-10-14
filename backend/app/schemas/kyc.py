from typing import Optional
from pydantic import BaseModel, Field

class KycPresignedUploadResponse(BaseModel):
    upload_url: str = Field(..., description="S3v4 presigned PUT URL for temporary live frame")
    object_key: str = Field(..., description="Temporary R2 object key")
    expires_in: int = Field(default=120, description="Expiration time in seconds")

class KycVerifyRequest(BaseModel):
    object_key: str = Field(..., description="Temporary object key under kyc_temp/")

class KycVerifyResponse(BaseModel):
    success: bool
    status: str = Field(..., description="approved | escalated | rejected")
    score: int = Field(..., ge=0, le=100)
    message: str
    reasoning: Optional[str] = None

class KycStatusResponse(BaseModel):
    kyc_status: bool
    has_pending_escalation: bool
