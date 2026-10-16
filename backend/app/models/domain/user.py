import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import (
    String,
    Boolean,
    Date,
    Numeric,
    Integer,
    SmallInteger,
    Text,
    CheckConstraint,
    JSON,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, TimestampMixin, TIMESTAMPTZ, UniversalUUID

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UniversalUUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    auth_id: Mapped[uuid.UUID] = mapped_column(
        UniversalUUID,
        unique=True,
        nullable=False,
    )
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    full_name: Mapped[str] = mapped_column(String(60), nullable=False)
    dob: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[str] = mapped_column(String(15), nullable=False)
    interested_in: Mapped[str] = mapped_column(String(15), nullable=False)
    contact_bridge_type: Mapped[str] = mapped_column(
        String(20),
        default="whatsapp",
        server_default="whatsapp",
        nullable=False,
    )
    contact_bridge_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    location_name: Mapped[str] = mapped_column(
        String(100),
        default="Saket, Ayodhya",
        server_default="Saket, Ayodhya",
        nullable=False,
    )
    latitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 6), nullable=True)
    bio: Mapped[str] = mapped_column(String(500), default="", server_default="", nullable=False)
    profession: Mapped[str] = mapped_column(String(80), default="", server_default="", nullable=False)
    education: Mapped[str] = mapped_column(String(100), default="", server_default="", nullable=False)
    preferred_age_min: Mapped[int] = mapped_column(SmallInteger, default=18, server_default="18", nullable=False)
    preferred_age_max: Mapped[int] = mapped_column(SmallInteger, default=35, server_default="35", nullable=False)
    streak_count: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0", nullable=False)
    boost_points: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    last_streak_ad_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ, nullable=True)
    streak_expires_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ, nullable=True)
    reveal_tokens_count: Mapped[int] = mapped_column(SmallInteger, default=1, server_default="1", nullable=False)
    reward_balance: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    swipes_remaining: Mapped[int] = mapped_column(SmallInteger, default=25, server_default="25", nullable=False)
    direct_letters_count: Mapped[int] = mapped_column(SmallInteger, default=1, server_default="1", nullable=False)
    super_likes_count: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0", nullable=False)
    instant_bridge_passes: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0", nullable=False)
    instant_contact_keys: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0", nullable=False)
    has_unlimited_swipes: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    passport_expires_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ, nullable=True)
    last_ad_watched_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ, nullable=True)
    last_installation_uuid: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    referral_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    kyc_status: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    is_incognito: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    is_photo_veiled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    discreet_mode: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    night_slumber: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    is_profile_completed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    welcome_email_sent: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    public_encryption_key: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    push_notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    fcm_token: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    subscription_tier: Mapped[str] = mapped_column(String(20), default="free", server_default="free", nullable=False)
    subscription_expires_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ, nullable=True)
    is_ad_free: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    passport_city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    photos: Mapped[List[str]] = mapped_column(
        MutableList.as_mutable(ARRAY(Text).with_variant(JSON, "sqlite")),
        default=list,
        nullable=False,
    )
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    voice_spark_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    voice_spark_prompt: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    voice_spark_duration: Mapped[Decimal] = mapped_column(
        Numeric(4, 1),
        default=Decimal("7.0"),
        server_default="7.0",
        nullable=False,
    )
    is_voice_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    last_blind_date_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    blind_date_passes: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="user", server_default="user", nullable=False)
    token_version: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ, nullable=True)

    __table_args__ = (
        CheckConstraint("gender IN ('Woman', 'Man', 'Non-Binary', 'Other')", name="chk_gender"),
        CheckConstraint("interested_in IN ('Men', 'Women', 'Everyone')", name="chk_interested_in"),
        CheckConstraint("contact_bridge_type IN ('whatsapp', 'instagram', 'snapchat', 'telegram', 'signal')", name="chk_contact_bridge_type"),
        CheckConstraint("subscription_tier IN ('free', 'spark', 'flame', 'kindred', 'lifetime')", name="chk_subscription_tier"),
        CheckConstraint("role IN ('user', 'moderator', 'superadmin')", name="chk_role"),
        CheckConstraint("preferred_age_min >= 18", name="chk_min_age"),
        CheckConstraint("preferred_age_max <= 100", name="chk_max_age"),
        CheckConstraint("preferred_age_min <= preferred_age_max", name="chk_preferred_age_range"),
    )
