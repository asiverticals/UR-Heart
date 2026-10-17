"""
Adversarial Verification Suite: Challenger 2
Focus: Data Invariants, SLA Calculations, Audit Log Immutability & Coverage, Seeker Ban/Session Revocation.

Empirically tests:
1. Grievance status check constraints (DB-level IntegrityError & API-level 422 validation).
2. Grievance violation category and reporter!=reported check constraints.
3. SLA calculations across edge cases:
   - Negative remaining SLA (past/overdue deadlines)
   - Zero seconds remaining (exact deadline hit)
   - Future deadlines
   - Fallback to statutory_resolution_due_at
   - Null deadlines
   - Triage sorting order (breached/overdue tickets prioritized first)
   - Naive datetime edge case
4. Mandatory audit logging across ALL 6 mutating endpoints:
   - kyc decide (approve & reject)
   - grievance resolve
   - user toggle-ban (ban & unban)
   - quarantine release
   - grant-sparks
   - grant-pass
   - Client IP extraction & no phantom logs on 401/404/422
5. Seeker ban immediate account locking & JWT session revocation:
   - Token invalidation on ban
   - Invalidation persistence across unban (token_version increment invariant)
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.admin_portal import create_admin_session_token, SESSION_COOKIE_NAME
from backend.app.api.deps import get_current_user, get_db
from backend.app.core.config import settings
from backend.app.core.exceptions import SanctuaryException
from backend.app.core.security import create_access_token, create_refresh_token
from backend.app.main import app
from backend.app.models.domain.admin_telemetry import (
    AdminAuditLog,
    AdminKycEscalation,
)
from backend.app.models.domain.legal import (
    GrievanceDossier,
    UnderageQuarantineRegistry,
)
from backend.app.models.domain.user import User
from backend.app.services.auth_service import auth_service


@pytest.fixture
def auth_admin_cookies():
    """Generates valid authenticated superadmin session cookie."""
    token = create_admin_session_token("asiverticals@gmail.com")
    return {SESSION_COOKIE_NAME: token}


# ==============================================================================
# SECTION 1: Grievance Status & Invariant Check Constraints
# ==============================================================================

@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_status", [
    "resolved",       # Common synonym, NOT in check constraint
    "pending",        # Valid in KYC, but invalid in Grievance
    "invalid",        # Arbitrary junk
    "in_progress",    # Non-standard
    "",               # Empty string
    "ACTIONED",       # Case sensitivity violation
    "under_review; DROP TABLE grievance_dossiers; --", # Injection payload
])
async def test_db_check_constraint_grievance_status_rejects_invalid(db_session: AsyncSession, make_user, invalid_status):
    """DB check constraint `chk_grievance_status` must raise IntegrityError on invalid status."""
    reporter = make_user()
    db_session.add(reporter)
    await db_session.flush()

    dossier = GrievanceDossier(
        dossier_reference_id=f"TEST-INV-{uuid.uuid4().hex[:8]}",
        reporter_id=reporter.id,
        violation_category="harassment",
        evidence_text="Harassment evidence",
        status=invalid_status,
    )
    db_session.add(dossier)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
@pytest.mark.parametrize("valid_status", [
    "under_review",
    "actioned",
    "dismissed",
    "acknowledged",
    "investigating",
    "closed",
])
async def test_db_check_constraint_grievance_status_accepts_all_valid(db_session: AsyncSession, make_user, valid_status):
    """DB check constraint `chk_grievance_status` must succeed for all 6 statutory statuses."""
    reporter = make_user()
    db_session.add(reporter)
    await db_session.flush()

    dossier = GrievanceDossier(
        dossier_reference_id=f"TEST-VAL-{uuid.uuid4().hex[:8]}",
        reporter_id=reporter.id,
        violation_category="harassment",
        evidence_text="Harassment evidence",
        status=valid_status,
    )
    db_session.add(dossier)
    await db_session.commit()
    await db_session.refresh(dossier)
    assert dossier.status == valid_status


@pytest.mark.asyncio
async def test_db_check_constraint_grievance_category_invalid(db_session: AsyncSession, make_user):
    """DB check constraint `chk_grievance_category` must raise IntegrityError on unauthorized category."""
    reporter = make_user()
    db_session.add(reporter)
    await db_session.flush()

    dossier = GrievanceDossier(
        dossier_reference_id=f"TEST-CAT-{uuid.uuid4().hex[:8]}",
        reporter_id=reporter.id,
        violation_category="unauthorized_category_spam",
        evidence_text="Spam report",
        status="acknowledged",
    )
    db_session.add(dossier)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_db_check_constraint_grievance_same_reporter_reported(db_session: AsyncSession, make_user):
    """DB check constraint `chk_grievance_reporter_reported_diff` must prevent self-reporting."""
    user = make_user()
    db_session.add(user)
    await db_session.flush()

    dossier = GrievanceDossier(
        dossier_reference_id=f"TEST-SELF-{uuid.uuid4().hex[:8]}",
        reporter_id=user.id,
        reported_user_id=user.id,  # Identical IDs
        violation_category="harassment",
        evidence_text="Self report attempt",
        status="acknowledged",
    )
    db_session.add(dossier)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_status", ["resolved", "pending", "invalid", "", "COMPLETED"])
async def test_api_grievance_resolve_rejects_invalid_status_with_422(
    auth_admin_cookies, db_session: AsyncSession, make_user, invalid_status
):
    """Endpoint POST /admin/api/grievances/{id}/resolve must return HTTP 422 for invalid statuses."""
    reporter = make_user()
    db_session.add(reporter)
    await db_session.flush()

    dossier = GrievanceDossier(
        dossier_reference_id=f"TEST-API-{uuid.uuid4().hex[:8]}",
        reporter_id=reporter.id,
        violation_category="ncii",
        evidence_text="NCII evidence",
        status="under_review",
    )
    db_session.add(dossier)
    await db_session.commit()

    app.dependency_overrides[get_db] = lambda: db_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", cookies=auth_admin_cookies) as client:
        res = await client.post(
            f"/admin/api/grievances/{dossier.id}/resolve",
            json={"status": invalid_status, "resolution_summary": "Attempt invalid transition"},
        )
        assert res.status_code == 422

    # Verify DB was NOT mutated
    await db_session.refresh(dossier)
    assert dossier.status == "under_review"

    # Verify no spurious audit log was recorded
    stmt = select(AdminAuditLog).where(
        AdminAuditLog.target_id == str(dossier.id),
        AdminAuditLog.action == "resolve_grievance",
    )
    log = (await db_session.execute(stmt)).scalar_one_or_none()
    assert log is None


# ==============================================================================
# SECTION 2: SLA Deadline Calculations & Triage Ordering Edge Cases
# ==============================================================================

@pytest.mark.asyncio
async def test_sla_deadline_edge_cases_and_sorting(auth_admin_cookies, db_session: AsyncSession, make_user):
    """Tests remaining SLA calculations: past deadline (negative), zero seconds, future, fallback, and sorting."""
    now = datetime.now(timezone.utc)
    reporter = make_user()
    db_session.add(reporter)
    await db_session.flush()

    # Case 1: Past / Overdue SLA (Emergency NCII breached 3 hours ago)
    d_overdue = GrievanceDossier(
        dossier_reference_id="SLA-OVERDUE-01",
        reporter_id=reporter.id,
        violation_category="ncii",
        evidence_text="Overdue ticket",
        status="under_review",
        sla_deadline_at=now - timedelta(hours=3),
    )

    # Case 2: Zero seconds remaining (Deadline right now)
    d_zero = GrievanceDossier(
        dossier_reference_id="SLA-ZERO-02",
        reporter_id=reporter.id,
        violation_category="ncii",
        evidence_text="Zero seconds ticket",
        status="under_review",
        sla_deadline_at=now,
    )

    # Case 3: Future deadline (20 hours remaining)
    d_future = GrievanceDossier(
        dossier_reference_id="SLA-FUTURE-03",
        reporter_id=reporter.id,
        violation_category="explicit_content",
        evidence_text="Future ticket",
        status="under_review",
        sla_deadline_at=now + timedelta(hours=20),
    )

    # Case 4: No sla_deadline_at, but statutory_resolution_due_at present (15 days)
    d_fallback = GrievanceDossier(
        dossier_reference_id="SLA-FALLBACK-04",
        reporter_id=reporter.id,
        violation_category="other",
        evidence_text="Fallback ticket",
        status="acknowledged",
        sla_deadline_at=None,
        statutory_resolution_due_at=now + timedelta(days=15),
    )

    # Case 5: Both deadlines null
    d_none = GrievanceDossier(
        dossier_reference_id="SLA-NONE-05",
        reporter_id=reporter.id,
        violation_category="other",
        evidence_text="No deadline ticket",
        status="acknowledged",
        sla_deadline_at=None,
        statutory_resolution_due_at=None,
    )

    db_session.add_all([d_overdue, d_zero, d_future, d_fallback, d_none])
    await db_session.commit()

    app.dependency_overrides[get_db] = lambda: db_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", cookies=auth_admin_cookies) as client:
        res = await client.get("/admin/api/grievances?limit=50")
        assert res.status_code == 200
        items = res.json()

    item_map = {i["dossier_reference_id"]: i for i in items}

    # Verify Case 1: Negative seconds
    assert "SLA-OVERDUE-01" in item_map
    overdue_item = item_map["SLA-OVERDUE-01"]
    assert overdue_item["remaining_sla_seconds"] is not None
    assert overdue_item["remaining_sla_seconds"] < -10000  # -3 hours is approx -10800s

    # Verify Case 2: Near-zero seconds
    assert "SLA-ZERO-02" in item_map
    zero_item = item_map["SLA-ZERO-02"]
    assert zero_item["remaining_sla_seconds"] is not None
    assert abs(zero_item["remaining_sla_seconds"]) <= 10  # within a few seconds of execution

    # Verify Case 3: Positive seconds
    assert "SLA-FUTURE-03" in item_map
    future_item = item_map["SLA-FUTURE-03"]
    assert future_item["remaining_sla_seconds"] is not None
    assert future_item["remaining_sla_seconds"] > 70000  # 20 hours is 72000s

    # Verify Case 4: Fallback to statutory_resolution_due_at
    assert "SLA-FALLBACK-04" in item_map
    fallback_item = item_map["SLA-FALLBACK-04"]
    assert fallback_item["remaining_sla_seconds"] is not None
    assert fallback_item["remaining_sla_seconds"] > 1000000  # 15 days

    # Verify Case 5: Null deadlines
    assert "SLA-NONE-05" in item_map
    none_item = item_map["SLA-NONE-05"]
    assert none_item["remaining_sla_seconds"] is None

    # Verify Triage Sorting Order:
    # Most overdue ticket (SLA-OVERDUE-01) must appear before near-due and future tickets
    relevant_ids = [i["dossier_reference_id"] for i in items if i["dossier_reference_id"].startswith("SLA-")]
    # Priority order with non-null sla_deadline_at ascending: OVERDUE, then ZERO, then FUTURE
    overdue_idx = relevant_ids.index("SLA-OVERDUE-01")
    zero_idx = relevant_ids.index("SLA-ZERO-02")
    future_idx = relevant_ids.index("SLA-FUTURE-03")
    fallback_idx = relevant_ids.index("SLA-FALLBACK-04")
    none_idx = relevant_ids.index("SLA-NONE-05")

    assert overdue_idx < zero_idx < future_idx, "Tickets with sla_deadline_at must be sorted ascending (breached first)"
    assert future_idx < fallback_idx or future_idx < none_idx, "Tickets with sla_deadline_at must appear before null sla_deadline_at"


# ==============================================================================
# SECTION 3: Mandatory Audit Logging Across ALL Mutating Endpoints
# ==============================================================================

@pytest.mark.asyncio
async def test_audit_logging_kyc_approve_and_reject(auth_admin_cookies, db_session: AsyncSession, make_user):
    """Mutating endpoints POST /admin/api/kyc/{id}/decide must write to admin_audit_logs for both approve & reject."""
    app.dependency_overrides[get_db] = lambda: db_session
    transport = httpx.ASGITransport(app=app)

    # 1. Test KYC Approve
    user1 = make_user(full_name="Seeker One", kyc_status=False)
    db_session.add(user1)
    await db_session.flush()

    esc1 = AdminKycEscalation(
        user_id=user1.id,
        declared_dob=date(1999, 1, 1),
        declared_age=27,
        groq_match_score=Decimal("0.750"),
        anchor_photo_url="users/1/anchor.webp",
        kyc_video_url="kyc/1/selfie.webp",
        status="pending",
    )
    db_session.add(esc1)
    await db_session.commit()

    async with httpx.AsyncClient(transport=transport, base_url="http://test", cookies=auth_admin_cookies) as client:
        res1 = await client.post(
            f"/admin/api/kyc/{esc1.id}/decide",
            json={"decision": "approve", "notes": "Human verified photo."},
            headers={"X-Forwarded-For": "198.51.100.10"},
        )
        assert res1.status_code == 200

    stmt1 = select(AdminAuditLog).where(
        AdminAuditLog.action == "kyc_approve",
        AdminAuditLog.target_id == str(esc1.id),
    )
    log1 = (await db_session.execute(stmt1)).scalar_one_or_none()
    assert log1 is not None
    assert log1.admin_email == "asiverticals@gmail.com"
    assert log1.target_type == "kyc_escalation"
    assert log1.ip_address in ("198.51.100.10", "127.0.0.1")
    assert log1.details["decision"] == "approve"

    # 2. Test KYC Reject
    user2 = make_user(full_name="Seeker Two", kyc_status=False)
    db_session.add(user2)
    await db_session.flush()

    esc2 = AdminKycEscalation(
        user_id=user2.id,
        declared_dob=date(2005, 1, 1),
        declared_age=21,
        groq_match_score=Decimal("0.200"),
        anchor_photo_url="users/2/anchor.webp",
        kyc_video_url="kyc/2/selfie.webp",
        status="pending",
    )
    db_session.add(esc2)
    await db_session.commit()

    async with httpx.AsyncClient(transport=transport, base_url="http://test", cookies=auth_admin_cookies) as client:
        res2 = await client.post(
            f"/admin/api/kyc/{esc2.id}/decide",
            json={"decision": "reject", "notes": "Deepfake spoof detected."},
            headers={"X-Forwarded-For": "198.51.100.20"},
        )
        assert res2.status_code == 200

    stmt2 = select(AdminAuditLog).where(
        AdminAuditLog.action == "kyc_reject",
        AdminAuditLog.target_id == str(esc2.id),
    )
    log2 = (await db_session.execute(stmt2)).scalar_one_or_none()
    assert log2 is not None
    assert log2.admin_email == "asiverticals@gmail.com"
    assert log2.ip_address in ("198.51.100.20", "127.0.0.1")
    assert log2.details["decision"] == "reject"


@pytest.mark.asyncio
async def test_audit_logging_grievance_resolve(auth_admin_cookies, db_session: AsyncSession, make_user):
    """Mutating endpoint POST /admin/api/grievances/{id}/resolve must write to admin_audit_logs."""
    reporter = make_user()
    db_session.add(reporter)
    await db_session.flush()

    dossier = GrievanceDossier(
        dossier_reference_id=f"AUDIT-GRV-{uuid.uuid4().hex[:8]}",
        reporter_id=reporter.id,
        violation_category="explicit_content",
        evidence_text="Explicit image share",
        status="investigating",
    )
    db_session.add(dossier)
    await db_session.commit()

    app.dependency_overrides[get_db] = lambda: db_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", cookies=auth_admin_cookies) as client:
        res = await client.post(
            f"/admin/api/grievances/{dossier.id}/resolve",
            json={"status": "closed", "resolution_summary": "Handled according to safety standard."},
            headers={"X-Forwarded-For": "203.0.113.50"},
        )
        assert res.status_code == 200

    stmt = select(AdminAuditLog).where(
        AdminAuditLog.action == "resolve_grievance",
        AdminAuditLog.target_id == str(dossier.id),
    )
    log = (await db_session.execute(stmt)).scalar_one_or_none()
    assert log is not None
    assert log.admin_email == "asiverticals@gmail.com"
    assert log.target_type == "grievance"
    assert log.ip_address == "203.0.113.50"
    assert log.details["status"] == "closed"


@pytest.mark.asyncio
async def test_audit_logging_user_toggle_ban_both_directions(auth_admin_cookies, db_session: AsyncSession, make_user):
    """Mutating endpoint POST /admin/api/users/{id}/toggle-ban must write user_banned and user_unbanned."""
    user = make_user(full_name="Target User")
    db_session.add(user)
    await db_session.commit()

    app.dependency_overrides[get_db] = lambda: db_session
    transport = httpx.ASGITransport(app=app)

    # 1. Ban
    async with httpx.AsyncClient(transport=transport, base_url="http://test", cookies=auth_admin_cookies) as client:
        res_ban = await client.post(
            f"/admin/api/users/{user.id}/toggle-ban",
            json={"reason": "Policy violations observed."},
            headers={"X-Forwarded-For": "192.0.2.11"},
        )
        assert res_ban.status_code == 200

    stmt_ban = select(AdminAuditLog).where(
        AdminAuditLog.action == "user_banned",
        AdminAuditLog.target_id == str(user.id),
    )
    log_ban = (await db_session.execute(stmt_ban)).scalar_one_or_none()
    assert log_ban is not None
    assert log_ban.admin_email == "asiverticals@gmail.com"
    assert log_ban.ip_address == "192.0.2.11"
    assert log_ban.details["is_banned"] is True

    # 2. Unban
    async with httpx.AsyncClient(transport=transport, base_url="http://test", cookies=auth_admin_cookies) as client:
        res_unban = await client.post(
            f"/admin/api/users/{user.id}/toggle-ban",
            json={"reason": "Appeal validated and approved."},
            headers={"X-Forwarded-For": "192.0.2.22"},
        )
        assert res_unban.status_code == 200

    stmt_unban = select(AdminAuditLog).where(
        AdminAuditLog.action == "user_unbanned",
        AdminAuditLog.target_id == str(user.id),
    )
    log_unban = (await db_session.execute(stmt_unban)).scalar_one_or_none()
    assert log_unban is not None
    assert log_unban.admin_email == "asiverticals@gmail.com"
    assert log_unban.ip_address == "192.0.2.22"
    assert log_unban.details["is_banned"] is False


@pytest.mark.asyncio
async def test_audit_logging_quarantine_release(auth_admin_cookies, db_session: AsyncSession):
    """Mutating endpoint POST /admin/api/quarantine/{id}/release must write to admin_audit_logs."""
    now = datetime.now(timezone.utc)
    record = UnderageQuarantineRegistry(
        device_hash="device_fingerprint_to_release",
        attempted_dob=date(2012, 1, 1),
        quarantine_until=now + timedelta(days=90),
    )
    db_session.add(record)
    await db_session.commit()

    app.dependency_overrides[get_db] = lambda: db_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", cookies=auth_admin_cookies) as client:
        res = await client.post(
            f"/admin/api/quarantine/{record.id}/release",
            json={"reason": "Appeal verified with government ID."},
            headers={"X-Forwarded-For": "198.51.100.99"},
        )
        assert res.status_code == 200

    stmt = select(AdminAuditLog).where(
        AdminAuditLog.action == "release_quarantine",
        AdminAuditLog.target_id == str(record.id),
    )
    log = (await db_session.execute(stmt)).scalar_one_or_none()
    assert log is not None
    assert log.admin_email == "asiverticals@gmail.com"
    assert log.target_type == "underage_quarantine"
    assert log.ip_address == "198.51.100.99"


@pytest.mark.asyncio
async def test_audit_logging_grant_sparks(auth_admin_cookies, db_session: AsyncSession, make_user):
    """Mutating endpoint POST /admin/api/users/{id}/grant-sparks must write to admin_audit_logs with accurate delta."""
    user = make_user(reward_balance=25)
    db_session.add(user)
    await db_session.commit()

    app.dependency_overrides[get_db] = lambda: db_session
    transport = httpx.ASGITransport(app=app)

    # 1. Positive grant (+50)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", cookies=auth_admin_cookies) as client:
        res = await client.post(
            f"/admin/api/users/{user.id}/grant-sparks",
            json={"sparks_amount": 50, "reason": "Customer loyalty bonus"},
            headers={"X-Forwarded-For": "10.0.0.1"},
        )
        assert res.status_code == 200

    stmt = select(AdminAuditLog).where(
        AdminAuditLog.action == "grant_sparks",
        AdminAuditLog.target_id == str(user.id),
    )
    log = (await db_session.execute(stmt)).scalar_one_or_none()
    assert log is not None
    assert log.details["delta"] == 50
    assert log.details["previous_balance"] == 25
    assert log.details["new_balance"] == 75

    # 2. Debit / negative grant (-100, clamped to 0)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", cookies=auth_admin_cookies) as client:
        res_debit = await client.post(
            f"/admin/api/users/{user.id}/grant-sparks",
            json={"sparks_amount": -100, "reason": "Chargeback reversal"},
        )
        assert res_debit.status_code == 200
        assert res_debit.json()["reward_balance"] == 0


@pytest.mark.asyncio
async def test_audit_logging_grant_pass(auth_admin_cookies, db_session: AsyncSession, make_user):
    """Mutating endpoint POST /admin/api/users/{id}/grant-pass must write to admin_audit_logs."""
    user = make_user(subscription_tier="free")
    db_session.add(user)
    await db_session.commit()

    app.dependency_overrides[get_db] = lambda: db_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", cookies=auth_admin_cookies) as client:
        res = await client.post(
            f"/admin/api/users/{user.id}/grant-pass",
            json={"sku": "pass_weekly", "reason": "Recovery of interrupted payment"},
            headers={"X-Forwarded-For": "10.0.0.2"},
        )
        assert res.status_code == 200

    stmt = select(AdminAuditLog).where(
        AdminAuditLog.action == "grant_pass",
        AdminAuditLog.target_id == str(user.id),
    )
    log = (await db_session.execute(stmt)).scalar_one_or_none()
    assert log is not None
    assert log.admin_email == "asiverticals@gmail.com"
    assert log.details["sku"] == "pass_weekly"


@pytest.mark.asyncio
async def test_audit_log_not_written_for_unauthenticated_or_failed_mutations(db_session: AsyncSession, make_user):
    """Mutating endpoints must NOT create audit logs when requests fail authentication or validation."""
    user = make_user()
    db_session.add(user)
    await db_session.commit()

    app.dependency_overrides[get_db] = lambda: db_session
    transport = httpx.ASGITransport(app=app)

    # 1. Unauthenticated request to toggle-ban -> 401
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            f"/admin/api/users/{user.id}/toggle-ban",
            json={"reason": "Unauthorized attempt"},
        )
        assert res.status_code == 401

    # Ensure no audit log was created for user
    stmt = select(AdminAuditLog).where(AdminAuditLog.target_id == str(user.id))
    log = (await db_session.execute(stmt)).scalar_one_or_none()
    assert log is None

    # 2. Nonexistent user grant-sparks with auth -> 404
    token = create_admin_session_token("asiverticals@gmail.com")
    cookies = {SESSION_COOKIE_NAME: token}
    fake_uuid = uuid.uuid4()
    async with httpx.AsyncClient(transport=transport, base_url="http://test", cookies=cookies) as client:
        res_404 = await client.post(
            f"/admin/api/users/{fake_uuid}/grant-sparks",
            json={"sparks_amount": 100, "reason": "Should fail with 404"},
        )
        assert res_404.status_code == 404

    stmt_404 = select(AdminAuditLog).where(AdminAuditLog.target_id == str(fake_uuid))
    assert (await db_session.execute(stmt_404)).scalar_one_or_none() is None


# ==============================================================================
# SECTION 4: Seeker Ban Account Locking & JWT Session Revocation
# ==============================================================================

@pytest.mark.asyncio
async def test_seeker_ban_locks_account_and_revokes_sessions(auth_admin_cookies, db_session: AsyncSession, make_user):
    """
    Adversarial session test:
    1. Active user with token_version=1 can authenticate.
    2. Admin bans user via /admin/api/users/{id}/toggle-ban:
       - user.deleted_at is set (account locked)
       - user.token_version is incremented to 2
       - existing access token is immediately rejected with 401 (account inactive / soft-deleted)
       - existing refresh token is immediately rejected with 401
    3. Admin unbans user:
       - user.deleted_at is set to None
       - user.token_version remains 2
       - pre-ban access token with token_version=1 remains permanently REVOKED (TOKEN_REVOKED 401)
       - pre-ban refresh token remains permanently REVOKED
       - freshly signed-in token with token_version=2 works normally.
    """
    app.dependency_overrides[get_db] = lambda: db_session

    # Step 1: Create active user with initial token_version=1
    user = make_user(
        full_name="Vulnerable Seeker",
        email="vulnerable@urheart.app",
        token_version=1,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Issue access and refresh tokens at token_version=1
    pre_ban_access_token = create_access_token(subject=user.id, token_version=1)
    pre_ban_refresh_token = create_refresh_token(subject=user.id, token_version=1)

    transport = httpx.ASGITransport(app=app)

    # Verify user can access authenticated endpoint
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res_me_before = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {pre_ban_access_token}"},
        )
        assert res_me_before.status_code == 200
        assert res_me_before.json()["data"]["email"] == "vulnerable@urheart.app"

    # Step 2: Superadmin bans seeker
    async with httpx.AsyncClient(transport=transport, base_url="http://test", cookies=auth_admin_cookies) as client:
        res_ban = await client.post(
            f"/admin/api/users/{user.id}/toggle-ban",
            json={"reason": "Safety violations"},
        )
        assert res_ban.status_code == 200
        ban_payload = res_ban.json()
        assert ban_payload["is_banned"] is True
        assert ban_payload["token_version"] == 2

    await db_session.refresh(user)
    assert user.deleted_at is not None
    assert user.token_version == 2

    # Step 3: Verify banned user cannot access protected endpoint
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res_me_banned = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {pre_ban_access_token}"},
        )
        assert res_me_banned.status_code == 401
        assert res_me_banned.json()["error_code"] == "USER_NOT_FOUND"

    # Step 4: Verify banned user cannot refresh token (denied with 404 SEEKER_NOT_FOUND or 401)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res_refresh_banned = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": pre_ban_refresh_token},
        )
        assert res_refresh_banned.status_code in (401, 404)
        assert res_refresh_banned.json().get("error_code") in ("SEEKER_NOT_FOUND", "TOKEN_REVOKED", "INVALID_REFRESH_TOKEN")

    # Step 5: Superadmin unbans seeker
    async with httpx.AsyncClient(transport=transport, base_url="http://test", cookies=auth_admin_cookies) as client:
        res_unban = await client.post(
            f"/admin/api/users/{user.id}/toggle-ban",
            json={"reason": "Grievance resolved; account restored"},
        )
        assert res_unban.status_code == 200
        assert res_unban.json()["is_banned"] is False

    await db_session.refresh(user)
    assert user.deleted_at is None
    # Crucial security invariant: token_version must still be 2 (not rolled back to 1)
    assert user.token_version == 2

    # Step 6: Verify pre-ban access token is STILL REVOKED (token_version 1 < user.token_version 2)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res_me_old_token = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {pre_ban_access_token}"},
        )
        assert res_me_old_token.status_code == 401
        assert res_me_old_token.json()["error_code"] == "TOKEN_REVOKED"

    # Step 7: Verify pre-ban refresh token is STILL REVOKED
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res_refresh_old = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": pre_ban_refresh_token},
        )
        assert res_refresh_old.status_code == 401
        assert res_refresh_old.json()["error_code"] == "INVALID_REFRESH_TOKEN"

    # Step 8: Verify a freshly issued token with current token_version=2 works seamlessly
    new_access_token = create_access_token(subject=user.id, token_version=user.token_version)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res_me_fresh = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {new_access_token}"},
        )
        assert res_me_fresh.status_code == 200
        assert res_me_fresh.json()["data"]["email"] == "vulnerable@urheart.app"


@pytest.mark.asyncio
async def test_kyc_audit_log_captures_client_ip(auth_admin_cookies, db_session: AsyncSession, make_user):
    """Adversarial bug probe: KYC decisions must capture actual client IP rather than hardcoding 127.0.0.1."""
    user = make_user()
    db_session.add(user)
    await db_session.flush()

    esc = AdminKycEscalation(
        user_id=user.id,
        declared_dob=date(2000, 1, 1),
        declared_age=26,
        groq_match_score=Decimal("0.850"),
        anchor_photo_url="users/test/anchor.webp",
        kyc_video_url="kyc/test/video.webp",
        status="pending",
    )
    db_session.add(esc)
    await db_session.commit()

    app.dependency_overrides[get_db] = lambda: db_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", cookies=auth_admin_cookies) as client:
        res = await client.post(
            f"/admin/api/kyc/{esc.id}/decide",
            json={"decision": "approve", "notes": "Verified"},
            headers={"X-Forwarded-For": "203.0.113.199"},
        )
        assert res.status_code == 200

    stmt = select(AdminAuditLog).where(AdminAuditLog.target_id == str(esc.id))
    log = (await db_session.execute(stmt)).scalar_one_or_none()
    assert log is not None
    # This assertion fails because admin_service.py hardcodes '127.0.0.1'
    assert log.ip_address == "203.0.113.199"


@pytest.mark.asyncio
async def test_grievance_sla_naive_datetime_handling(auth_admin_cookies, db_session: AsyncSession, make_user):
    """Stress test: evaluate how GET /admin/api/grievances handles naive datetimes in SQLite/DB."""
    reporter = make_user()
    db_session.add(reporter)
    await db_session.flush()

    # Create dossier with naive datetime (no tzinfo)
    naive_dt = datetime.now() + timedelta(hours=10)
    dossier = GrievanceDossier(
        dossier_reference_id="SLA-NAIVE-TEST",
        reporter_id=reporter.id,
        violation_category="ncii",
        evidence_text="Naive datetime ticket",
        status="under_review",
        sla_deadline_at=naive_dt,
    )
    db_session.add(dossier)
    await db_session.commit()

    app.dependency_overrides[get_db] = lambda: db_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", cookies=auth_admin_cookies) as client:
        res = await client.get("/admin/api/grievances?limit=10")
        assert res.status_code == 200
        items = res.json()
        assert any(i["dossier_reference_id"] == "SLA-NAIVE-TEST" for i in items)


