import uuid
from datetime import date
from decimal import Decimal
import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy import select

from backend.app.api.deps import get_current_user
from backend.app.core.database import get_db
from backend.app.core.security import decrypt_contact_bridge
from backend.app.main import app
from backend.app.models.domain.user import User


@pytest.mark.asyncio
async def test_create_profile_success(db_session, make_user):
    """Test 1: Uncompleted profile calls POST /create -> marks profile complete."""
    user = make_user(is_profile_completed=False)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/profile/create",
                json={
                    "full_name": "Mira Bai",
                    "dob": "1998-05-15",
                    "gender": "Woman",
                    "interested_in": "Everyone",
                    "contact_bridge_type": "whatsapp",
                    "contact_bridge_handle": "+919876543210",
                    "bio": "Devotional artist and poet.",
                    "profession": "Author",
                    "education": "Varanasi Sanskrit Vishwavidyalaya",
                    "photos": ["https://media.urheart.app/mira/photo1.webp"],
                },
            )
            assert resp.status_code == 200
            data = resp.json()["data"]
            assert data["is_profile_completed"] is True
            assert data["full_name"] == "Mira Bai"

            # Verify in DB
            stmt = select(User).where(User.id == user.id)
            updated = (await db_session.execute(stmt)).scalar_one()
            assert updated.is_profile_completed is True
            assert updated.bio == "Devotional artist and poet."
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_profile_already_completed_fails(db_session, make_user):
    """Test 2: Completed profile calling POST /create triggers HTTP 400 PROFILE_ALREADY_COMPLETED."""
    user = make_user(is_profile_completed=True)
    db_session.add(user)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/profile/create",
                json={
                    "full_name": "Duplicate Entry",
                    "dob": "1995-01-01",
                    "gender": "Man",
                    "interested_in": "Women",
                    "contact_bridge_type": "telegram",
                    "contact_bridge_handle": "@duplicate",
                    "photos": ["https://media.urheart.app/p1.webp"],
                },
            )
            assert resp.status_code == 400
            body = resp.json()
            assert body["error_code"] == "PROFILE_ALREADY_COMPLETED"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_put_profile_uncompleted_profile_fails(db_session, make_user):
    """Test 3: Calling PUT /api/v1/profile before onboarding triggers HTTP 400 PROFILE_NOT_COMPLETED."""
    user = make_user(is_profile_completed=False)
    db_session.add(user)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.put(
                "/api/v1/profile",
                json={"bio": "Trying to edit early."},
            )
            assert resp.status_code == 400
            assert resp.json()["error_code"] == "PROFILE_NOT_COMPLETED"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_put_profile_success(db_session, make_user):
    """Test 4: Completed profile calling PUT /api/v1/profile successfully updates multiple fields."""
    user = make_user(
        full_name="Anand Sen",
        bio="Original bio.",
        profession="Engineer",
        education="IIT Kanpur",
        photos=["https://media.urheart.app/orig.webp"],
        avatar_url="https://media.urheart.app/orig.webp",
        is_profile_completed=True,
    )
    db_session.add(user)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.put(
                "/api/v1/profile",
                json={
                    "bio": "Updated spiritual journey and architect.",
                    "profession": "Senior Architect",
                    "education": "IIT Delhi",
                    "photos": [
                        "https://media.urheart.app/new1.webp",
                        "https://media.urheart.app/new2.webp",
                    ],
                    "avatar_url": "https://media.urheart.app/new1.webp",
                    "location_name": "New Delhi, DL",
                    "latitude": 28.6139,
                    "longitude": 77.2090,
                    "voice_spark_url": "https://media.urheart.app/voice/spark1.m4a",
                    "voice_spark_duration": 6.5,
                },
            )
            assert resp.status_code == 200
            data = resp.json()["data"]
            assert data["bio"] == "Updated spiritual journey and architect."
            assert data["profession"] == "Senior Architect"
            assert data["education"] == "IIT Delhi"
            assert len(data["photos"]) == 2
            assert data["avatar_url"] == "https://media.urheart.app/new1.webp"
            assert data["voice_spark_duration"] == 6.5

            # Verify in DB
            stmt = select(User).where(User.id == user.id)
            refreshed = (await db_session.execute(stmt)).scalar_one()
            assert refreshed.profession == "Senior Architect"
            assert refreshed.education == "IIT Delhi"
            assert refreshed.latitude == Decimal("28.61")  # Fuzzed to 2 decimal places
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_put_profile_partial_update_preserves_other_fields(db_session, make_user):
    """Test 5: Updating only bio does not erase photos or profession."""
    user = make_user(
        full_name="Sita Devi",
        bio="Initial bio.",
        profession="Botanist",
        education="University of Delhi",
        photos=["https://media.urheart.app/photo_a.webp"],
        avatar_url="https://media.urheart.app/photo_a.webp",
        is_profile_completed=True,
    )
    db_session.add(user)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.put(
                "/api/v1/profile",
                json={"bio": "Now loving silence and forestry."},
            )
            assert resp.status_code == 200
            data = resp.json()["data"]
            assert data["bio"] == "Now loving silence and forestry."
            assert data["profession"] == "Botanist"
            assert data["education"] == "University of Delhi"
            assert data["photos"] == ["https://media.urheart.app/photo_a.webp"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_put_profile_contact_bridge_re_encryption(db_session, make_user):
    """Test 6: Updating contact bridge re-encrypts the handle in DB."""
    user = make_user(
        contact_bridge_type="whatsapp",
        contact_bridge_encrypted="old_encrypted_val",
        is_profile_completed=True,
    )
    db_session.add(user)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.put(
                "/api/v1/profile",
                json={
                    "contact_bridge_type": "telegram",
                    "contact_bridge_handle": "@sanctuary_peace",
                },
            )
            assert resp.status_code == 200

            # Verify in DB that it is encrypted and decryptable
            stmt = select(User).where(User.id == user.id)
            refreshed = (await db_session.execute(stmt)).scalar_one()
            assert refreshed.contact_bridge_type == "telegram"
            assert refreshed.contact_bridge_encrypted != "old_encrypted_val"
            decrypted = decrypt_contact_bridge(refreshed.contact_bridge_encrypted)
            assert decrypted == "@sanctuary_peace"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_put_profile_age_range_validation_rejection(db_session, make_user):
    """Test 7: Inverted preferred age range (min > max) is rejected with HTTP 422."""
    user = make_user(is_profile_completed=True)
    db_session.add(user)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.put(
                "/api/v1/profile",
                json={
                    "preferred_age_min": 35,
                    "preferred_age_max": 25,
                },
            )
            assert resp.status_code == 422
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_put_profile_coordinate_fuzzing(db_session, make_user):
    """Test 8: Latitude and longitude are fuzzed to 2 decimal places (~1.1km grid)."""
    user = make_user(is_profile_completed=True)
    db_session.add(user)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.put(
                "/api/v1/profile",
                json={
                    "latitude": 26.792222,
                    "longitude": 82.199722,
                },
            )
            assert resp.status_code == 200
            data = resp.json()["data"]
            assert data["latitude"] == 26.79
            assert data["longitude"] == 82.20
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_put_profile_trailing_slash_resilience(db_session, make_user):
    """Test 9: Both PUT /api/v1/profile and PUT /api/v1/profile/ succeed without redirect errors."""
    user = make_user(is_profile_completed=True)
    db_session.add(user)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # Without slash
            r1 = await client.put("/api/v1/profile", json={"bio": "Path test 1"})
            assert r1.status_code == 200

            # With slash
            r2 = await client.put("/api/v1/profile/", json={"bio": "Path test 2"})
            assert r2.status_code == 200
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_put_profile_extra_fields_ignored(db_session, make_user):
    """Test 10: Extra client fields (like dob from Flutter) are ignored and do not trigger 422."""
    user = make_user(
        full_name="Radha Rani",
        bio="Original Radha bio.",
        is_profile_completed=True,
    )
    db_session.add(user)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.put(
                "/api/v1/profile",
                json={
                    "bio": "Updated Radha bio with ignore extra.",
                    "dob": "1996-08-10",
                    "unrecognized_flutter_prop": "ignored_value",
                },
            )
            assert resp.status_code == 200
            data = resp.json()["data"]
            assert data["bio"] == "Updated Radha bio with ignore extra."
    finally:
        app.dependency_overrides.clear()
