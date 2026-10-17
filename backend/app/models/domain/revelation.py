import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String,
    Boolean,
    SmallInteger,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from .base import Base, TIMESTAMPTZ, UniversalUUID

class ContactRevealToken(Base):
    __tablename__ = "contact_reveal_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UniversalUUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    match_id: Mapped[uuid.UUID] = mapped_column(
        UniversalUUID,
        ForeignKey("matches.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    user1_consent: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    user2_consent: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    user1_ads_count: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0", nullable=False)
    user2_ads_count: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0", nullable=False)
    is_unlocked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    ephemeral_token: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint("user1_ads_count BETWEEN 0 AND 3", name="chk_contact_user1_ads"),
        CheckConstraint("user2_ads_count BETWEEN 0 AND 3", name="chk_contact_user2_ads"),
    )

class PhotoRevealConsent(Base):
    __tablename__ = "photo_reveal_consents"

    id: Mapped[uuid.UUID] = mapped_column(
        UniversalUUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    requester_id: Mapped[uuid.UUID] = mapped_column(
        UniversalUUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        UniversalUUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
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
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("requester_id", "target_id", name="uq_photo_reveal_pair"),
        CheckConstraint("requester_id <> target_id", name="chk_photo_reveal_no_self"),
        CheckConstraint("status IN ('pending', 'accepted', 'declined')", name="chk_photo_reveal_status"),
    )
