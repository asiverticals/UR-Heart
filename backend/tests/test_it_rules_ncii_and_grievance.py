"""
IT Rules 2021 Rule 3(2)(a) & (b) Compliance & Safe Harbor Integrity Tests.

Verifies:
1. Ingestion of 'ncii' (Non-Consensual Intimate Imagery) grievances succeeds without HTTP 422.
2. 24-hour statutory takedown SLA calculation for emergency categories (ncii, explicit_content).
3. Publication of physical office address in India in GET /api/v1/legal/grievance-officer.
4. Public unauthenticated emergency takedown portal for non-user victims (POST /api/v1/legal/emergency-takedown).
5. Database constraint alignment in migration 20261016170000_legal_and_compliance_hardening.sql.
"""

from datetime import datetime, timezone, timedelta
from pathlib import Path
import uuid
import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_current_user, get_db
from backend.app.main import app
from backend.app.models.domain.legal import GrievanceDossier


@pytest.mark.asyncio
async def test_ncii_grievance_submission_and_24h_sla(db_session: AsyncSession, make_user):
    """Assert authenticated seekers can report NCII violations with 24-hour emergency SLA."""
    reporter = make_user(full_name="Reporting Seeker", is_profile_completed=True)
    reported = make_user(full_name="Violating Seeker", is_profile_completed=True)
    db_session.add_all([reporter, reported])
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: reporter
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/legal/grievance",
                json={
                    "reported_user_id": str(reported.id),
                    "violation_category": "ncii",
                    "evidence_text": "Non-consensual image distribution reported under IT Rules Rule 3(2)(b).",
                },
            )
            assert resp.status_code == 200, f"Failed with {resp.text}"
            data = resp.json()["data"]
            assert data["dossier_reference_id"].startswith("URH-GRV-")
            assert data["emergency_takedown_due_at"] is not None

            # Verify 24-hour SLA calculation
            ack_dt = datetime.fromisoformat(data["acknowledgment_sent_at"])
            emg_dt = datetime.fromisoformat(data["emergency_takedown_due_at"])
            delta = emg_dt - ack_dt
            assert abs(delta.total_seconds() - 86400) < 60  # ~24 hours

            # Verify database record
            stmt = select(GrievanceDossier).where(
                GrievanceDossier.dossier_reference_id == data["dossier_reference_id"]
            )
            res = await db_session.execute(stmt)
            dossier = res.scalar_one_or_none()
            assert dossier is not None
            assert dossier.violation_category == "ncii"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_grievance_officer_publishes_indian_physical_address():
    """Assert GET /api/v1/legal/grievance-officer returns mandatory Indian physical address (Rule 3(2)(a))."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/legal/grievance-officer")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "physical_address" in data
        assert "India" in data["physical_address"]
        assert "Ayodhya" in data["physical_address"]
        assert data["emergency_takedown_sla_hours"] == 24
        assert data["email"] == "asiverticals@gmail.com"
        assert data["name"] == "Anubhav Singh"
        assert data.get("telephone") is None


@pytest.mark.asyncio
async def test_public_emergency_takedown_portal_for_external_victims(db_session: AsyncSession):
    """Assert unauthenticated non-user victims can submit emergency 24-hour NCII complaints."""
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/legal/emergency-takedown",
                json={
                    "complainant_name": "Aggrieved Citizen",
                    "complainant_email": "citizen@example.com",
                    "complainant_phone": "+91-9876543210",
                    "reported_handle_or_name": "harasser_handle",
                    "violation_category": "ncii",
                    "evidence_text": "Private photographs shared without consent on profile moments.",
                    "evidence_media_url": "https://media.urheart.app/users/abc/moments/slot_1.webp",
                    "good_faith_affirmation": True,
                },
            )
            assert resp.status_code == 200
            data = resp.json()["data"]
            assert data["dossier_reference_id"].startswith("NCII-EMG-")
            assert data["statutory_sla_hours"] == 24
            assert data["status"] == "acknowledged"

            # Check DB record
            stmt = select(GrievanceDossier).where(
                GrievanceDossier.dossier_reference_id == data["dossier_reference_id"]
            )
            res = await db_session.execute(stmt)
            dossier = res.scalar_one_or_none()
            assert dossier is not None
            assert dossier.reporter_id is None
            assert dossier.violation_category == "ncii"
            assert "Aggrieved Citizen" in dossier.statutory_notes
    finally:
        app.dependency_overrides.clear()


def test_ncii_migration_file_exists_and_contains_check_constraint():
    """Verify migration 20261016170000_legal_and_compliance_hardening.sql alters chk_grievance_category."""
    migration_path = (
        Path(__file__).resolve().parent.parent.parent
        / "supabase"
        / "migrations"
        / "20261016170000_legal_and_compliance_hardening.sql"
    )
    assert migration_path.exists()
    content = migration_path.read_text(encoding="utf-8")
    assert "chk_grievance_category" in content
    assert "'ncii'" in content
