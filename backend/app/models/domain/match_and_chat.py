import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String,
    Boolean,
    Text,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from .base import Base, TIMESTAMPTZ, BigIntPK, UniversalUUID

class Swipe(Base):
    __tablename__ = "swipes"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    actor_id: Mapped[uuid.UUID] = mapped_column(
        UniversalUUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        UniversalUUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    swipe_type: Mapped[str] = mapped_column(String(10), nullable=False)
    direct_letter_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ,
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("actor_id", "target_id", name="uq_swipes_actor_target"),
        CheckConstraint("actor_id <> target_id", name="chk_swipes_no_self_swipe"),
        CheckConstraint("swipe_type IN ('like', 'pass', 'superlike')", name="chk_swipes_type"),
    )

class Match(Base):
    __tablename__ = "matches"

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
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    matched_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ,
        server_default=func.now(),
        nullable=False,
    )
    last_message_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ,
        server_default=func.now(),
        nullable=False,
    )
    closure_status: Mapped[str] = mapped_column(
        String(30),
        default="active",
        server_default="active",
        nullable=False,
    )
    closed_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UniversalUUID,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ, nullable=True)
    closure_template_key: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    closure_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("user1_id", "user2_id", name="uq_matches_pair"),
        CheckConstraint("user1_id <> user2_id", name="chk_matches_no_self_match"),
        CheckConstraint("user1_id < user2_id", name="chk_matches_ordered_pair"),
        CheckConstraint("closure_status IN ('active', 'closed_with_grace', 'unmatched')", name="chk_matches_closure_status"),
    )

class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    match_id: Mapped[uuid.UUID] = mapped_column(
        UniversalUUID,
        ForeignKey("matches.id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        UniversalUUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    encrypted_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(10), default="sent", server_default="sent", nullable=False)
    client_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ,
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint("status IN ('sent', 'delivered', 'read')", name="chk_messages_status"),
    )
