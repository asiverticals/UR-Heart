"""
Milestone 2 Adversarial Verification Suite.

Adversarially tests:
1. All 22 ad reward types in AdRewardLedger (both against migration DDL and SQLAlchemy model)
   and tests valid vs invalid ad types.
2. GrievanceDossier check constraint with all 6 valid statuses and illegal string rejection.
3. AdminService.decide_escalation with numeric string IDs, non-numeric strings, valid UUIDs,
   and malformed inputs.
"""

import uuid
from datetime import datetime, timezone, date
from decimal import Decimal
import pytest
from sqlalchemy import select, inspect
from sqlalchemy.exc import IntegrityError

from backend.app.models.domain import (
    Base,
    User,
    AdRewardLedger,
    GrievanceDossier,
    AdminKycEscalation,
)
from backend.app.services.admin_service import AdminService
from backend.app.core.exceptions import SanctuaryException


# ==============================================================================
# Challenge 1: 22 Ad Reward Types in AdRewardLedger & Store Catalog / Service Parity
# ==============================================================================

ALL_22_AD_TYPES = [
    # Emitted by ad_ssv_service.py
    "quick_reflection",
    "deep_resonance",
    "sacred_bridge_reveal",
    "whatsapp_reveal",
    "morning_harvest_unlock",
    "daily_streak_boost",
    "rewarded_daily_boost",
    # Monetization model & claim endpoints
    "rewarded_reveal",
    "rewarded_extra_swipes",
    "rewarded_streak_freeze",
    "rewarded_blind_date_extend",
    "extra_swipes",
    # Rewarded catalog & perk boosts
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

INVALID_AD_TYPES = [
    "free_coins",
    "hacked_unlimited_swipes",
    "bitcoin_reward",
    "unknown_video_ad",
    "",
    "   ",
    "QUICK_REFLECTION",  # Case sensitivity
    "null",
]


@pytest.mark.asyncio
async def test_ad_reward_ledger_per_type_breakdown(db_session, make_user):
    """AdRewardLedger must accept all 22 legitimate ad reward types individually."""
    user = make_user()
    db_session.add(user)
    await db_session.commit()
    user_id = user.id

    passed = []
    failed = []
    for idx, ad_type in enumerate(ALL_22_AD_TYPES):
        async with db_session.begin_nested():
            ledger = AdRewardLedger(
                user_id=user_id,
                ssv_transaction_id=f"tx_type_{idx}_{ad_type}",
                network="admob",
                ad_type=ad_type,
                reward_points=10,
            )
            db_session.add(ledger)
            try:
                await db_session.flush()
                passed.append(ad_type)
            except IntegrityError:
                failed.append(ad_type)

    print(f"\nALL 22 AD TYPES TEST RESULTS:")
    print(f"PASSED ({len(passed)}): {passed}")
    print(f"FAILED ({len(failed)}): {failed}")
    assert len(failed) == 0, f"AdRewardLedger check constraint failed on {len(failed)} types: {failed}"


@pytest.mark.asyncio
async def test_ad_reward_ledger_rejects_invalid_ad_types(db_session, make_user):
    """AdRewardLedger must reject invalid ad types violating check constraint."""
    user = make_user()
    db_session.add(user)
    await db_session.commit()
    user_id = user.id

    for idx, invalid_type in enumerate(INVALID_AD_TYPES):
        async with db_session.begin_nested():
            ledger = AdRewardLedger(
                user_id=user_id,
                ssv_transaction_id=f"tx_invalid_{idx}_{uuid.uuid4().hex[:6]}",
                network="admob",
                ad_type=invalid_type,
                reward_points=10,
            )
            db_session.add(ledger)
            with pytest.raises(IntegrityError):
                await db_session.flush()


# ==============================================================================
# Challenge 2: GrievanceDossier Status Check Constraint & Rejections
# ==============================================================================

VALID_GRIEVANCE_STATUSES = [
    "under_review",
    "actioned",
    "dismissed",
    "acknowledged",
    "investigating",
    "closed",
]

ILLEGAL_GRIEVANCE_STATUSES = [
    "pending",          # old/invalid status
    "in_progress",
    "open",
    "resolved",         # should be actioned or closed
    "deleted",
    "REJECTED",
    "",
    "   ",
    "unknown_status",
]


@pytest.mark.asyncio
async def test_grievance_dossier_accepts_all_6_statuses(db_session, make_user):
    """GrievanceDossier must persist all 6 valid statuses."""
    reporter = make_user()
    reported = make_user()
    db_session.add_all([reporter, reported])
    await db_session.commit()
    rep_id, repd_id = reporter.id, reported.id

    for idx, status in enumerate(VALID_GRIEVANCE_STATUSES):
        dossier = GrievanceDossier(
            dossier_reference_id=f"GRV-ADV-{idx:04d}",
            reporter_id=rep_id,
            reported_user_id=repd_id,
            violation_category="harassment",
            evidence_text=f"Evidence text for status {status}",
            status=status,
        )
        db_session.add(dossier)

    await db_session.commit()

    result = await db_session.execute(
        select(GrievanceDossier).where(
            GrievanceDossier.dossier_reference_id.like("GRV-ADV-%")
        )
    )
    dossiers = result.scalars().all()
    assert len(dossiers) == 6
    assert {d.status for d in dossiers} == set(VALID_GRIEVANCE_STATUSES)


@pytest.mark.asyncio
async def test_grievance_dossier_rejects_illegal_statuses(db_session, make_user):
    """GrievanceDossier must reject any status not in the 6 canonical statuses."""
    reporter = make_user()
    reported = make_user()
    db_session.add_all([reporter, reported])
    await db_session.commit()
    rep_id, repd_id = reporter.id, reported.id

    for idx, illegal_status in enumerate(ILLEGAL_GRIEVANCE_STATUSES):
        async with db_session.begin_nested():
            dossier = GrievanceDossier(
                dossier_reference_id=f"GRV-BAD-{idx:04d}",
                reporter_id=rep_id,
                reported_user_id=repd_id,
                violation_category="harassment",
                evidence_text="Testing illegal status",
                status=illegal_status,
            )
            db_session.add(dossier)
            with pytest.raises(IntegrityError):
                await db_session.flush()


# ==============================================================================
# Challenge 3: AdminService.decide_escalation Type Safety
# ==============================================================================

@pytest.mark.asyncio
async def test_admin_service_decide_escalation_numeric_string(db_session, make_user):
    """decide_escalation with numeric string ID successfully adjudicates."""
    reviewer = make_user()
    candidate = make_user()
    db_session.add_all([reviewer, candidate])
    await db_session.commit()

    escalation = AdminKycEscalation(
        user_id=candidate.id,
        declared_dob=date(2000, 1, 1),
        groq_match_score=Decimal("0.900"),
        anchor_photo_url="https://media.urheart.app/id.jpg",
        kyc_video_url="https://media.urheart.app/selfie.mp4",
        status="pending",
    )
    db_session.add(escalation)
    await db_session.commit()
    await db_session.refresh(escalation)

    numeric_id_str = str(escalation.id)
    assert numeric_id_str.isdigit()

    service = AdminService()
    resp = await service.decide_escalation(
        session=db_session,
        escalation_id=numeric_id_str,
        decision="approve",
        reviewer=reviewer,
    )
    assert resp.success is True
    assert resp.status == "approved"

    await db_session.refresh(escalation)
    assert escalation.status == "approved"
    await db_session.refresh(candidate)
    assert candidate.kyc_status is True


@pytest.mark.asyncio
async def test_admin_service_decide_escalation_candidate_uuid(db_session, make_user):
    """decide_escalation with candidate's UUID string successfully adjudicates."""
    reviewer = make_user()
    candidate = make_user()
    db_session.add_all([reviewer, candidate])
    await db_session.commit()

    escalation = AdminKycEscalation(
        user_id=candidate.id,
        declared_dob=date(2000, 1, 1),
        groq_match_score=Decimal("0.900"),
        anchor_photo_url="https://media.urheart.app/id.jpg",
        kyc_video_url="https://media.urheart.app/selfie.mp4",
        status="pending",
    )
    db_session.add(escalation)
    await db_session.commit()

    service = AdminService()
    resp = await service.decide_escalation(
        session=db_session,
        escalation_id=str(candidate.id),
        decision="reject",
        reviewer=reviewer,
    )
    assert resp.success is True
    assert resp.status == "rejected"

    await db_session.refresh(escalation)
    assert escalation.status == "rejected"
    await db_session.refresh(candidate)
    assert candidate.kyc_status is False


@pytest.mark.asyncio
async def test_admin_service_decide_escalation_non_numeric_non_uuid_strings(db_session, make_user):
    """decide_escalation with non-numeric, non-UUID strings raises 404 ESCALATION_NOT_FOUND."""
    reviewer = make_user()
    db_session.add(reviewer)
    await db_session.commit()

    service = AdminService()

    invalid_ids = [
        "not_an_id",
        "abc-def-ghi",
        "123.456",
        "-999",
        "",
        "   ",
        "select * from admin_kyc_escalations",
        "undefined",
        "null",
        "0x1234",
    ]

    for bad_id in invalid_ids:
        with pytest.raises(SanctuaryException) as exc_info:
            await service.decide_escalation(
                session=db_session,
                escalation_id=bad_id,
                decision="approve",
                reviewer=reviewer,
            )
        assert exc_info.value.status_code == 404
        assert exc_info.value.error_code == "ESCALATION_NOT_FOUND"


@pytest.mark.asyncio
async def test_admin_service_decide_escalation_nonexistent_numeric_id(db_session, make_user):
    """decide_escalation with nonexistent numeric string raises 404 ESCALATION_NOT_FOUND."""
    reviewer = make_user()
    db_session.add(reviewer)
    await db_session.commit()

    service = AdminService()
    with pytest.raises(SanctuaryException) as exc_info:
        await service.decide_escalation(
            session=db_session,
            escalation_id="999999999",
            decision="approve",
            reviewer=reviewer,
        )
    assert exc_info.value.status_code == 404
    assert exc_info.value.error_code == "ESCALATION_NOT_FOUND"


@pytest.mark.asyncio
async def test_admin_service_decide_escalation_already_decided_conflict(db_session, make_user):
    """Adjudicating an already decided escalation raises 409 ESCALATION_ALREADY_DECIDED."""
    reviewer = make_user()
    candidate = make_user()
    db_session.add_all([reviewer, candidate])
    await db_session.commit()

    escalation = AdminKycEscalation(
        user_id=candidate.id,
        declared_dob=date(2000, 1, 1),
        groq_match_score=Decimal("0.900"),
        anchor_photo_url="https://media.urheart.app/id.jpg",
        kyc_video_url="https://media.urheart.app/selfie.mp4",
        status="approved",
    )
    db_session.add(escalation)
    await db_session.commit()
    await db_session.refresh(escalation)

    service = AdminService()
    with pytest.raises(SanctuaryException) as exc_info:
        await service.decide_escalation(
            session=db_session,
            escalation_id=str(escalation.id),
            decision="approve",
            reviewer=reviewer,
        )
    assert exc_info.value.status_code == 409
    assert exc_info.value.error_code == "ESCALATION_ALREADY_DECIDED"
