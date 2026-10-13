import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String,
    Boolean,
    SmallInteger,
    Text,
    ForeignKey,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from .base import Base, TIMESTAMPTZ, BigIntPK, UniversalUUID

class BlindDateQueue(Base):
    __tablename__ = "blind_date_queue"

    id: Mapped[uuid.UUID] = mapped_column(
        UniversalUUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UniversalUUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    gender: Mapped[str] = mapped_column(String(15), nullable=False)
    interested_in: Mapped[str] = mapped_column(String(15), nullable=False)
    preferred_age_min: Mapped[int] = mapped_column(SmallInteger, default=18, server_default="18", nullable=False)
    preferred_age_max: Mapped[int] = mapped_column(SmallInteger, default=35, server_default="35", nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        default="waiting",
        server_default="waiting",
        nullable=False,
    )
    is_fast_track: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    joined_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ,
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint("status IN ('waiting', 'matching', 'matched', 'cancelled')", name="chk_blind_queue_status"),
        CheckConstraint("preferred_age_min >= 18 AND preferred_age_min <= preferred_age_max", name="chk_blind_queue_age_range"),
    )

class BlindDateSession(Base):
    __tablename__ = "blind_date_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UniversalUUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    user1_id: Mapped[uuid.UUID] = mapped_column(
        UniversalUUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    user2_id: Mapped[uuid.UUID] = mapped_column(
        UniversalUUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        server_default="active",
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ,
        server_default=func.now(),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False)
    user1_decision: Mapped[str] = mapped_column(
        String(15),
        default="pending",
        server_default="pending",
        nullable=False,
    )
    user2_decision: Mapped[str] = mapped_column(
        String(15),
        default="pending",
        server_default="pending",
        nullable=False,
    )
    icebreaker_prompt: Mapped[Text] = mapped_column(
        Text,
        default="What is a quiet dream you hold close to your heart?",
        server_default="What is a quiet dream you hold close to your heart?",
        nullable=False,
    )
    match_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UniversalUUID,
        ForeignKey("matches.id", ondelete="SET NULL"),
        nullable=True,
    )
    extension_count: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ,
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint("status IN ('active', 'expired', 'revealed', 'passed', 'cancelled')", name="chk_session_status"),
        CheckConstraint("user1_decision IN ('pending', 'resonate', 'pass')", name="chk_user1_decision"),
        CheckConstraint("user2_decision IN ('pending', 'resonate', 'pass')", name="chk_user2_decision"),
        CheckConstraint("user1_id <> user2_id", name="chk_blind_date_no_self_match"),
    )

class BlindDateMessage(Base):
    __tablename__ = "blind_date_messages"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UniversalUUID,
        ForeignKey("blind_date_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        UniversalUUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    recipient_id: Mapped[uuid.UUID] = mapped_column(
        UniversalUUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    encrypted_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ,
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint("sender_id <> recipient_id", name="chk_blind_msg_no_self"),
    )
