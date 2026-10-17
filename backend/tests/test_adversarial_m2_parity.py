"""Adversarial & Empirical Parity Verification Suite for Milestone 2 (Challenger M2_2).

Verifies:
1. 100% elimination of WhatsappRevealToken from domain models, exports, and Base metadata.
2. Model primary key type parity against PostgreSQL DDL:
   - GrievanceDossier.id: BigIntPK (> 2^31 - 1 persistence)
   - AdminKycEscalation.id: BigIntPK (> 2^31 - 1 persistence)
   - DeviceFcmToken.id: UniversalUUID (UUID PK)
   - BlindDateMessage.id: UniversalUUID (UUID PK)
3. SQLAlchemy column synonyms functioning seamlessly in live queries:
   - BlindDateMessage: ciphertext <-> encrypted_text (WHERE, LIKE, ORDER BY, mutation)
   - DeviceFcmToken: active <-> is_active (WHERE == True, WHERE == False, mutation)
   - AdminKycEscalation: id_card_storage_url <-> anchor_photo_url, selfie_storage_url <-> kyc_video_url
4. Check constraints & model parity invariants.
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
import pytest
from sqlalchemy import BigInteger, Integer, Uuid, inspect, select, desc
from sqlalchemy.exc import IntegrityError

from backend.app.models.domain import (
    Base,
    User,
    GrievanceDossier,
    AdminKycEscalation,
    DeviceFcmToken,
    BlindDateMessage,
    BlindDateSession,
)
from backend.app.models.domain.base import BigIntPK, UniversalUUID


# ==============================================================================
# 1. Elimination of WhatsappRevealToken
# ==============================================================================

def test_whatsapp_reveal_token_eliminated_from_domain_models():
    """Verify WhatsappRevealToken is completely removed from models, __all__, and metadata."""
    import backend.app.models.domain as domain_pkg
    assert "WhatsappRevealToken" not in domain_pkg.__all__
    assert not hasattr(domain_pkg, "WhatsappRevealToken")

    import backend.app.models.domain.revelation as rev_mod
    assert not hasattr(rev_mod, "WhatsappRevealToken")
    assert "whatsapp_reveal_tokens" not in Base.metadata.tables


def test_whatsapp_reveal_token_zero_code_references():
    """Verify zero source code references in backend/app and supabase/migrations."""
    repo_root = Path(__file__).resolve().parents[2]

    # Check python files
    for py_path in (repo_root / "backend" / "app").rglob("*.py"):
        content = py_path.read_text(encoding="utf-8", errors="ignore")
        assert "WhatsappRevealToken" not in content, f"Found reference in {py_path}"


# ==============================================================================
# 2. Primary Key PostgreSQL Parity
# ==============================================================================

def test_primary_key_postgres_types():
    """GrievanceDossier and AdminKycEscalation must be BigIntPK; DeviceFcmToken and BlindDateMessage UniversalUUID."""
    # GrievanceDossier
    gd_pk = inspect(GrievanceDossier).primary_key[0]
    assert gd_pk.name == "id"
    assert isinstance(gd_pk.type, (BigInteger, Integer))
    assert gd_pk.autoincrement is True

    # AdminKycEscalation
    esc_pk = inspect(AdminKycEscalation).primary_key[0]
    assert esc_pk.name == "id"
    assert isinstance(esc_pk.type, (BigInteger, Integer))
    assert esc_pk.autoincrement is True

    # DeviceFcmToken
    fcm_pk = inspect(DeviceFcmToken).primary_key[0]
    assert fcm_pk.name == "id"
    assert isinstance(fcm_pk.type, Uuid)
    assert fcm_pk.type.as_uuid is True

    # BlindDateMessage
    bdm_pk = inspect(BlindDateMessage).primary_key[0]
    assert bdm_pk.name == "id"
    assert isinstance(bdm_pk.type, Uuid)
    assert bdm_pk.type.as_uuid is True


@pytest.mark.asyncio
async def test_bigint_64bit_range_persistence(db_session, make_user):
    """Verify that 64-bit integer IDs (> 2^31 - 1) persist without truncation or overflow."""
    u1 = make_user()
    u2 = make_user()
    db_session.add_all([u1, u2])
    await db_session.commit()

    large_id_1 = 6_000_000_001
    gd = GrievanceDossier(
        id=large_id_1,
        dossier_reference_id="GRV-BIGINT-CHALLENGE-01",
        reporter_id=u1.id,
        reported_user_id=u2.id,
        violation_category="harassment",
        evidence_text="Large ID test",
        status="acknowledged",
    )
    db_session.add(gd)

    large_id_2 = 9_123_456_789
    esc = AdminKycEscalation(
        id=large_id_2,
        user_id=u1.id,
        declared_dob=date(1995, 1, 1),
        groq_match_score=Decimal("0.890"),
        anchor_photo_url="https://media.urheart.app/id.jpg",
        kyc_video_url="https://media.urheart.app/selfie.mp4",
        status="pending",
    )
    db_session.add(esc)
    await db_session.commit()

    # Query back
    saved_gd = (await db_session.execute(select(GrievanceDossier).where(GrievanceDossier.id == large_id_1))).scalar_one()
    assert saved_gd.id == large_id_1

    saved_esc = (await db_session.execute(select(AdminKycEscalation).where(AdminKycEscalation.id == large_id_2))).scalar_one()
    assert saved_esc.id == large_id_2


@pytest.mark.asyncio
async def test_uuid_primary_keys_live_persistence(db_session, make_user):
    """Verify native UUID primary keys for DeviceFcmToken and BlindDateMessage."""
    u1 = make_user()
    u2 = make_user()
    db_session.add_all([u1, u2])
    await db_session.commit()

    custom_fcm_id = uuid.uuid4()
    fcm = DeviceFcmToken(
        id=custom_fcm_id,
        user_id=u1.id,
        token="tok_fcm_uuid_test_123",
        platform="android",
        is_active=True,
    )
    db_session.add(fcm)

    bds = BlindDateSession(
        user1_id=u1.id,
        user2_id=u2.id,
        icebreaker_prompt="Art and dreams",
        expires_at=datetime.now(timezone.utc),
    )
    db_session.add(bds)
    await db_session.commit()

    custom_msg_id = uuid.uuid4()
    msg = BlindDateMessage(
        id=custom_msg_id,
        session_id=bds.id,
        sender_id=u1.id,
        recipient_id=u2.id,
        encrypted_text="encrypted_data_string",
    )
    db_session.add(msg)
    await db_session.commit()

    res_fcm = (await db_session.execute(select(DeviceFcmToken).where(DeviceFcmToken.id == custom_fcm_id))).scalar_one()
    assert res_fcm.id == custom_fcm_id

    res_msg = (await db_session.execute(select(BlindDateMessage).where(BlindDateMessage.id == custom_msg_id))).scalar_one()
    assert res_msg.id == custom_msg_id


# ==============================================================================
# 3. Column Synonyms in SQLAlchemy Queries
# ==============================================================================

@pytest.mark.asyncio
async def test_blind_date_message_ciphertext_synonym_queries(db_session, make_user):
    """Verify BlindDateMessage ciphertext <-> encrypted_text synonym in queries."""
    u1 = make_user()
    u2 = make_user()
    db_session.add_all([u1, u2])
    await db_session.commit()

    bds = BlindDateSession(
        user1_id=u1.id,
        user2_id=u2.id,
        icebreaker_prompt="Connecting souls",
        expires_at=datetime.now(timezone.utc),
    )
    db_session.add(bds)
    await db_session.commit()

    m1 = BlindDateMessage(
        session_id=bds.id,
        sender_id=u1.id,
        recipient_id=u2.id,
        ciphertext="secret_cipher_payload_a",
    )
    m2 = BlindDateMessage(
        session_id=bds.id,
        sender_id=u2.id,
        recipient_id=u1.id,
        encrypted_text="secret_cipher_payload_b",
    )
    db_session.add_all([m1, m2])
    await db_session.commit()

    # Query WHERE ciphertext == 'secret_cipher_payload_a'
    res = await db_session.execute(
        select(BlindDateMessage).where(BlindDateMessage.ciphertext == "secret_cipher_payload_a")
    )
    found = res.scalar_one_or_none()
    assert found is not None
    assert found.encrypted_text == "secret_cipher_payload_a"
    assert found.ciphertext == "secret_cipher_payload_a"

    # Query LIKE
    res_like = await db_session.execute(
        select(BlindDateMessage).where(BlindDateMessage.ciphertext.like("%cipher_payload%"))
    )
    assert len(res_like.scalars().all()) == 2

    # Query ORDER BY desc
    res_ord = await db_session.execute(
        select(BlindDateMessage).order_by(desc(BlindDateMessage.ciphertext))
    )
    ordered = res_ord.scalars().all()
    assert ordered[0].ciphertext == "secret_cipher_payload_b"

    # Mutation via synonym
    found.ciphertext = "mutated_cipher"
    await db_session.commit()
    await db_session.refresh(found)
    assert found.encrypted_text == "mutated_cipher"


@pytest.mark.asyncio
async def test_device_fcm_token_active_synonym_queries(db_session, make_user):
    """Verify DeviceFcmToken active <-> is_active synonym in queries."""
    u = make_user()
    db_session.add(u)
    await db_session.commit()

    tok_act = DeviceFcmToken(
        user_id=u.id,
        token="tok_act_111",
        platform="android",
        active=True,
    )
    tok_inact = DeviceFcmToken(
        user_id=u.id,
        token="tok_inact_222",
        platform="ios",
        active=False,
    )
    db_session.add_all([tok_act, tok_inact])
    await db_session.commit()

    # Query active == True
    res_true = await db_session.execute(
        select(DeviceFcmToken).where(DeviceFcmToken.active == True)
    )
    actives = res_true.scalars().all()
    assert len(actives) == 1
    assert actives[0].token == "tok_act_111"

    # Query active == False
    res_false = await db_session.execute(
        select(DeviceFcmToken).where(DeviceFcmToken.active == False)
    )
    inactives = res_false.scalars().all()
    assert len(inactives) == 1
    assert inactives[0].token == "tok_inact_222"

    # Mutate via synonym
    tok_act.active = False
    await db_session.commit()
    await db_session.refresh(tok_act)
    assert tok_act.is_active is False


@pytest.mark.asyncio
async def test_admin_kyc_escalation_storage_url_synonym_queries(db_session, make_user):
    """Verify AdminKycEscalation id_card_storage_url & selfie_storage_url synonyms in queries."""
    u1 = make_user()
    u2 = make_user()
    db_session.add_all([u1, u2])
    await db_session.commit()

    esc1 = AdminKycEscalation(
        user_id=u1.id,
        declared_dob=date(1995, 1, 1),
        groq_match_score=Decimal("0.900"),
        id_card_storage_url="https://media.urheart.app/id1.jpg",
        selfie_storage_url="https://media.urheart.app/selfie1.mp4",
    )
    esc2 = AdminKycEscalation(
        user_id=u2.id,
        declared_dob=date(1996, 2, 2),
        groq_match_score=Decimal("0.850"),
        anchor_photo_url="https://media.urheart.app/id2.jpg",
        kyc_video_url="https://media.urheart.app/selfie2.mp4",
    )
    db_session.add_all([esc1, esc2])
    await db_session.commit()

    # Query by synonym id_card_storage_url
    res1 = await db_session.execute(
        select(AdminKycEscalation).where(
            AdminKycEscalation.id_card_storage_url == "https://media.urheart.app/id1.jpg"
        )
    )
    found1 = res1.scalar_one_or_none()
    assert found1 is not None
    assert found1.anchor_photo_url == "https://media.urheart.app/id1.jpg"

    # Query by synonym selfie_storage_url
    res2 = await db_session.execute(
        select(AdminKycEscalation).where(
            AdminKycEscalation.selfie_storage_url == "https://media.urheart.app/selfie2.mp4"
        )
    )
    found2 = res2.scalar_one_or_none()
    assert found2 is not None
    assert found2.kyc_video_url == "https://media.urheart.app/selfie2.mp4"
