from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

ViolationCategory = Literal[
    "harassment",
    "explicit_content",
    "impersonation",
    "underage",
    "offplatform_leak",
    "ncii",
]

class GrievanceSubmitRequest(BaseModel):
    """Statutory grievance submission under India IT Rules 2021 & DPDP Act 2023."""
    model_config = ConfigDict(extra="forbid")

    reported_user_id: UUID = Field(..., description="Target seeker profile reported")
    violation_category: ViolationCategory = Field(..., description="Category of breach")
    evidence_text: str = Field(default="", max_length=500, description="Contextual report evidence narrative")

class EmergencyTakedownRequest(BaseModel):
    """Public emergency 24-hour takedown request under IT Rules 2021 Rule 3(2)(b) for NCII/explicit violations."""
    model_config = ConfigDict(extra="forbid")

    complainant_name: str = Field(..., min_length=2, max_length=100, description="Full name of reporting individual or legal counsel")
    complainant_email: EmailStr = Field(..., description="Official notification email for statutory updates")
    complainant_phone: Optional[str] = Field(None, max_length=20, description="Contact phone for urgent verification")
    reported_user_id: Optional[UUID] = Field(None, description="Reported seeker UUID if known")
    reported_handle_or_name: Optional[str] = Field(None, max_length=100, description="Profile name or handle if UUID unknown")
    violation_category: Literal["ncii", "explicit_content", "impersonation", "underage"] = Field(
        "ncii", description="Emergency violation category subject to 24-hour statutory takedown SLA"
    )
    evidence_text: str = Field(..., min_length=10, max_length=1000, description="Detailed statement explaining violation")
    evidence_media_url: Optional[str] = Field(None, max_length=500, description="Link to offending media location or CDN asset")
    good_faith_affirmation: bool = Field(..., description="Affirmation that statements are true under penalty of law")

class EmergencyTakedownResponse(BaseModel):
    """Statutory emergency takedown acknowledgment under IT Rules 2021 Rule 3(2)(b)."""
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    dossier_reference_id: str
    status: str
    statutory_sla_hours: int = 24
    emergency_takedown_due_at: str
    message: str

class GrievanceResponse(BaseModel):
    """Statutory acknowledgment ticket with IT Rules strict SLA timeline."""
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    dossier_reference_id: str = Field(..., description="Unique grievance tracking token")
    status: str = Field(..., description="Investigation status: submitted, triaged, resolved")
    acknowledgment_sent_at: str = Field(..., description="24-hour statutory acknowledgment timestamp")
    statutory_resolution_due_at: str = Field(..., description="15-day statutory resolution deadline")
    emergency_takedown_due_at: Optional[str] = Field(None, description="24-hour emergency removal SLA for explicit/NCII content")

class DataNomineeRequest(BaseModel):
    """Digital nominee designation under DPDP Act 2023 Section 14."""
    model_config = ConfigDict(extra="forbid")

    nominee_name: str = Field(..., min_length=2, max_length=60, description="Full name of designated digital nominee")
    nominee_contact: str = Field(..., min_length=5, max_length=30, description="Phone number or verified email")
    relationship: str = Field(..., min_length=2, max_length=30, description="Kinship relationship to seeker")

class NomineeResponse(BaseModel):
    """Digital nominee state under DPDP Act 2023 Section 14."""
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    nominee_name: str = Field(..., description="Full name of designated digital nominee")
    nominee_contact: str = Field(..., description="Phone number or email")
    relationship: str = Field(..., description="Kinship relationship to seeker")
    assigned_at: Optional[str] = Field(None, description="ISO timestamp of designation")
    verification_status: str = Field(default="designated", description="Nominee state")

class GrievanceDossierItem(BaseModel):
    """Itemized grievance dossier in seeker's legal vault."""
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    dossier_reference_id: str
    violation_category: str
    evidence_text: str
    status: str
    acknowledgment_sent_at: str
    statutory_resolution_due_at: str
    emergency_takedown_due_at: Optional[str] = None
    created_at: str

class DataExportResponse(BaseModel):
    """DPDP Act Section 11 machine-readable data portability payload."""
    model_config = ConfigDict(extra="forbid")

    export_data: dict = Field(..., description="Sanitized seeker data archive")
    generated_at: str = Field(..., description="Archive compilation timestamp")

class WebAccountDeletionRequest(BaseModel):
    """Public web endpoint account incineration request under DPDP Section 12."""
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(..., description="Seeker registered account email")
    reason: Optional[str] = Field(None, max_length=500, description="Voluntary departure feedback")

class AccountIncinerateRequest(BaseModel):
    """Authenticated account incineration request under DPDP Section 12."""
    confirmation_phrase: Literal["PERMANENTLY INCINERATE"]
    reason: Optional[str] = Field(None, max_length=500, description="Voluntary departure feedback")
    model_config = ConfigDict(extra="forbid")

class MagicLinkVerifyRequest(BaseModel):
    """Web deletion confirmation request carrying statutory magic link token."""
    token: str = Field(..., min_length=1, max_length=128, description="Cryptographic web deletion token")
    model_config = ConfigDict(extra="forbid")

class ConsentRecordRequest(BaseModel):
    """Statutory consent record submission under DPDP Act 2023 Section 6."""
    model_config = ConfigDict(extra="forbid")

    consent_purpose_id: str = Field(..., min_length=1, max_length=64, description="Statutory purpose limitation identifier")
    installation_uuid: Optional[str] = Field(None, max_length=64, description="Client hardware/installation identifier")

    @field_validator("consent_purpose_id")
    @classmethod
    def validate_purpose_id(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("consent_purpose_id must not be empty or whitespace")
        return stripped


