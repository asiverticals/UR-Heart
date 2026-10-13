from typing import Literal, Optional
from pydantic import BaseModel, Field, model_validator

VALID_IMAGE_MIMES = {"image/webp"}
VALID_AUDIO_MIMES = {"audio/m4a", "audio/mp4", "audio/aac"}

MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_VOICE_BYTES = 10 * 1024 * 1024  # 10 MB

class PresignedUploadRequest(BaseModel):
    """Payload schema requesting an S3v4 presigned upload URL."""
    asset_type: Literal["moment", "avatar", "voice_spark"]
    slot_number: Optional[int] = Field(None, ge=1, le=5, description="Slot index (1-5) mandatory for moments")
    content_type: str = Field(default="image/webp", description="MIME type for binary payload")
    file_size_bytes: int = Field(..., ge=1024, description="Declared payload size in bytes")

    @model_validator(mode="after")
    def validate_asset_parameters(self) -> "PresignedUploadRequest":
        if self.asset_type == "moment":
            if self.slot_number is None:
                raise ValueError("slot_number is mandatory for moment assets and must be between 1 and 5.")
            if self.content_type not in VALID_IMAGE_MIMES:
                raise ValueError(f"Moments must use WebP encoding: {VALID_IMAGE_MIMES}")
            if self.file_size_bytes > MAX_IMAGE_BYTES:
                raise ValueError(f"Moment payload exceeds maximum limit of {MAX_IMAGE_BYTES} bytes (5 MB).")

        elif self.asset_type == "avatar":
            if self.content_type not in VALID_IMAGE_MIMES:
                raise ValueError(f"Avatar images must use WebP encoding: {VALID_IMAGE_MIMES}")
            if self.file_size_bytes > MAX_IMAGE_BYTES:
                raise ValueError(f"Avatar payload exceeds maximum limit of {MAX_IMAGE_BYTES} bytes (5 MB).")

        elif self.asset_type == "voice_spark":
            if self.content_type not in VALID_AUDIO_MIMES:
                raise ValueError(f"Voice Sparks must use AAC/M4A audio encoding: {VALID_AUDIO_MIMES}")
            if self.file_size_bytes > MAX_VOICE_BYTES:
                raise ValueError(f"Voice Spark audio exceeds maximum limit of {MAX_VOICE_BYTES} bytes (10 MB).")

        return self

class PresignedUploadResponse(BaseModel):
    """Response containing presigned S3v4 direct upload coordinates and public CDN reference."""
    success: bool = True
    upload_url: str
    public_cdn_url: str
    object_key: str
    expires_in: int = 300
    max_bytes: int = MAX_IMAGE_BYTES

class MomentDeleteResponse(BaseModel):
    """Response returned upon deleting a moment asset."""
    success: bool = True
    slot_number: int
    deleted: bool = True
