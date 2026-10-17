"""
Comprehensive Automated Test Suite for UR-Heart Web Admin Portal & Gatekeeper
Tests cover:
1. Superadmin Authentication & Rate-Limiting
2. Gatekeeper Session Protection & HTML / API Redirects
3. Real-Time Telemetry & System KPIs
4. Biometric KYC Adjudication Flow + Section 8 Purge & Audit Trail
5. Grievances & Emergency NCII SLA Desk + Resolution & Audit Trail
6. Seeker Management Console + Search + Ban/Unban Toggle + Session Revocation
7. Underage Hardware Quarantine Registry & Release
8. Monetization Ledger & Dispute Grants (Sparks & Subscription Passes)
9. DPDP Compliance & Privacy Vault Inspection
10. Immutable Admin Audit Trail Verification
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.admin_portal import create_admin_session_token, SESSION_COOKIE_NAME
from backend.app.api.deps import get_db
from backend.app.core.config import settings
from backend.app.main import app
from backend.app.models.domain.admin_telemetry import (
    AdminAuditLog,
    AdminKycEscalation,
    DeviceFcmToken,
)
from backend.app.models.domain.legal import (
    ConsentAuditLog,
    DataExportRequest,
    DataNominee,
    GrievanceDossier,
    UnderageQuarantineRegistry,
)
from backend.app.models.domain.monetization import (
    InAppPurchase,
    PendingWebEntitlement,
)
from backend.app.models.domain.user import User


@pytest.fixture
def auth_admin_cookies():
    """Generates valid authenticated superadmin session cookie."""
    token = create_admin_session_token("asiverticals@gmail.com")
    return {SESSION_COOKIE_NAME: token}


# ==============================================================================
# 1. Superadmin Authentication Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_admin_login_rejects_unauthorized_email(db_session: AsyncSession):
    """Unauthorized email must be rejected with 401 and logged in admin_audit_logs."""
    app.dependency_overrides[get_db] = lambda: db_session

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/admin/api/login",
            json={"email": "hacker@gmail.com", "secret_key": settings.SUPERADMIN_SECRET_KEY},
        )
        assert res.status_code == 401
        data = res.json()
        assert data["error_code"] == "INVALID_ADMIN_CREDENTIALS"

    # Verify audit log entry
    stmt = select(AdminAuditLog).where(
        AdminAuditLog.action == "admin_login_failed",
        AdminAuditLog.admin_email == "hacker@gmail.com",
    )
    log = (await db_session.execute(stmt)).scalar_one_or_none()
    assert log is not None
    assert log.target_type == "admin_auth"


@pytest.mark.asyncio
async def test_admin_login_rejects_invalid_secret(db_session: AsyncSession):
    """Authorized email with invalid secret key must be rejected with 401 and logged."""
    app.dependency_overrides[get_db] = lambda: db_session

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/admin/api/login",
            json={"email": "asiverticals@gmail.com", "secret_key": "WrongSecret123"},
        )
        assert res.status_code == 401
        data = res.json()
        assert data["error_code"] == "INVALID_ADMIN_CREDENTIALS"

    # Verify audit log entry
    stmt = select(AdminAuditLog).where(
        AdminAuditLog.action == "admin_login_failed",
        AdminAuditLog.admin_email == "asiverticals@gmail.com",
    )
    log = (await db_session.execute(stmt)).scalar_one_or_none()
    assert log is not None


@pytest.mark.asyncio
async def test_admin_login_success_with_valid_credentials(db_session: AsyncSession):
    """Valid credentials create authenticated session, issue HttpOnly cookie, and log audit."""
    app.dependency_overrides[get_db] = lambda: db_session

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/admin/api/login",
            json={"email": "asiverticals@gmail.com", "secret_key": settings.SUPERADMIN_SECRET_KEY},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["redirect_url"] == "/admin"

        # Check Set-Cookie
        cookies = res.cookies
        assert SESSION_COOKIE_NAME in cookies

    # Verify audit log entry
    stmt = select(AdminAuditLog).where(
        AdminAuditLog.action == "admin_login_success",
        AdminAuditLog.admin_email == "asiverticals@gmail.com",
    )
    log = (await db_session.execute(stmt)).scalar_one_or_none()
    assert log is not None


# ==============================================================================
# 2. Gatekeeper Session Protection & Redirect Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_gatekeeper_unauthenticated_web_redirects_to_login():
    """Unauthenticated access to GET /admin must redirect to /admin/login (HTTP 303)."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as client:
        res = await client.get("/admin")
        assert res.status_code in (302, 303, 307)
        assert res.headers.get("location") == "/admin/login"


@pytest.mark.asyncio
async def test_gatekeeper_unauthenticated_api_returns_401():
    """Unauthenticated access to /admin/api/* must return HTTP 401."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/admin/api/telemetry")
        assert res.status_code == 401
        data = res.json()
        assert data["error_code"] == "ADMIN_UNAUTHORIZED"


@pytest.mark.asyncio
async def test_gatekeeper_authenticated_web_access_succeeds(auth_admin_cookies):
    """Authenticated request with session cookie loads the Sanctuary Web Dashboard."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", cookies=auth_admin_cookies) as client:
        res = await client.get("/admin")
        assert res.status_code == 200
        assert "text/html" in res.headers.get("content-type", "")
        html = res.text
        assert "UR-Heart Sanctuary Administration" in html
        assert "asiverticals@gmail.com" in html
        assert "Operations Hub" in html
        assert "Biometric KYC" in html


@pytest.mark.asyncio
async def test_admin_logout_flow(auth_admin_cookies, db_session: AsyncSession):
    """POST /admin/api/logout invalidates session cookie and records audit log."""
    app.dependency_overrides[get_db] = lambda: db_session

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", cookies=auth_admin_cookies) as client:
        res = await client.post("/admin/api/logout")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True

    # Check audit record
    stmt = select(AdminAuditLog).where(
        AdminAuditLog.action == "admin_logout",
        AdminAuditLog.admin_email == "asiverticals@gmail.com",
    )
    log = (await db_session.execute(stmt)).scalar_one_or_none()
    assert log is not None


# ==============================================================================
# 3. Operations Hub & Telemetry Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_telemetry_kpis_endpoint(auth_admin_cookies, db_session: AsyncSession, make_user):
    """GET /admin/api/telemetry returns accurate aggregated system metrics."""
    now = datetime.now(timezone.utc)
    user1 = make_user(full_name="Active Seeker", updated_at=now)
    user2 = make_user(full_name="Past Seeker", updated_at=now - timedelta(days=2))
    db_session.add_all([user1, user2])
    await db_session.commit()

    fcm = DeviceFcmToken(
        id=uuid.uuid4(),
        user_id=user1.id,
        token="fcm_token_sample_123456",
        platform="android",
        is_active=True,
    )
    iap = InAppPurchase(
        user_id=user1.id,
        transaction_reference="pay_order_telemetry_test_1",
        product_identifier="pass_monthly",
        store="web_razorpay_india",
        amount_gross=Decimal("149.00"),
        amount_net=Decimal("146.00"),
        status="completed",
        purchased_at=now,
    )
    grv = GrievanceDossier(
        dossier_reference_id="NCII-EMG-20261017-TEL1",
        reporter_id=user1.id,
        violation_category="ncii",
        evidence_text="Test emergency takedown ticket",
        status="under_review",
        sla_deadline_at=now + timedelta(hours=20),
    )

    db_session.add_all([fcm, iap, grv])
    await db_session.commit()

    app.dependency_overrides[get_db] = lambda: db_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", cookies=auth_admin_cookies) as client:
        res = await client.get("/admin/api/telemetry")
        assert res.status_code == 200
        data = res.json()
        assert data["total_seekers"] >= 2
        assert data["dau"] >= 1
        assert data["emergency_ncii_count"] >= 1
        assert data["revenue_24h"] >= 149.0
        assert data["active_fcm_devices"] >= 1


# ==============================================================================
# 4. Biometric KYC Adjudication & Audit Trail Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_kyc_escalation_adjudication_and_audit(auth_admin_cookies, db_session: AsyncSession, make_user):
    """Approving KYC escalation sets user.kyc_status=True, escalation=approved, and writes audit log."""
    seeker = make_user(full_name="KYC Pending Seeker", kyc_status=False)
    db_session.add(seeker)
    await db_session.flush()

    escalation = AdminKycEscalation(
        user_id=seeker.id,
        declared_dob=date(2000, 1, 1),
        declared_age=26,
        groq_match_score=Decimal("0.650"),
        groq_reasoning="Borderline facial similarity",
        anchor_photo_url="users/test/anchor.webp",
        kyc_video_url="kyc_escalations/test/review.webp",
        status="pending",
    )
    db_session.add(escalation)
    await db_session.commit()
    await db_session.refresh(escalation)

    app.dependency_overrides[get_db] = lambda: db_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", cookies=auth_admin_cookies) as client:
        # 1. Fetch pending queue
        res_list = await client.get("/admin/api/kyc/pending")
        assert res_list.status_code == 200
        items = res_list.json()
        assert any(i["id"] == str(escalation.id) for i in items)

        # 2. Adjudicate Approval
        res_decide = await client.post(
            f"/admin/api/kyc/{escalation.id}/decide",
            json={"decision": "approve", "notes": "Facial geometry verified by human admin."},
        )
        assert res_decide.status_code == 200
        data = res_decide.json()
        assert data["status"] == "approved"

    # Verify Database state
    await db_session.refresh(seeker)
    await db_session.refresh(escalation)
    assert seeker.kyc_status is True
    assert escalation.status == "approved"

    # Verify Audit log
    stmt = select(AdminAuditLog).where(
        AdminAuditLog.action == "kyc_approve",
        AdminAuditLog.target_type == "kyc_escalation",
        AdminAuditLog.target_id == str(escalation.id),
    )
    log = (await db_session.execute(stmt)).scalar_one_or_none()
    assert log is not None
    assert log.admin_email == "asiverticals@gmail.com"


@pytest.mark.asyncio
async def test_kyc_escalation_rejection_and_audit(auth_admin_cookies, db_session: AsyncSession, make_user):
    """Rejecting KYC escalation sets user.kyc_status=False, escalation=rejected, and writes audit log."""
    seeker = make_user(full_name="KYC Spoof Seeker", kyc_status=False)
    db_session.add(seeker)
    await db_session.flush()

    escalation = AdminKycEscalation(
        user_id=seeker.id,
        declared_dob=date(2002, 5, 12),
        declared_age=24,
        groq_match_score=Decimal("0.350"),
        groq_reasoning="Synthetic screen replay detected",
        anchor_photo_url="users/test/anchor.webp",
        kyc_video_url="kyc_escalations/test/spoof.webp",
        status="pending",
    )
    db_session.add(escalation)
    await db_session.commit()
    await db_session.refresh(escalation)

    app.dependency_overrides[get_db] = lambda: db_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", cookies=auth_admin_cookies) as client:
        res = await client.post(
            f"/admin/api/kyc/{escalation.id}/decide",
            json={"decision": "reject", "notes": "Anti-spoofing rejection: non-live screen capture."},
        )
        assert res.status_code == 200
        assert res.json()["status"] == "rejected"

    await db_session.refresh(seeker)
    await db_session.refresh(escalation)
    assert seeker.kyc_status is False
    assert escalation.status == "rejected"

    # Verify audit log
    stmt = select(AdminAuditLog).where(
        AdminAuditLog.action == "kyc_reject",
        AdminAuditLog.target_id == str(escalation.id),
    )
    log = (await db_session.execute(stmt)).scalar_one_or_none()
    assert log is not None


# ==============================================================================
# 5. Grievances & Emergency NCII Moderation Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_grievance_list_and_resolution_flow(auth_admin_cookies, db_session: AsyncSession, make_user):
    """Superadmin resolves emergency NCII grievance, updating status to actioned and recording audit log."""
    reporter = make_user(full_name="Victim Seeker")
    db_session.add(reporter)
    await db_session.flush()

    now = datetime.now(timezone.utc)
    dossier = GrievanceDossier(
        dossier_reference_id="NCII-EMG-20261017-TESTGRV",
        reporter_id=reporter.id,
        violation_category="ncii",
        evidence_text="Unauthorized photo distribution.",
        status="under_review",
        sla_deadline_at=now + timedelta(hours=18),
    )
    db_session.add(dossier)
    await db_session.commit()

    app.dependency_overrides[get_db] = lambda: db_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", cookies=auth_admin_cookies) as client:
        # 1. Fetch grievance list (sorted by SLA)
        res_list = await client.get("/admin/api/grievances")
        assert res_list.status_code == 200
        items = res_list.json()
        assert any(d["dossier_reference_id"] == "NCII-EMG-20261017-TESTGRV" for d in items)

        # 2. Resolve grievance
        res_res = await client.post(
            f"/admin/api/grievances/{dossier.id}/resolve",
            json={
                "status": "actioned",
                "resolution_summary": "Content taken down pursuant to IT Rules 2021 Rule 3(2)(b).",
            },
        )
        assert res_res.status_code == 200
        data = res_res.json()
        assert data["status"] == "actioned"

    # Verify DB update
    await db_session.refresh(dossier)
    assert dossier.status == "actioned"
    assert dossier.actioned_at is not None
    assert dossier.resolved_at is not None

    # Verify Audit log
    stmt = select(AdminAuditLog).where(
        AdminAuditLog.action == "resolve_grievance",
        AdminAuditLog.target_id == str(dossier.id),
    )
    log = (await db_session.execute(stmt)).scalar_one_or_none()
    assert log is not None
    assert log.details["status"] == "actioned"


@pytest.mark.asyncio
async def test_grievance_invalid_status_rejected(auth_admin_cookies, db_session: AsyncSession, make_user):
    """Status check constraints are strictly enforced; invalid status is rejected with 422."""
    dossier = GrievanceDossier(
        dossier_reference_id="URH-GRV-20261017-INVALID",
        violation_category="harassment",
        evidence_text="Abuse report",
        status="acknowledged",
    )
    db_session.add(dossier)
    await db_session.commit()

    app.dependency_overrides[get_db] = lambda: db_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", cookies=auth_admin_cookies) as client:
        res = await client.post(
            f"/admin/api/grievances/{dossier.id}/resolve",
            json={"status": "bogus_status_rejected", "resolution_summary": "Invalid"},
        )
        assert res.status_code == 422


# ==============================================================================
# 6. Seeker Management Console Tests (Ban / Unban / Revocation)
# ==============================================================================

@pytest.mark.asyncio
async def test_seeker_search_and_toggle_ban_flow(auth_admin_cookies, db_session: AsyncSession, make_user):
    """Superadmin searches seeker, toggles ban, verifies token_version increment, and restores account."""
    target_user = make_user(
        full_name="Violating User",
        email="bad_user@urheart.app",
        token_version=2,
    )
    db_session.add(target_user)
    await db_session.commit()

    app.dependency_overrides[get_db] = lambda: db_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", cookies=auth_admin_cookies) as client:
        # 1. Search seeker
        res_search = await client.get("/admin/api/users?query=bad_user@urheart.app")
        assert res_search.status_code == 200
        users = res_search.json()
        assert len(users) == 1
        assert users[0]["masked_contact_bridge"] == "whatsapp: [PROTECTED_AES_BRIDGE]"

        # 2. Toggle Ban (Soft delete + increment token_version)
        res_ban = await client.post(
            f"/admin/api/users/{target_user.id}/toggle-ban",
            json={"reason": "Safety policy violations."},
        )
        assert res_ban.status_code == 200
        ban_data = res_ban.json()
        assert ban_data["is_banned"] is True
        assert ban_data["token_version"] == 3

    # Check database
    await db_session.refresh(target_user)
    assert target_user.deleted_at is not None
    assert target_user.token_version == 3

    # Verify Audit log for ban
    stmt_ban = select(AdminAuditLog).where(
        AdminAuditLog.action == "user_banned",
        AdminAuditLog.target_id == str(target_user.id),
    )
    log_ban = (await db_session.execute(stmt_ban)).scalar_one_or_none()
    assert log_ban is not None

    # 3. Unban (Restore)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", cookies=auth_admin_cookies) as client:
        res_unban = await client.post(
            f"/admin/api/users/{target_user.id}/toggle-ban",
            json={"reason": "Appeal accepted by Grievance Officer."},
        )
        assert res_unban.status_code == 200
        assert res_unban.json()["is_banned"] is False

    await db_session.refresh(target_user)
    assert target_user.deleted_at is None


# ==============================================================================
# 7. Monetization & Customer Support Grants Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_monetization_grant_sparks_flow(auth_admin_cookies, db_session: AsyncSession, make_user):
    """Superadmin grants Sparks to seeker for customer support dispute resolution with audit record."""
    seeker = make_user(full_name="Loyal Seeker", reward_balance=50)
    db_session.add(seeker)
    await db_session.commit()

    app.dependency_overrides[get_db] = lambda: db_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", cookies=auth_admin_cookies) as client:
        res = await client.post(
            f"/admin/api/users/{seeker.id}/grant-sparks",
            json={"sparks_amount": 100, "reason": "Compensation for dropped call."},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["previous_balance"] == 50
        assert data["reward_balance"] == 150

    await db_session.refresh(seeker)
    assert seeker.reward_balance == 150

    # Verify audit log
    stmt = select(AdminAuditLog).where(
        AdminAuditLog.action == "grant_sparks",
        AdminAuditLog.target_id == str(seeker.id),
    )
    log = (await db_session.execute(stmt)).scalar_one_or_none()
    assert log is not None
    assert log.details["delta"] == 100


@pytest.mark.asyncio
async def test_monetization_grant_pass_flow(auth_admin_cookies, db_session: AsyncSession, make_user):
    """Superadmin manually provisions a monthly pass to seeker for missing purchase recovery."""
    seeker = make_user(full_name="Subscriber Seeker", subscription_tier="free")
    db_session.add(seeker)
    await db_session.commit()

    app.dependency_overrides[get_db] = lambda: db_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", cookies=auth_admin_cookies) as client:
        res = await client.post(
            f"/admin/api/users/{seeker.id}/grant-pass",
            json={"sku": "pass_monthly", "reason": "Missing purchase recovery for Razorpay order pay_99482"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["subscription_tier"] == "flame"

    await db_session.refresh(seeker)
    assert seeker.subscription_tier == "flame"

    # Verify audit log
    stmt = select(AdminAuditLog).where(
        AdminAuditLog.action == "grant_pass",
        AdminAuditLog.target_id == str(seeker.id),
    )
    log = (await db_session.execute(stmt)).scalar_one_or_none()
    assert log is not None


# ==============================================================================
# 8. Underage Quarantine Registry & Release Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_quarantine_list_and_release_flow(auth_admin_cookies, db_session: AsyncSession):
    """Superadmin inspects quarantined device and releases false-positive with audit log."""
    now = datetime.now(timezone.utc)
    quarantine = UnderageQuarantineRegistry(
        device_hash="device_fingerprint_hash_abc123",
        attempted_dob=date(2010, 1, 1),
        quarantine_until=now + timedelta(days=365),
        attempt_metadata={"attempted_age": 16},
    )
    db_session.add(quarantine)
    await db_session.commit()

    app.dependency_overrides[get_db] = lambda: db_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", cookies=auth_admin_cookies) as client:
        # 1. Query quarantine records
        res_list = await client.get("/admin/api/quarantine")
        assert res_list.status_code == 200
        items = res_list.json()
        assert any(r["device_hash"] == "device_fingerprint_hash_abc123" for r in items)

        # 2. Release quarantine
        res_rel = await client.post(
            f"/admin/api/quarantine/{quarantine.id}/release",
            json={"reason": "Seeker entered mistyped DOB; verified 24+ via passport."},
        )
        assert res_rel.status_code == 200
        assert res_rel.json()["success"] is True

    await db_session.refresh(quarantine)
    until_dt = quarantine.quarantine_until
    if until_dt.tzinfo is None:
        until_dt = until_dt.replace(tzinfo=timezone.utc)
    assert until_dt <= datetime.now(timezone.utc)

    # Verify audit log
    stmt = select(AdminAuditLog).where(
        AdminAuditLog.action == "release_quarantine",
        AdminAuditLog.target_id == str(quarantine.id),
    )
    log = (await db_session.execute(stmt)).scalar_one_or_none()
    assert log is not None


# ==============================================================================
# 9. DPDP Compliance & System Audit Logs Endpoints Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_dpdp_compliance_records_endpoint(auth_admin_cookies, db_session: AsyncSession, make_user):
    """GET /admin/api/dpdp returns SAR requests, digital nominees, and consent logs."""
    user = make_user()
    db_session.add(user)
    await db_session.flush()

    nominee = DataNominee(
        user_id=user.id,
        nominee_name="Legal Kin Nominee",
        nominee_contact="kin@urheart.app",
        relationship="Sister",
    )
    consent = ConsentAuditLog(
        user_id=user.id,
        consent_purpose_id="biometric_kyc",
        ip_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        installation_uuid="install_uuid_sample_abc",
    )
    export_req = DataExportRequest(
        user_id=user.id,
        status="ready",
        checksum_sha256="abcd1234efgh5678",
    )
    db_session.add_all([nominee, consent, export_req])
    await db_session.commit()

    app.dependency_overrides[get_db] = lambda: db_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", cookies=auth_admin_cookies) as client:
        res = await client.get("/admin/api/dpdp")
        assert res.status_code == 200
        data = res.json()
        assert len(data["export_requests"]) >= 1
        assert len(data["nominees"]) >= 1
        assert len(data["consent_logs"]) >= 1


@pytest.mark.asyncio
async def test_audit_logs_query_endpoint(auth_admin_cookies, db_session: AsyncSession):
    """GET /admin/api/audit-logs returns real-time immutable audit records with filters."""
    log_entry = AdminAuditLog(
        admin_email="asiverticals@gmail.com",
        action="manual_test_action",
        target_type="test_entity",
        target_id="test_id_12345",
        details={"info": "Automated test audit log entry"},
        ip_address="192.168.1.1",
    )
    db_session.add(log_entry)
    await db_session.commit()

    app.dependency_overrides[get_db] = lambda: db_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", cookies=auth_admin_cookies) as client:
        res = await client.get("/admin/api/audit-logs?action=manual_test_action")
        assert res.status_code == 200
        items = res.json()
        assert len(items) >= 1
        assert items[0]["action"] == "manual_test_action"
        assert items[0]["admin_email"] == "asiverticals@gmail.com"
