import re
from datetime import datetime, timezone, timedelta
import httpx
from httpx import ASGITransport
import pytest
from sqlalchemy import select

from backend.app.api.deps import get_current_user, get_db
from backend.app.main import app
from backend.app.models.domain.legal import DataNominee, GrievanceDossier, ConsentAuditLog
from backend.app.models.domain.match_and_chat import Match
from backend.app.services.legal_vault_service import legal_vault_service


@pytest.mark.asyncio
async def test_nominee_registration_and_upsert(db_session, make_user):
    """Test 1: Nominee Upsert: Registering creates database row; re-submitting updates details without duplicate PK error."""
    user = make_user(full_name="Legal Seeker", is_profile_completed=True)
    db_session.add(user)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Initial Designation
            payload1 = {
                "nominee_name": "Radha Devi",
                "nominee_contact": "+919876543210",
                "relationship": "Sister",
            }
            res1 = await client.post("/api/v1/legal/nominee", json=payload1)
            assert res1.status_code == 200
            data1 = res1.json()["data"]
            assert data1["nominee_name"] == "Radha Devi"
            assert data1["nominee_contact"] == "+919876543210"
            assert data1["relationship"] == "Sister"
            assert data1["verification_status"] == "designated"
            assert "assigned_at" in data1

            # Verify in DB
            stmt = select(DataNominee).where(DataNominee.user_id == user.id)
            db_res = await db_session.execute(stmt)
            nominees = db_res.scalars().all()
            assert len(nominees) == 1
            assert nominees[0].nominee_name == "Radha Devi"

            # 2. Idempotent Update
            payload2 = {
                "nominee_name": "Radha Sharma",
                "nominee_contact": "+919876543211",
                "relationship": "Spouse",
            }
            res2 = await client.post("/api/v1/legal/nominee", json=payload2)
            assert res2.status_code == 200
            data2 = res2.json()["data"]
            assert data2["nominee_name"] == "Radha Sharma"
            assert data2["relationship"] == "Spouse"

            # Verify still exactly 1 record in DB
            db_res2 = await db_session.execute(stmt)
            nominees2 = db_res2.scalars().all()
            assert len(nominees2) == 1
            assert nominees2[0].nominee_name == "Radha Sharma"
            assert nominees2[0].nominee_contact == "+919876543211"

            # 3. GET /api/v1/legal/nominee returns active nominee
            get_res = await client.get("/api/v1/legal/nominee")
            assert get_res.status_code == 200
            assert get_res.json()["data"]["nominee_name"] == "Radha Sharma"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_grievance_reference_format(db_session, make_user):
    """Test 2: Verified dossier reference matches URH-GRV-\\d{8}-[A-F0-9]{6} regex."""
    ref = legal_vault_service.generate_dossier_reference()
    pattern = r"^URH-GRV-\d{8}-[A-F0-9]{6}$"
    assert re.match(pattern, ref), f"Reference {ref} failed to match pattern {pattern}"


@pytest.mark.asyncio
async def test_grievance_statutory_sla_15_days(db_session, make_user):
    """Test 3: SLA Due Date: statutory_resolution_due_at is exactly 15 days ahead of acknowledgment timestamp."""
    u1 = make_user(full_name="Reporter Seeker")
    u2 = make_user(full_name="Reported Seeker")
    db_session.add_all([u1, u2])
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: u1
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "reported_user_id": str(u2.id),
                "violation_category": "harassment",
                "evidence_text": "Repeated unwelcome communications in violation of Sanctuary norms.",
            }
            res = await client.post("/api/v1/legal/grievance", json=payload)
            assert res.status_code == 200
            data = res.json()["data"]

            assert re.match(r"^URH-GRV-\d{8}-[A-F0-9]{6}$", data["dossier_reference_id"])
            assert data["status"] == "acknowledged"

            ack_time = datetime.fromisoformat(data["acknowledgment_sent_at"])
            due_time = datetime.fromisoformat(data["statutory_resolution_due_at"])

            delta = due_time - ack_time
            assert delta.days == 15
            assert abs(delta.total_seconds() - (15 * 86400)) < 5.0

            # Verify GET /api/v1/legal/grievances lists the filed dossier
            list_res = await client.get("/api/v1/legal/grievances")
            assert list_res.status_code == 200
            items = list_res.json()["data"]
            assert len(items) >= 1
            assert items[0]["dossier_reference_id"] == data["dossier_reference_id"]
            assert items[0]["violation_category"] == "harassment"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_grievance_category_validation(db_session, make_user):
    """Test 4: Grievance Category Enforcement: Submitting an invalid category outside allowed literal set raises HTTP 422."""
    u1 = make_user(full_name="Grievance Validator")
    u2 = make_user(full_name="Target Seeker")
    db_session.add_all([u1, u2])
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: u1
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Invalid Category -> 422
            invalid_payload = {
                "reported_user_id": str(u2.id),
                "violation_category": "commercial_spam_unauthorized",
                "evidence_text": "Spam message",
            }
            res = await client.post("/api/v1/legal/grievance", json=invalid_payload)
            assert res.status_code == 422

            # 2. Self Reporting -> 400
            self_payload = {
                "reported_user_id": str(u1.id),
                "violation_category": "harassment",
                "evidence_text": "Self report attempt",
            }
            res_self = await client.post("/api/v1/legal/grievance", json=self_payload)
            assert res_self.status_code == 400
            assert res_self.json()["error_code"] == "INVALID_GRIEVANCE_TARGET"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_data_portability_sanitized_export(db_session, make_user):
    """Test 5: Data Portability Export: Asserts exported JSON includes core profile fields, media links, and sanitizes private keys."""
    u1 = make_user(
        full_name="Sovereign Seeker",
        bio="Deep reflections and mindful dialogue.",
        profession="Architect",
        education="IIT Roorkee",
        photos=["https://media.urheart.app/p1.webp", "https://media.urheart.app/p2.webp"],
        voice_spark_url="https://media.urheart.app/voice1.m4a",
    )
    u2 = make_user(full_name="Counterparty Seeker")
    db_session.add_all([u1, u2])
    await db_session.flush()

    # Add match (respect user1_id < user2_id constraint)
    p1, p2 = (u1.id, u2.id) if u1.id < u2.id else (u2.id, u1.id)
    match = Match(user1_id=p1, user2_id=p2, is_active=True, closure_status="active")
    # Add consent
    consent = ConsentAuditLog(
        user_id=u1.id,
        consent_purpose_id="terms_dpdp_2023",
        ip_hash="fake_hash",
        installation_uuid="inst_uuid_123",
    )
    # Add nominee
    nominee = DataNominee(
        user_id=u1.id,
        nominee_name="Gitanjali Devi",
        nominee_contact="+919876543200",
        relationship="Mother",
    )
    db_session.add_all([match, consent, nominee])
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: u1
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post("/api/v1/legal/data-export")
            assert res.status_code == 200
            body = res.json()
            assert body["success"] is True

            export = body["data"]["export_data"]

            # Compliance Seal
            seal = export["compliance_seal"]
            assert "Digital Personal Data Protection Act 2023" in seal["act"]
            assert seal["sanitized"] is True
            assert seal["secrets_redacted"] is True

            # Profile attributes
            profile = export["user_profile"]
            assert profile["full_name"] == "Sovereign Seeker"
            assert profile["profession"] == "Architect"
            assert profile["education"] == "IIT Roorkee"

            # Media Assets
            media = export["media_assets"]
            assert len(media["photos"]) == 2
            assert media["voice_spark_url"] == "https://media.urheart.app/voice1.m4a"

            # Connections & Consents
            assert len(export["connections_metadata"]) >= 1
            assert "omitted to protect counterparty statutory privacy" in export["connections_metadata"][0]["privacy_notice"]
            assert len(export["consent_audit_trail"]) >= 1

            # Digital Nominee
            assert export["digital_nominee"]["nominee_name"] == "Gitanjali Devi"

            # Strict Security Sanitization Verification
            export_text = str(export).lower()
            assert "password" not in export_text or "passwords_and_hashes_omitted" in export_text
            assert "raw_secret" not in export_text
            assert "private_key" not in export_text
    finally:
        app.dependency_overrides.clear()
