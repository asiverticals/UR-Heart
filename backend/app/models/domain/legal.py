import uuid
from datetime import date, datetime
from typing import Optional, Dict, Any
from sqlalchemy import (
    String,
    Date,
    Text,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
    JSON,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from .base import Base, TIMESTAMPTZ, BigIntPK, UniversalUUID

class UnderageQuarantineRegistry(Base):
    __tablename__ = "underage_quarantine_registry"

    id: Mapped[uuid.UUID] = mapped_column(
        UniversalUUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    device_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    attempted_dob: Mapped[date] = mapped_column(Date, nullable=False)
    quarantine_until: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False)
    attempt_metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON, "sqlite"),
        default=dict,
        server_default="{}",
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ,
        server_default=func.now(),
        nullable=False,
    )

class DataNominee(Base):
    __tablename__ = "data_nominees"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UniversalUUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    nominee_name: Mapped[str] = mapped_column(String(100), nullable=False)
    nominee_contact: Mapped[str] = mapped_column(String(100), nullable=False)
    relationship: Mapped[str] = mapped_column(String(50), nullable=False)
    designated_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ,
        server_default=func.now(),
        nullable=False,
    )

class DataExportRequest(Base):
    __tablename__ = "data_export_requests"

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
    status: Mapped[str] = mapped_column(
        String(20),
        default="processing",
        server_default="processing",
        nullable=False,
    )
    export_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    checksum_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ,
        server_default=func.now(),
        nullable=False,
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ, nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('processing', 'ready', 'expired')", name="chk_export_status"),
    )

class ConsentAuditLog(Base):
    __tablename__ = "consent_audit_logs"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UniversalUUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    consent_purpose_id: Mapped[str] = mapped_column(String(64), nullable=False)
    ip_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    installation_uuid: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ,
        server_default=func.now(),
        nullable=False,
    )

class GrievanceDossier(Base):
    __tablename__ = "grievance_dossiers"

    id: Mapped[uuid.UUID] = mapped_column(
        UniversalUUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    dossier_reference_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    reporter_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UniversalUUID,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reported_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UniversalUUID,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    violation_category: Mapped[str] = mapped_column(String(50), nullable=False)
    statutory_notes: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        default="received",
        server_default="received",
        nullable=False,
    )
    sla_deadline_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ,
        server_default=func.now(),
        nullable=False,
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "violation_category IN ('harassment', 'underage_suspicion', 'impersonation', 'inappropriate_content', 'fraud', 'other')",
            name="chk_grievance_category",
        ),
        CheckConstraint(
            "status IN ('received', 'investigating', 'resolved', 'dismissed')",
            name="chk_grievance_status",
        ),
        CheckConstraint(
            "reporter_id IS NULL OR reported_user_id IS NULL OR reporter_id <> reported_user_id",
            name="chk_grievance_reporter_reported_diff",
        ),
    )

class BlockedUser(Base):
    __tablename__ = "blocked_users"

    id: Mapped[uuid.UUID] = mapped_column(
        UniversalUUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    blocker_id: Mapped[uuid.UUID] = mapped_column(
        UniversalUUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    blocked_id: Mapped[uuid.UUID] = mapped_column(
        UniversalUUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    reason: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ,
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("blocker_id", "blocked_id", name="uq_blocked_users_pair"),
        CheckConstraint("blocker_id <> blocked_id", name="chk_blocked_no_self_block"),
    )

class WebDeletionToken(Base):
    __tablename__ = "web_deletion_tokens"

    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UniversalUUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    auth_id: Mapped[Optional[uuid.UUID]] = mapped_column(UniversalUUID, nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ,
        server_default=func.now(),
        nullable=False,
    )

class ConsumedMagicToken(Base):
    __tablename__ = "consumed_magic_tokens"

    jti: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ,
        server_default=func.now(),
        nullable=False,
    )

