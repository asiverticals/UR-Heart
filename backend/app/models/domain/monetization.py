import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import (
    String,
    Numeric,
    Integer,
    ForeignKey,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from .base import Base, TIMESTAMPTZ, BigIntPK, UniversalUUID

class AdRewardLedger(Base):
    __tablename__ = "ad_reward_ledger"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UniversalUUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    ssv_transaction_id: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    network: Mapped[str] = mapped_column(String(20), nullable=False)
    ad_type: Mapped[str] = mapped_column(String(30), nullable=False)
    reward_points: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ,
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint("network IN ('admob', 'admob_client', 'meta', 'unity', 'chartboost', 'liftoff')", name="chk_ad_network"),
        CheckConstraint("ad_type IN ('quick_reflection', 'deep_resonance', 'sacred_bridge_reveal', 'whatsapp_reveal', 'morning_harvest_unlock', 'daily_streak_boost', 'rewarded_daily_boost', 'rewarded_reveal', 'rewarded_extra_swipes', 'rewarded_streak_freeze', 'rewarded_blind_date_extend')", name="chk_ad_type"),
        CheckConstraint("reward_points > 0", name="chk_positive_reward"),
    )

class ProcessedAdTransaction(Base):
    __tablename__ = "processed_ad_transactions"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    transaction_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    network: Mapped[str] = mapped_column(String(32), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UniversalUUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    ad_type: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ,
        server_default=func.now(),
        nullable=False,
    )

class InAppPurchase(Base):
    __tablename__ = "in_app_purchases"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UniversalUUID,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    transaction_reference: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    product_identifier: Mapped[str] = mapped_column(String(60), nullable=False)
    store: Mapped[str] = mapped_column(
        String(30),
        default="google_play",
        server_default="google_play",
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(String(10), default="USD", server_default="USD", nullable=False)
    amount_gross: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        server_default="0.00",
        nullable=False,
    )
    platform_fee: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        server_default="0.00",
        nullable=False,
    )
    amount_net: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        server_default="0.00",
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        server_default="pending",
        nullable=False,
    )
    purchased_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ,
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint("store IN ('google_play', 'web_razorpay_india', 'web_stripe_global')", name="chk_iap_store"),
        CheckConstraint("status IN ('pending', 'completed', 'refunded')", name="chk_iap_status"),
        CheckConstraint("amount_gross >= 0 AND platform_fee >= 0 AND amount_net >= 0", name="chk_iap_nonnegative_amounts"),
    )

class PendingWebEntitlement(Base):
    __tablename__ = "pending_web_entitlements"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    product_identifier: Mapped[str] = mapped_column(String(60), nullable=False)
    payment_reference: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    amount_gross: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        server_default="0.00",
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(String(10), default="INR", server_default="INR", nullable=False)
    status: Mapped[str] = mapped_column(
        String(30),
        default="paid_pending_claim",
        server_default="paid_pending_claim",
        nullable=False,
    )
    claimed_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UniversalUUID,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ,
        server_default=func.now(),
        nullable=False,
    )
    claimed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ, nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('paid_pending_claim', 'claimed', 'refunded')", name="chk_pending_entitlement_status"),
        CheckConstraint("amount_gross >= 0", name="chk_web_entitlement_nonnegative_amount"),
    )
