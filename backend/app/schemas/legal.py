from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field

ViolationCategory = Literal[
    "harassment",
    "explicit_content",
    "impersonation",
    "underage",
    "offplatform_leak",
]

class GrievanceSubmitRequest(BaseModel):
    """Statutory grievance submission under India IT Rules 2021 & DPDP Act 2023."""
    model_config = ConfigDict(extra="forbid")

    reported_user_id: UUID = Field(..., description="Target seeker profile reported")
    violation_category: ViolationCategory = Field(..., description="Category of breach")
    evidence_text: str = Field(default="", max_length=500, description="Contextual report evidence narrative")

class GrievanceResponse(BaseModel):
    """Statutory acknowledgment ticket with IT Rules strict 15-day SLA timeline."""
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    dossier_reference_id: str = Field(..., description="Unique grievance tracking token")
    status: str = Field(..., description="Investigation status: submitted, triaged, resolved")
    acknowledgment_sent_at: str = Field(..., description="24-hour statutory acknowledgment timestamp")
    statutory_resolution_due_at: str = Field(..., description="15-day statutory resolution deadline")

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

