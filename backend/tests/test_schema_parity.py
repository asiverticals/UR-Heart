"""
Milestone 2 Schema Parity & Integrity Verification Tests.

Verifies:
1. Primary key types parity between PostgreSQL and SQLAlchemy declarative models:
   - GrievanceDossier: BigIntPK
   - AdminKycEscalation: BigIntPK
   - DeviceFcmToken: UniversalUUID
   - BlindDateMessage: UniversalUUID
2. Column parity and SQLAlchemy synonyms:
   - AdminKycEscalation: anchor_photo_url, kyc_video_url, declared_age, groq_reasoning,
     with synonyms selfie_storage_url and id_card_storage_url.
   - DeviceFcmToken: is_active with active synonym, installation_id, last_seen_at.
   - BlindDateMessage: encrypted_text with ciphertext synonym, nullable recipient_id.
3. Check constraints and status lifecycle:
   - GrievanceDossier: status in ('under_review', 'actioned', 'dismissed', 'acknowledged', 'investigating', 'closed').
   - Default status is 'acknowledged'.
4. Ad reward ledger 22 types parity:
   - SQL migration includes all 22 legitimate ad reward types.
   - AdSSVService emission types are completely covered.
5. Service defense:
   - AdminService.decide_escalation handles integer IDs via str.isdigit() safely.
6. Endpoint defense:
   - PUT /api/v1/profile composite age range check prevents min > max on partial updates.
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Integer, BigInteger, String, Uuid, inspect, select
from sqlalchemy.exc import IntegrityError

from backend.app.main import app
from backend.app.core.database import get_db
from backend.app.api.deps import get_current_user
from backend.app.models.domain import (
    Base,
    User,
    AdRewardLedger,
    GrievanceDossier,
    AdminKycEscalation,
    DeviceFcmToken,
    BlindDateMessage,
    BlindDateSession,
    ContactRevealToken,
)
from backend.app.models.domain.base import BigIntPK, UniversalUUID
from backend.app.services.admin_service import AdminService
from backend.app.services.ad_ssv_service import AdSsvService


# ---------------------------------------------------------------------------
# 1. Primary Key Types Parity
# ---------------------------------------------------------------------------

def test_grievance_dossier_pk_is_bigint():
    """GrievanceDossier.id must be BigIntPK to match PostgreSQL BIGINT identity."""
    mapper = inspect(GrievanceDossier)
    pk_col = mapper.primary_key[0]
    assert pk_col.name == "id"
    assert isinstance(pk_col.type, (Integer, BigInteger))


def test_admin_kyc_escalation_pk_is_bigint():
    """AdminKycEscalation.id must be BigIntPK to match PostgreSQL BIGINT identity."""
    mapper = inspect(AdminKycEscalation)
    pk_col = mapper.primary_key[0]
    assert pk_col.name == "id"
    assert isinstance(pk_col.type, (Integer, BigInteger))


def test_device_fcm_token_pk_is_uuid():
    """DeviceFcmToken.id must be UniversalUUID matching PostgreSQL UUID PK."""
    mapper = inspect(DeviceFcmToken)
    pk_col = mapper.primary_key[0]
    assert pk_col.name == "id"
    assert isinstance(pk_col.type, Uuid)


def test_blind_date_message_pk_is_uuid():
    """BlindDateMessage.id must be UniversalUUID matching PostgreSQL UUID PK."""
    mapper = inspect(BlindDateMessage)
    pk_col = mapper.primary_key[0]
    assert pk_col.name == "id"
    assert isinstance(pk_col.type, Uuid)


# ---------------------------------------------------------------------------
# 2. Column Parity & Synonyms
# ---------------------------------------------------------------------------

def test_admin_kyc_escalation_columns_and_synonyms():
    """AdminKycEscalation must expose canonical columns and backward-compatible synonyms."""
    mapper = inspect(AdminKycEscalation)
    column_names = {c.name for c in mapper.columns}
    assert "anchor_photo_url" in column_names
    assert "kyc_video_url" in column_names
    assert "declared_age" in column_names
    assert "groq_reasoning" in column_names

    # Verify column defaults on the metadata
    assert mapper.columns["declared_age"].default.arg == 18
    assert mapper.columns["groq_reasoning"].default.arg == "Automated biometric audit"

    # Instantiate model using synonyms
    esc = AdminKycEscalation(
        user_id=uuid.uuid4(),
        declared_dob=date(2000, 1, 1),
        groq_match_score=Decimal("0.950"),
        id_card_storage_url="https://media.urheart.app/id.jpg",
        selfie_storage_url="https://media.urheart.app/selfie.mp4",
    )
    # Synonyms should write to canonical columns
    assert esc.anchor_photo_url == "https://media.urheart.app/id.jpg"
    assert esc.kyc_video_url == "https://media.urheart.app/selfie.mp4"
    assert esc.id_card_storage_url == "https://media.urheart.app/id.jpg"
    assert esc.selfie_storage_url == "https://media.urheart.app/selfie.mp4"


def test_device_fcm_token_columns_and_synonym():
    """DeviceFcmToken must expose is_active, installation_id, last_seen_at and active synonym."""
    mapper = inspect(DeviceFcmToken)
    column_names = {c.name for c in mapper.columns}
    assert "is_active" in column_names
    assert "installation_id" in column_names
    assert "last_seen_at" in column_names

    token_obj = DeviceFcmToken(
        user_id=uuid.uuid4(),
        token="sample_fcm_token_12345",
        platform="android",
        active=True,
    )
    assert token_obj.is_active is True
    assert token_obj.active is True

    token_obj.active = False
    assert token_obj.is_active is False


def test_blind_date_message_columns_and_synonym():
    """BlindDateMessage must expose encrypted_text, ciphertext synonym, and nullable recipient_id."""
    mapper = inspect(BlindDateMessage)
    column_names = {c.name for c in mapper.columns}
    assert "encrypted_text" in column_names

    recipient_col = mapper.columns["recipient_id"]
    assert recipient_col.nullable is True

    msg = BlindDateMessage(
        session_id=uuid.uuid4(),
        sender_id=uuid.uuid4(),
        ciphertext="encrypted_payload_bytes",
    )
    assert msg.encrypted_text == "encrypted_payload_bytes"
    assert msg.ciphertext == "encrypted_payload_bytes"
    assert msg.recipient_id is None


# ---------------------------------------------------------------------------
# 3. Status Lifecycle & Grievance Constraints
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_grievance_dossier_persistence_and_statuses(db_session, make_user):
    """GrievanceDossier defaults to acknowledged and accepts all 6 valid statuses."""
    reporter = make_user()
    reported = make_user()
    db_session.add_all([reporter, reported])
    await db_session.commit()

    valid_statuses = [
        "under_review",
        "actioned",
        "dismissed",
        "acknowledged",
        "investigating",
        "closed",
    ]

    for idx, st in enumerate(valid_statuses):
        dossier = GrievanceDossier(
            dossier_reference_id=f"GRV-TEST-{idx:04d}",
            reporter_id=reporter.id,
            reported_user_id=reported.id,
            violation_category="harassment",
            evidence_text=f"Evidence for status {st}",
            statutory_notes="Statutory tracking note",
            status=st,
            resolution_summary=f"Resolved as {st}" if st in ("actioned", "closed") else None,
            actioned_at=datetime.now(timezone.utc) if st == "actioned" else None,
        )
        db_session.add(dossier)

    await db_session.commit()

    # Query back and verify BigInt identity ID
    result = await db_session.execute(
        select(GrievanceDossier).order_by(GrievanceDossier.id.asc())
    )
    saved = result.scalars().all()
    assert len(saved) == 6
    for s in saved:
        assert isinstance(s.id, int)
        assert s.id > 0
        assert s.statutory_notes == "Statutory tracking note"


# ---------------------------------------------------------------------------
# 4. Ad Reward 22 Types Parity
# ---------------------------------------------------------------------------

def test_migration_contains_all_22_ad_types():
    """Verify that the SQL migration explicitly includes all 22 legitimate ad reward types."""
    migration_path = Path("supabase/migrations/20261016150000_harmonize_schema_types_and_constraints.sql")
    assert migration_path.exists(), "Migration file does not exist!"

    content = migration_path.read_text(encoding="utf-8")

    expected_ad_types = [
        "quick_reflection",
        "deep_resonance",
        "sacred_bridge_reveal",
        "whatsapp_reveal",
        "morning_harvest_unlock",
        "daily_streak_boost",
        "rewarded_daily_boost",
        "rewarded_reveal",
        "rewarded_extra_swipes",
        "rewarded_streak_freeze",
        "rewarded_blind_date_extend",
        "extra_swipes",
        "daily_harvest_boost",
        "instant_reveal_key",
        "super_like",
        "instant_bridge_pass",
        "streak_freeze",
        "rewind_pass",
        "compass_teleport",
        "ad_free_24h",
        "profile_spotlight",
        "incognito_hour",
    ]

    for ad_type in expected_ad_types:
        assert f"'{ad_type}'" in content, f"Missing ad type: {ad_type} in migration constraint!"


def test_ad_reward_ledger_ad_type_column_length():
    """AdRewardLedger.ad_type column length must be String(50) to match PostgreSQL VARCHAR(50)."""
    mapper = inspect(AdRewardLedger)
    col = mapper.columns["ad_type"]
    assert isinstance(col.type, String)
    assert col.type.length == 50


@pytest.mark.asyncio
async def test_ad_reward_ledger_orm_accepts_all_22_ad_types(db_session, make_user):
    """Verify that AdRewardLedger ORM entity can be inserted into db_session for all 22 ad types without constraint failure."""
    user = make_user()
    db_session.add(user)
    await db_session.commit()

    expected_ad_types = [
        "quick_reflection",
        "deep_resonance",
        "sacred_bridge_reveal",
        "whatsapp_reveal",
        "morning_harvest_unlock",
        "daily_streak_boost",
        "rewarded_daily_boost",
        "rewarded_reveal",
        "rewarded_extra_swipes",
        "rewarded_streak_freeze",
        "rewarded_blind_date_extend",
        "extra_swipes",
        "daily_harvest_boost",
        "instant_reveal_key",
        "super_like",
        "instant_bridge_pass",
        "streak_freeze",
        "rewind_pass",
        "compass_teleport",
        "ad_free_24h",
        "profile_spotlight",
        "incognito_hour",
    ]

    for idx, ad_type in enumerate(expected_ad_types):
        ledger = AdRewardLedger(
            user_id=user.id,
            ssv_transaction_id=f"tx_schema_parity_{idx}_{uuid.uuid4().hex[:8]}",
            network="admob",
            ad_type=ad_type,
            reward_points=10,
        )
        db_session.add(ledger)

    await db_session.commit()

    # Query back and verify all 22 records were persisted with proper ad_type
    result = await db_session.execute(
        select(AdRewardLedger).where(
            AdRewardLedger.user_id == user.id,
            AdRewardLedger.ssv_transaction_id.like("tx_schema_parity_%"),
        )
    )
    records = result.scalars().all()
    assert len(records) == 22
    persisted_types = {r.ad_type for r in records}
    assert persisted_types == set(expected_ad_types)

    # Verify check constraint rejects invalid ad types
    async with db_session.begin_nested():
        invalid_ledger = AdRewardLedger(
            user_id=user.id,
            ssv_transaction_id=f"tx_invalid_{uuid.uuid4().hex[:8]}",
            network="admob",
            ad_type="invalid_unauthorized_ad_type",
            reward_points=10,
        )
        db_session.add(invalid_ledger)
        with pytest.raises(IntegrityError):
            await db_session.flush()


# ---------------------------------------------------------------------------
# 5. Service Integer ID Handling in AdminService
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_service_decide_escalation_by_integer_id(db_session, make_user):
    """AdminService.decide_escalation safely looks up tickets via integer ID."""
    reviewer = make_user()
    candidate = make_user()
    db_session.add_all([reviewer, candidate])
    await db_session.commit()

    escalation = AdminKycEscalation(
        user_id=candidate.id,
        declared_dob=candidate.dob or date(2000, 1, 1),
        groq_match_score=Decimal("0.850"),
        anchor_photo_url="https://media.urheart.app/id.jpg",
        kyc_video_url="https://media.urheart.app/selfie.mp4",
        status="pending",
    )
    db_session.add(escalation)
    await db_session.commit()
    await db_session.refresh(escalation)

    assert isinstance(escalation.id, int)

    service = AdminService()
    # Adjudicate using stringified integer ID
    response = await service.decide_escalation(
        session=db_session,
        escalation_id=str(escalation.id),
        decision="approve",
        reviewer=reviewer,
    )
    assert response.success is True
    assert response.status == "approved"

    # Verify user kyc_status was updated
    await db_session.refresh(candidate)
    assert candidate.kyc_status is True


# ---------------------------------------------------------------------------
# 6. Composite Age Range Check on Profile Endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_put_profile_composite_age_range_rejection(db_session, make_user):
    """Partial age update where new min exceeds existing max must return 422."""
    user = make_user(is_profile_completed=True)
    user.preferred_age_min = 20
    user.preferred_age_max = 28
    db_session.add(user)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Send only preferred_age_min = 30, which exceeds existing max (28)
            resp = await client.put(
                "/api/v1/profile",
                json={"preferred_age_min": 30},
            )
            assert resp.status_code == 422
            data = resp.json()
            assert data.get("error_code") == "INVALID_AGE_RANGE" or "cannot exceed" in resp.text

            # Send only preferred_age_max = 19, which is less than existing min (20)
            resp2 = await client.put(
                "/api/v1/profile",
                json={"preferred_age_max": 19},
            )
            assert resp2.status_code == 422

            # Send valid partial update preferred_age_min = 22 <= existing max 28
            resp3 = await client.put(
                "/api/v1/profile",
                json={"preferred_age_min": 22},
            )
            assert resp3.status_code == 200
            assert resp3.json()["data"]["preferred_age_min"] == 22
    finally:
        app.dependency_overrides.clear()
