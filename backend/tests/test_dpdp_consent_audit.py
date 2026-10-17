import httpx
from httpx import ASGITransport
import pytest
from sqlalchemy import select

from backend.app.api.deps import get_current_user, get_db
from backend.app.main import app
from backend.app.models.domain.legal import ConsentAuditLog


@pytest.mark.asyncio
async def test_record_statutory_consent_affirmation(db_session, make_user):
    """Verifies POST /api/v1/legal/consent-record logs immutable consent under DPDP Act 2023 § 6."""
    user = make_user(full_name="Consenting Seeker")
    db_session.add(user)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "consent_purpose_id": "dpdp_statutory_consent_v1",
                "installation_uuid": "inst-device-789-xyz",
            }
            res = await client.post("/api/v1/legal/consent-record", json=payload)
            assert res.status_code == 200
            body = res.json()
            assert body["success"] is True
            assert body["data"]["recorded"] is True
            assert body["data"]["purpose_id"] == "dpdp_statutory_consent_v1"

            # Verify recorded in DB
            stmt = select(ConsentAuditLog).where(ConsentAuditLog.user_id == user.id)
            result = await db_session.execute(stmt)
            logs = result.scalars().all()
            assert len(logs) == 1
            assert logs[0].consent_purpose_id == "dpdp_statutory_consent_v1"
            assert logs[0].installation_uuid == "inst-device-789-xyz"
            assert len(logs[0].ip_hash) == 64  # SHA-256 hash of IP
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_privacy_policy_eighth_schedule_languages():
    """Verifies GET /api/v1/legal/privacy exposes official Eighth Schedule languages under DPDP § 6(7)."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/legal/privacy")
        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        data = body["data"]

        assert "languages_supported" in data
        languages = data["languages_supported"]

        required_languages = [
            "English", "Hindi", "Bengali", "Telugu", "Marathi",
            "Tamil", "Gujarati", "Kannada", "Malayalam", "Odia", "Punjabi",
        ]
        for lang in required_languages:
            assert lang in languages, f"Missing required Eighth Schedule language: {lang}"


@pytest.mark.asyncio
async def test_grievance_officer_physical_address_and_sla():
    """Verifies GET /api/v1/legal/grievance-officer returns physical address in India under IT Rules 2021 Rule 3(2)(a)."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/legal/grievance-officer")
        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        data = body["data"]

        assert "physical_address" in data
        assert "Ayodhya" in data["physical_address"]
        assert "India" in data["physical_address"]
        assert data["emergency_takedown_sla_hours"] == 24
        assert data["general_resolution_sla_days"] == 15
        assert data["email"] == "asiverticals@gmail.com"
        assert data["name"] == "Anubhav Singh"
        assert data.get("telephone") is None
