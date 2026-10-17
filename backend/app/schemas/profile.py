from datetime import date
from decimal import Decimal
from typing import Any, List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

GenderType = Literal["Woman", "Man", "Non-Binary", "Other"]
InterestedInType = Literal["Men", "Women", "Everyone"]
ContactBridgeType = Literal["whatsapp", "instagram", "snapchat", "telegram", "signal"]

class ProfileCreate(BaseModel):
    """Initial seeker profile onboarding schema with statutory 18+ gate and coordinate fuzzing."""
    model_config = ConfigDict(extra="ignore")

    full_name: str = Field(..., min_length=2, max_length=60)
    dob: date
    gender: GenderType
    interested_in: InterestedInType
    contact_bridge_type: ContactBridgeType = "whatsapp"
    contact_bridge_raw: Optional[str] = Field(None, min_length=3, max_length=64, description="Raw bridge handle to be AES-256 encrypted")
    contact_bridge_handle: Optional[str] = Field(None, min_length=3, max_length=64, description="Contact bridge handle from client")

    @model_validator(mode="before")
    @classmethod
    def populate_bridge_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            handle = data.get("contact_bridge_handle")
            raw_field = data.get("contact_bridge_raw")
            selected = None
            if isinstance(handle, str) and len(handle.strip()) >= 3:
                selected = handle.strip()
            elif isinstance(raw_field, str) and len(raw_field.strip()) >= 3:
                selected = raw_field.strip()
            if not selected:
                raise ValueError("Either contact_bridge_handle or contact_bridge_raw must be provided with at least 3 characters")
            data["contact_bridge_raw"] = selected
            data["contact_bridge_handle"] = selected
        return data
    bio: str = Field(default="", max_length=500)
    profession: str = Field(default="", max_length=80)
    education: str = Field(default="", max_length=100)
    photos: List[str] = Field(..., min_length=1, max_length=5, description="Array of Cloudflare R2 / CDN media URLs")
    avatar_url: Optional[str] = Field(None, max_length=500)
    latitude: Optional[Decimal] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[Decimal] = Field(None, ge=-180.0, le=180.0)
    voice_spark_url: Optional[str] = Field(None, max_length=500)
    voice_spark_duration: Optional[float] = Field(None, ge=0.0, le=60.0)

    @field_validator("dob")
    @classmethod
    def validate_adult_age(cls, v: date) -> date:
        today = date.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age < 18:
            raise ValueError("Seeker must be at least 18 years of age to enter the sanctuary")
        return v

    @field_validator("latitude", "longitude")
    @classmethod
    def fuzz_coordinates(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None:
            return round(v, 2)  # Fuzz to ~1.1km neighborhood grid to protect exact location
        return None

class ProfileUpdate(BaseModel):
    """Partial profile update schema with permissive extra-field handling and strict validation."""
    model_config = ConfigDict(extra="ignore")

    full_name: Optional[str] = Field(None, min_length=2, max_length=60)
    bio: Optional[str] = Field(None, max_length=500)
    profession: Optional[str] = Field(None, max_length=80)
    education: Optional[str] = Field(None, max_length=100)
    photos: Optional[List[str]] = Field(None, min_length=1, max_length=5)
    avatar_url: Optional[str] = Field(None, max_length=500)
    gender: Optional[GenderType] = None
    interested_in: Optional[InterestedInType] = None
    preferred_age_min: Optional[int] = Field(None, ge=18, le=99)
    preferred_age_max: Optional[int] = Field(None, ge=18, le=100)
    latitude: Optional[Decimal] = Field(None, ge=-90.0, le=90.0)
    location_lat: Optional[Decimal] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[Decimal] = Field(None, ge=-180.0, le=180.0)
    location_lon: Optional[Decimal] = Field(None, ge=-180.0, le=180.0)
    city: Optional[str] = Field(None, max_length=100)
    location_name: Optional[str] = Field(None, max_length=100)
    voice_spark_url: Optional[str] = Field(None, max_length=500)
    voice_spark_duration: Optional[float] = Field(None, ge=0.0, le=60.0)
    voice_spark_prompt: Optional[str] = Field(None, max_length=120)
    prompts: Optional[Any] = None
    contact_bridge: Optional[str] = Field(None, min_length=3, max_length=64)
    contact_bridge_type: Optional[ContactBridgeType] = None
    contact_bridge_raw: Optional[str] = Field(None, min_length=3, max_length=64)
    contact_bridge_handle: Optional[str] = Field(None, min_length=3, max_length=64)
    is_photo_veiled: Optional[bool] = None
    discreet_mode: Optional[bool] = None
    night_slumber: Optional[bool] = None
    passport_city: Optional[str] = Field(None, max_length=100)
    dob: Optional[date] = None

    @field_validator("latitude", "longitude", "location_lat", "location_lon")
    @classmethod
    def fuzz_coordinates(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None:
            return round(v, 2)
        return None

    @model_validator(mode="after")
    def validate_preferred_age_range(self) -> "ProfileUpdate":
        if (
            self.preferred_age_min is not None
            and self.preferred_age_max is not None
            and self.preferred_age_min > self.preferred_age_max
        ):
            raise ValueError("preferred_age_min cannot exceed preferred_age_max")
        return self

class ProfilePublicResponse(BaseModel):
    """Sanitized public seeker card returned on discovery deck, protecting PII."""
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    full_name: str
    age: int
    gender: str
    interested_in: str
    location_name: str
    bio: str
    profession: str
    education: str
    streak_count: int
    boost_points: int
    kyc_status: bool
    is_photo_veiled: bool
    photos: List[str]
    avatar_url: Optional[str] = None
    voice_spark_url: Optional[str] = None
    voice_spark_prompt: Optional[str] = None
    voice_spark_duration: Decimal = Decimal("7.0")
    is_voice_verified: bool = False
    distance_km: Optional[float] = None

    @model_validator(mode="before")
    @classmethod
    def populate_age(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data = dict(data)
            dob = data.pop("dob", None)
            if "age" not in data and dob:
                today = date.today()
                data["age"] = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            return data
        if hasattr(data, "dob") and not hasattr(data, "age"):
            today = date.today()
            v = data.dob
            computed_age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
            return {
                "id": data.id,
                "full_name": data.full_name,
                "age": computed_age,
                "gender": data.gender,
                "interested_in": data.interested_in,
                "location_name": data.location_name,
                "bio": data.bio,
                "profession": data.profession,
                "education": data.education,
                "streak_count": data.streak_count,
                "boost_points": data.boost_points,
                "kyc_status": data.kyc_status,
                "is_photo_veiled": data.is_photo_veiled,
                "photos": data.photos,
                "avatar_url": getattr(data, "avatar_url", None),
                "voice_spark_url": getattr(data, "voice_spark_url", None),
                "voice_spark_prompt": getattr(data, "voice_spark_prompt", None),
                "voice_spark_duration": getattr(data, "voice_spark_duration", None) or Decimal("7.0"),
                "is_voice_verified": getattr(data, "is_voice_verified", None) or False,
                "distance_km": getattr(data, "distance_km", None),
            }
        return data


class ProfileResponse(BaseModel):
    """Seeker's own complete profile response schema."""
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: UUID
    full_name: str
    is_profile_completed: bool
    gender: Optional[str] = None
    interested_in: Optional[str] = None
    bio: Optional[str] = ""
    profession: Optional[str] = ""
    education: Optional[str] = ""
    location_name: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    avatar_url: Optional[str] = None
    photos: List[str] = Field(default_factory=list)
    voice_spark_url: Optional[str] = None
    voice_spark_duration: Optional[float] = None
    voice_spark_prompt: Optional[str] = None
    contact_bridge_type: Optional[str] = None
    is_photo_veiled: Optional[bool] = False
    discreet_mode: Optional[bool] = False
    night_slumber: Optional[bool] = False
    passport_city: Optional[str] = None
    preferred_age_min: Optional[int] = 18
    preferred_age_max: Optional[int] = 35
    kyc_status: Optional[bool] = False
    streak_count: Optional[int] = 0

