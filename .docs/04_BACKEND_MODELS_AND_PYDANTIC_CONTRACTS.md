1. Architectural Philosophy & Type Invariants
UR-Heart Sanctuary enforces an Anti-"Vibe-Code" invariant: Zero dynamic JSON or untyped dictionaries in domain services and API boundaries.
MD

  ┌─────────────────────────────────────────────────────────────┐
  │                 INCOMING REQUEST (HTTP/WSS)                 │
  └──────────────────────────────┬──────────────────────────────┘
                                 │
                                 ▼
  ┌─────────────────────────────────────────────────────────────┐
  │            Pydantic v2 Ingestion & Bounds Contract          │
  │   • Strict Types (UUIDv4/v5, EmailStr, HttpUrl, Constrained)│
  │   • ModelValidator (DOB 18+ Gate, Enum normalization)       │
  │   • ConfigDict(from_attributes=True, extra='forbid')        │
  └──────────────────────────────┬──────────────────────────────┘
                                 │
                                 ▼
  ┌─────────────────────────────────────────────────────────────┐
  │           Domain Services & State Transitions               │
  │   • Typed entity schemas passed across function signatures  │
  │   • Business rules & conditions (C1 – C4) validation        │
  └──────────────────────────────┬──────────────────────────────┘
                                 │
                                 ▼
  ┌─────────────────────────────────────────────────────────────┐
  │       SQLAlchemy 2.0 Async Mapped Persistence Engine        │
  │   • Strict Mapped[T] column declarations                    │
  │   • Native Enum mapping & asyncpg UUID adapters             │
  │   • Explicit lazy="selectin" relationship cascades          │
  └──────────────────────────────┬──────────────────────────────┘
                                 │
                                 ▼
  ┌─────────────────────────────────────────────────────────────┐
  │             OUTGOING RESPONSE (Pydantic Out Schema)         │
  └─────────────────────────────────────────────────────────────┘
Invariant Rules
Pydantic v2 extra='forbid': All ingestion schemas explicitly reject unknown JSON keys to stop payload injection attacks and parameter pollution.

SQLAlchemy 2.0 Declarative Mapping: All models utilize Mapped[...] and mapped_column(...). Legacy Column() syntax is prohibited.

No Database Leaks: Internal ORM objects are never returned directly to endpoints; every route serializes through an explicit Pydantic response contract.

Error Containment: Every failure yields a typed SanctuaryErrorResponse schema with zero stack traces leaked in production.
MD

1. Standard Error Taxonomy & Exception Models
2.1 Standardized Error Contract (SanctuaryErrorResponse)
Python

# backend/app/schemas/base_response.py

from datetime import datetime, timezone
from typing import Generic, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")

class SanctuaryResponse(BaseModel, Generic[T]):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    success: bool = Field(default=True, description="Indicates operation success")
    data: Optional[T] = Field(default=None, description="Typed payload")
    message: Optional[str] = Field(default=None, description="Human readable contextual message")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="ISO 8601 UTC timestamp"
    )

class SanctuaryErrorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    success: bool = Field(default=False, description="Always false for error states")
    error_code: str = Field(..., description="Machine-readable error identifier")
    message: str = Field(..., description="Human-readable safe explanation")
    details: Optional[dict] = Field(default=None, description="Optional safe structured context")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="ISO 8601 UTC timestamp"
    )

MD

2.2 Domain Exception Hierarchy (backend/app/core/exceptions.py)
Python

# backend/app/core/exceptions.py

from typing import Optional
from fastapi import status

class SanctuaryException(Exception):
    """Base exception for all intentional sanctuary domain errors."""
    def __init__(
        self,
        error_code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[dict] = None
    ):
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details

class UnderageRegistrationException(SanctuaryException):
    def __init__(self, message: str = "Seeker is under the legal threshold of 18 years."):
        super().__init__(
            error_code="UNDERAGE_QUARANTINE_TRIGGERED",
            message=message,
            status_code=status.HTTP_403_FORBIDDEN
        )

class MilestoneLockedException(SanctuaryException):
    def __init__(self, condition_code: str, current_mau: int, target_mau: int = 1_000_000):
        super().__init__(
            error_code="MILESTONE_LOCKED",
            message=f"Feature gated under condition {condition_code} until sanctuary reaches {target_mau} active souls.",
            status_code=status.HTTP_403_FORBIDDEN,
            details={"condition": condition_code, "current_mau": current_mau, "target_mau": target_mau}
        )

class BilateralConsentPendingException(SanctuaryException):
    def __init__(self, message: str = "Sacred action requires affirmative consent from both seekers."):
        super().__init__(
            error_code="BILATERAL_CONSENT_REQUIRED",
            message=message,
            status_code=status.HTTP_423_LOCKED
        )

class ReplayAttackDetectedException(SanctuaryException):
    def __init__(self, transaction_id: str):
        super().__init__(
            error_code="IDEMPOTENCY_REPLAY_DETECTED",
            message="This transaction or callback has already been processed.",
            status_code=status.HTTP_200_OK,  # Idempotent 200 response to webhooks
            details={"transaction_id": transaction_id}
        )

class QuarantinedDeviceException(SanctuaryException):
    def __init__(self, quarantine_until: str):
        super().__init__(
            error_code="DEVICE_HARDWARE_QUARANTINED",
            message="This device has been quarantined under child safety protection mandates.",
            status_code=status.HTTP_403_FORBIDDEN,
            details={"quarantine_until": quarantine_until}
        )

MD

1. SQLAlchemy 2.0 Async Domain Models (backend/app/models/domain/)
3.1 Declarative Base Setup (backend/app/models/domain/base.py)
Python

# backend/app/models/domain/base.py

from datetime import datetime, timezone
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import TIMESTAMPTZ

# Unified naming convention for Postgres constraints

convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "chk_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=convention)

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ,
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
3.2 Core Identity & Kinship Models
Python

# backend/app/models/domain/user.py

import uuid
from datetime import date, datetime
from typing import List, Optional
from decimal import Decimal
from sqlalchemy import (
    String, Boolean, Date, Numeric, Integer, SmallInteger, Text, ARRAY, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMPTZ
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    auth_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    full_name: Mapped[str] = mapped_column(String(60), nullable=False)
    dob: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[str] = mapped_column(String(15), nullable=False)
    interested_in: Mapped[str] = mapped_column(String(15), nullable=False)
    contact_bridge_type: Mapped[str] = mapped_column(String(20), default="whatsapp", nullable=False)
    contact_bridge_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    location_name: Mapped[str] = mapped_column(String(100), default="Saket, Ayodhya", nullable=False)
    latitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 6), nullable=True)
    bio: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    profession: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    education: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    preferred_age_min: Mapped[int] = mapped_column(SmallInteger, default=18, nullable=False)
    preferred_age_max: Mapped[int] = mapped_column(SmallInteger, default=35, nullable=False)
    streak_count: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    boost_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_streak_ad_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ, nullable=True)
    streak_expires_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ, nullable=True)
    reveal_tokens_count: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    reward_balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    swipes_remaining: Mapped[int] = mapped_column(SmallInteger, default=25, nullable=False)
    direct_letters_count: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    last_installation_uuid: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    referral_code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    kyc_status: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_incognito: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_photo_veiled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    discreet_mode: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    night_slumber: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_profile_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    welcome_email_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    public_encryption_key: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    push_notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    fcm_token: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    subscription_tier: Mapped[str] = mapped_column(String(20), default="free", nullable=False)
    subscription_expires_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ, nullable=True)
    is_ad_free: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    passport_city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    photos: Mapped[List[str]] = mapped_column(ARRAY(Text), default=list, nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    voice_spark_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    voice_spark_prompt: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    voice_spark_duration: Mapped[Decimal] = mapped_column(Numeric(4, 1), default=Decimal("7.0"), nullable=False)
    is_voice_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_blind_date_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    blind_date_passes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="user", nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ, nullable=True)

    __table_args__ = (
        CheckConstraint("gender IN ('Woman', 'Man', 'Non-Binary', 'Other')", name="chk_gender"),
        CheckConstraint("interested_in IN ('Men', 'Women', 'Everyone')", name="chk_interested_in"),
        CheckConstraint("role IN ('user', 'moderator', 'superadmin')", name="chk_role"),
        CheckConstraint("preferred_age_min >= 18", name="chk_min_age"),
        CheckConstraint("preferred_age_max <= 100", name="chk_max_age"),
    )

MD

Python

# backend/app/models/domain/match_and_chat.py

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String, Boolean, BigInteger, Text, ForeignKey, CheckConstraint, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMPTZ
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin

class Match(Base):
    __tablename__ = "matches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user1_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user2_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    matched_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, default=datetime.utcnow, nullable=False)
    last_message_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, default=datetime.utcnow, nullable=False)
    closure_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    closed_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ, nullable=True)
    closure_template_key: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    closure_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("user1_id", "user2_id", name="uq_match_pair"),
        CheckConstraint("user1_id <> user2_id", name="chk_no_self_match"),
    )

class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    match_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("matches.id", ondelete="CASCADE"), nullable=False)
    sender_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    encrypted_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(10), default="sent", nullable=False)
    client_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('sent', 'delivered', 'read')", name="chk_msg_status"),
    )

MD

3.3 Blind Date & Monetization Models
Python

# backend/app/models/domain/blind_date.py

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, SmallInteger, Text, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMPTZ
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base

class BlindDateSession(Base):
    __tablename__ = "blind_date_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user1_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user2_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    started_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, default=datetime.utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False)
    user1_decision: Mapped[str] = mapped_column(String(15), default="pending", nullable=False)
    user2_decision: Mapped[str] = mapped_column(String(15), default="pending", nullable=False)
    icebreaker_prompt: Mapped[str] = mapped_column(Text, default="What is a quiet dream you hold close to your heart?", nullable=False)
    match_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("matches.id", ondelete="SET NULL"), nullable=True)
    extension_count: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('active', 'expired', 'revealed', 'passed', 'cancelled')", name="chk_session_status"),
        CheckConstraint("user1_decision IN ('pending', 'resonate', 'pass')", name="chk_user1_decision"),
        CheckConstraint("user2_decision IN ('pending', 'resonate', 'pass')", name="chk_user2_decision"),
    )

MD

Python

# backend/app/models/domain/monetization.py

from datetime import datetime
from decimal import Decimal
from typing import Optional
import uuid
from sqlalchemy import String, BigInteger, Numeric, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMPTZ
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base

class AdRewardLedger(Base):
    __tablename__ = "ad_reward_ledger"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ssv_transaction_id: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    network: Mapped[str] = mapped_column(String(20), nullable=False)
    ad_type: Mapped[str] = mapped_column(String(30), nullable=False)
    reward_points: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("network IN ('admob', 'admob_client', 'meta', 'unity', 'chartboost', 'liftoff')", name="chk_ad_network"),
        CheckConstraint("reward_points > 0", name="chk_positive_reward"),
    )

class PendingWebEntitlement(Base):
    __tablename__ = "pending_web_entitlements"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    product_identifier: Mapped[str] = mapped_column(String(60), nullable=False)
    payment_reference: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    amount_gross: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="paid_pending_claim", nullable=False)
    claimed_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, default=datetime.utcnow, nullable=False)
    claimed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ, nullable=True)

MD

1. Pydantic v2 Ingestion & Response Schemas (backend/app/schemas/)
4.1 Authentication & Onboarding Schemas
Python

# backend/app/schemas/auth.py

from datetime import date
from typing import Optional, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

class RegisterIntentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dob: date = Field(..., description="Declared Date of Birth")
    device_fingerprint: str = Field(..., min_length=32, max_length=64, description="SHA-256 hardware hash")

    @field_validator("dob")
    @classmethod
    def validate_age_threshold(cls, v: date) -> date:
        today = date.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age < 18:
            raise ValueError("Seeker is under 18 years of age. Registration prohibited.")
        return v

class GoogleSyncRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_token: str = Field(..., min_length=50, description="RS256 Google JWT token")
    installation_uuid: Optional[str] = Field(None, max_length=64)

class TokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    user_id: UUID
    is_profile_completed: bool

MD

4.2 Profile & Seeker Schemas
Python

# backend/app/schemas/profile.py

from datetime import date
from decimal import Decimal
from typing import List, Optional, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator

GenderType = Literal["Woman", "Man", "Non-Binary", "Other"]
InterestedInType = Literal["Men", "Women", "Everyone"]
ContactBridgeType = Literal["whatsapp", "instagram", "snapchat", "telegram", "signal"]

class ProfileCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(..., min_length=2, max_length=60)
    dob: date
    gender: GenderType
    interested_in: InterestedInType
    contact_bridge_type: ContactBridgeType = "whatsapp"
    contact_bridge_raw: str = Field(..., min_length=3, max_length=64, description="Will be encrypted AES-256")
    bio: str = Field(default="", max_length=500)
    profession: str = Field(default="", max_length=80)
    education: str = Field(default="", max_length=100)
    photos: List[str] = Field(..., min_length=1, max_length=5, description="Supabase storage path URLs")
    avatar_url: Optional[str] = Field(None, max_length=500)
    latitude: Optional[Decimal] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[Decimal] = Field(None, ge=-180.0, le=180.0)

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

class ProfilePublicResponse(BaseModel):
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
    avatar_url: Optional[str]
    voice_spark_url: Optional[str]
    voice_spark_prompt: Optional[str]
    voice_spark_duration: Decimal
    is_voice_verified: bool

MD

4.3 Discovery Deck, Swipes & Photo Reveal
Python

# backend/app/schemas/feed.py

from typing import Optional, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

SwipeAction = Literal["like", "pass", "superlike"]

class SwipeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_id: UUID = Field(..., description="Target seeker profile UUID")
    action: SwipeAction
    direct_letter_text: Optional[str] = Field(None, max_length=280, description="Encrypted letter note if applicable")

class PhotoRevealRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_id: UUID = Field(..., description="Seeker whose photo veil unmasking is requested")

class PhotoRevealResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_id: UUID
    status: Literal["pending", "accepted", "declined"]

MD

4.4 Real-Time Encrypted Dialogue Chamber
Python

# backend/app/schemas/chat.py

from datetime import datetime
from typing import Optional, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

class DialogueMessageSend(BaseModel):
    model_config = ConfigDict(extra="forbid")

    match_id: UUID
    recipient_id: UUID
    encrypted_text: str = Field(..., min_length=1, max_length=4096)
    client_id: str = Field(..., max_length=64, description="Client-side UUID for idempotency")

class MessageItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: int
    match_id: UUID
    sender_id: UUID
    encrypted_text: str
    status: str
    client_id: Optional[str]
    created_at: datetime

class PassWithGraceClosureRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    closure_template_key: str = Field(..., max_length=50)
    closure_note: Optional[str] = Field(None, max_length=300)

class WsTicketResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticket: str = Field(..., description="Single-use 32-byte cryptographic token")
    expires_in_seconds: int = 60
    endpoint_url: str = Field(..., description="wss://urheart.app/ws/chat")

MD

4.5 180s Blind Date Subsystem (Condition C1)
Python

# backend/app/schemas/blind_date.py

from datetime import datetime
from typing import Optional, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

class BlindDateQueueJoin(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preferred_age_min: int = Field(default=18, ge=18, le=99)
    preferred_age_max: int = Field(default=35, ge=18, le=100)
    is_fast_track: bool = Field(default=False)

class BlindDateSessionResponse(BaseModel):
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
    model_config = ConfigDict(extra="forbid")

    decision: Literal["resonate", "pass"]

MD

4.6 Monetization, Store & Ad SSV Waterfall (Condition C2)
Python

# backend/app/schemas/monetization.py

from decimal import Decimal
from typing import Optional, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator

class RazorpayOrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_identifier: str = Field(..., max_length=60)
    currency: Literal["INR", "USD"] = "INR"

    @field_validator("currency")
    @classmethod
    def validate_usd_allowed(cls, v: str) -> str:
        if v == "USD":
            from app.core.config import settings
            if not getattr(settings, "ENABLE_GLOBAL_USD_BILLING", False):
                raise ValueError("USD billing is disabled under condition C2 until global milestone activation")
        return v

class RazorpayPaymentVerify(BaseModel):
    model_config = ConfigDict(extra="forbid")

    razorpay_order_id: str = Field(..., max_length=150)
    razorpay_payment_id: str = Field(..., max_length=150)
    razorpay_signature: str = Field(..., max_length=256)

class AdSSVCallbackParams(BaseModel):
    model_config = ConfigDict(extra="allow")  # Allows network-specific query parameters

    custom_data: str = Field(..., description="{user_id}:{ad_type}:{target_id}")
    transaction_id: str = Field(..., description="Unique ad view ID")
    signature: Optional[str] = None
    key_id: Optional[str] = None

class WebStoreClaimPending(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(..., max_length=255)

MD

4.7 DPDP Act Legal & Grievance Schemas
Python

# backend/app/schemas/legal.py

from typing import Optional, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

ViolationCategory = Literal["harassment", "explicit_content", "impersonation", "underage", "offplatform_leak"]

class GrievanceSubmitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reported_user_id: UUID
    violation_category: ViolationCategory
    evidence_text: str = Field(default="", max_length=500)

class GrievanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    dossier_reference_id: str
    status: str
    acknowledgment_sent_at: str
    statutory_resolution_due_at: str

class DataNomineeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nominee_name: str = Field(..., min_length=2, max_length=60)
    nominee_contact: str = Field(..., min_length=5, max_length=30)
    relationship: str = Field(..., min_length=2, max_length=30)

class WebAccountDeletionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(..., max_length=255)
    reason: Optional[str] = Field(None, max_length=500)

MD

1. Verification & Boundary Testing Standard
Any entity mapping or schema validation error is tested via:

Bash

pytest backend/tests/test_phase1_persistence.py backend/tests/test_sec01_jwt_verification.py

MD

All Pydantic v2 validation contracts must pass static analysis without warnings:

Bash

python -m mypy backend/app/schemas backend/app/models
