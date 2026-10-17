import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Dict, Any
from sqlalchemy import (
    String,
    Boolean,
    Numeric,
    SmallInteger,
    Date,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
    JSON,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, synonym
from sqlalchemy.sql import func
from .base import Base, TIMESTAMPTZ, BigIntPK, UniversalUUID

class AdminKycEscalation(Base):
    __tablename__ = "admin_kyc_escalations"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UniversalUUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    declared_dob: Mapped[date] = mapped_column(Date, nullable=False)
    declared_age: Mapped[int] = mapped_column(SmallInteger, default=18, server_default="18", nullable=False)
    groq_match_score: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    groq_reasoning: Mapped[str] = mapped_column(
        String(255),
        default="Automated biometric audit",
        server_default="Automated biometric audit",
        nullable=False,
    )
    anchor_photo_url: Mapped[str] = mapped_column(String(500), default="", server_default="", nullable=False)
    kyc_video_url: Mapped[str] = mapped_column(String(500), default="", server_default="", nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        server_default="pending",
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ,
        server_default=func.now(),
        nullable=False,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ, nullable=True)
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)

    # Backward-compatible synonyms for services and test suites
    id_card_storage_url = synonym("anchor_photo_url")
    selfie_storage_url = synonym("kyc_video_url")

    __table_args__ = (
        CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="chk_admin_kyc_status"),
    )

class DeviceFcmToken(Base):
    __tablename__ = "device_fcm_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UniversalUUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UniversalUUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    platform: Mapped[str] = mapped_column(String(20), default="unknown", server_default="unknown", nullable=False)
    installation_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    active = synonym("is_active")
    last_seen_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ,
        server_default=func.now(),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("user_id", "token", name="uq_user_fcm_token"),
        CheckConstraint("platform IN ('android', 'ios', 'web', 'unknown')", name="chk_device_platform"),
    )

class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    admin_email: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[str] = mapped_column(String(64), nullable=False)
    details: Mapped[Dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON, "sqlite"),
        default=dict,
        server_default="{}",
        nullable=False,
    )
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ,
        server_default=func.now(),
        nullable=False,
    )
