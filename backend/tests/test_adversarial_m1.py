"""Adversarial & Stress Verification Test Suite for Milestone 1.

Audits:
1. SwipeRequest schema strictness (extra='forbid') and endpoint HTTP 422 behavior.
2. ProfileUpdate schema validation boundaries, age ranges, coordinate fuzzing, extra fields ignorance.
3. PUT /api/v1/profile authentication guards, state machine (completed vs uncompleted),
   field immutability (dob, id, auth_id, is_profile_completed), and non-destructive partial updates.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal
import httpx
import pytest
from httpx import ASGITransport
from pydantic import ValidationError
from sqlalchemy import select

from backend.app.api.deps import get_current_user
from backend.app.core.database import get_db
from backend.app.core.security import (
    create_access_token,
    decrypt_contact_bridge,
    encrypt_contact_bridge,
)
from backend.app.main import app
from backend.app.models.domain.user import User
from backend.app.schemas.feed import SwipeRequest
from backend.app.schemas.profile import ProfileUpdate


# ==============================================================================
# SECTION 1: SwipeRequest Schema & Strictness Adversarial Tests
# ==============================================================================


def test_swipe_request_valid_actions():
    """Verify all legitimate swipe actions pass schema validation."""
    target_id = uuid.uuid4()
    for action in ["like", "pass", "superlike"]:
        req = SwipeRequest(target_id=target_id, action=action)
        assert req.action == action
        assert req.target_id == target_id


def test_swipe_request_extra_fields_forbidden():
    """Adversarial: Extra fields MUST raise ValidationError (extra='forbid')."""
    target_id = uuid.uuid4()

    # The legacy flutter bug key: 'swipe_type'
    with pytest.raises(ValidationError) as exc:
        SwipeRequest.model_validate({
            "target_id": str(target_id),
            "action": "like",
            "swipe_type": "like",
        })
    errors = exc.value.errors()
    assert any(e["type"] == "extra_forbidden" and "swipe_type" in e["loc"] for e in errors)

    # Arbitrary extraneous fields
    with pytest.raises(ValidationError) as exc2:
        SwipeRequest.model_validate({
            "target_id": str(target_id),
            "action": "pass",
            "malicious_payload": "exploit",
        })
    assert any(e["type"] == "extra_forbidden" for e in exc2.value.errors())


def test_swipe_request_invalid_action():
    """Adversarial: Invalid or corrupted actions must be rejected."""
    target_id = uuid.uuid4()
    for bad_action in ["dislike", "love", "SUPERLIKE", "swipe_right", "", None, 123]:
        with pytest.raises(ValidationError):
            SwipeRequest.model_validate({"target_id": str(target_id), "action": bad_action})


def test_swipe_request_invalid_target_id():
    """Adversarial: Non-UUID target_id must be rejected."""
    for bad_id in ["not-a-uuid", "12345", "", None]:
        with pytest.raises(ValidationError):
            SwipeRequest.model_validate({"target_id": bad_id, "action": "like"})


def test_swipe_request_direct_letter_boundaries():
    """Adversarial: direct_letter_text character limits (max 280)."""
    target_id = uuid.uuid4()

    # Exactly 280 chars -> PASS
    ok_text = "x" * 280
    req = SwipeRequest(target_id=target_id, action="like", direct_letter_text=ok_text)
    assert req.direct_letter_text == ok_text

    # 281 chars -> FAIL
    with pytest.raises(ValidationError):
        SwipeRequest(target_id=target_id, action="like", direct_letter_text="x" * 281)


@pytest.mark.asyncio
async def test_api_feed_swipe_extra_fields_fail_with_422(db_session, make_user):
    """Adversarial: POST /api/v1/feed/swipe rejects extra fields with HTTP 422 Unprocessable Entity."""
    user = make_user(is_profile_completed=True, swipes_remaining=10)
    target = make_user(is_profile_completed=True)
    db_session.add_all([user, target])
    await db_session.commit()

    token = create_access_token(user.id)
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            headers = {"Authorization": f"Bearer {token}"}

            # 1. Payload with legacy 'swipe_type' -> MUST return 422
            resp1 = await client.post(
                "/api/v1/feed/swipe",
                headers=headers,
                json={"target_id": str(target.id), "action": "like", "swipe_type": "like"},
            )
            assert resp1.status_code == 422
            err_types = [e["type"] for e in resp1.json()["detail"]]
            assert "extra_forbidden" in err_types

            # 2. Payload with ONLY 'swipe_type' (missing 'action') -> MUST return 422
            resp2 = await client.post(
                "/api/v1/feed/swipe",
                headers=headers,
                json={"target_id": str(target.id), "swipe_type": "like"},
            )
            assert resp2.status_code == 422

            # 3. Payload with arbitrary extra field -> MUST return 422
            resp3 = await client.post(
                "/api/v1/feed/swipe",
                headers=headers,
                json={"target_id": str(target.id), "action": "like", "unexpected": "value"},
            )
            assert resp3.status_code == 422

            # 4. Valid payload -> MUST NOT return 422 (should return 200)
            resp4 = await client.post(
                "/api/v1/feed/swipe",
                headers=headers,
                json={"target_id": str(target.id), "action": "like"},
            )
            assert resp4.status_code == 200
            assert "is_match" in resp4.json()
    finally:
        app.dependency_overrides.clear()


# ==============================================================================
# SECTION 2: ProfileUpdate Schema Adversarial Stress Tests
# ==============================================================================


def test_profile_update_ignores_extra_fields():
    """Adversarial: ProfileUpdate must tolerate arbitrary extra keys without throwing."""
    payload = {
        "bio": "Spiritual seeker",
        "dob": "1999-01-01",
        "extra_custom_param": "should_be_ignored",
        "nested_unsupported": {"a": 1, "b": [1, 2, 3]},
        "is_profile_completed": False,
        "token_version": 999,
    }
    model = ProfileUpdate.model_validate(payload)
    assert model.bio == "Spiritual seeker"
    # Extra fields are ignored and not attributes of the model
    assert not hasattr(model, "extra_custom_param")
    assert not hasattr(model, "nested_unsupported")


def test_profile_update_coordinate_fuzzing_and_bounds():
    """Adversarial: Fuzzing precision and boundary enforcement for geographic coordinates."""
    # Sub-meter precision gets fuzzed to 2 decimal places (~1.1km grid)
    p1 = ProfileUpdate(latitude=Decimal("28.61392817"), longitude=Decimal("77.20902241"))
    assert p1.latitude == Decimal("28.61")
    assert p1.longitude == Decimal("77.21")

    # Location aliases location_lat and location_lon also fuzzed
    p2 = ProfileUpdate(location_lat=Decimal("19.076090"), location_lon=Decimal("72.877426"))
    assert p2.location_lat == Decimal("19.08")
    assert p2.location_lon == Decimal("72.88")

    # Exact boundary coordinates (-90, 90, -180, 180)
    p3 = ProfileUpdate(latitude=Decimal("90.0"), longitude=Decimal("180.0"))
    assert p3.latitude == Decimal("90.00")
    assert p3.longitude == Decimal("180.00")

    p4 = ProfileUpdate(latitude=Decimal("-90.0"), longitude=Decimal("-180.0"))
    assert p4.latitude == Decimal("-90.00")
    assert p4.longitude == Decimal("-180.00")

    # Out of boundary coordinates must raise ValidationError
    with pytest.raises(ValidationError):
        ProfileUpdate(latitude=Decimal("90.0001"))

    with pytest.raises(ValidationError):
        ProfileUpdate(latitude=Decimal("-90.0001"))

    with pytest.raises(ValidationError):
        ProfileUpdate(longitude=Decimal("180.0001"))

    with pytest.raises(ValidationError):
        ProfileUpdate(longitude=Decimal("-180.0001"))


def test_profile_update_age_limit_validation():
    """Adversarial: Statutory 18+ and maximum bounds for preferred age range."""
    # Min age < 18 rejected
    with pytest.raises(ValidationError):
        ProfileUpdate(preferred_age_min=17)

    # Min age > 99 rejected
    with pytest.raises(ValidationError):
        ProfileUpdate(preferred_age_min=100)

    # Max age < 18 rejected
    with pytest.raises(ValidationError):
        ProfileUpdate(preferred_age_max=17)

    # Max age > 100 rejected
    with pytest.raises(ValidationError):
        ProfileUpdate(preferred_age_max=101)

    # Inverted range (min > max) rejected
    with pytest.raises(ValidationError) as exc:
        ProfileUpdate(preferred_age_min=40, preferred_age_max=30)
    assert "preferred_age_min cannot exceed preferred_age_max" in str(exc.value)

    # Edge: min == max (e.g. exactly 25) allowed
    p_equal = ProfileUpdate(preferred_age_min=25, preferred_age_max=25)
    assert p_equal.preferred_age_min == 25
    assert p_equal.preferred_age_max == 25

    # Edge: only min or only max provided
    p_only_min = ProfileUpdate(preferred_age_min=21)
    assert p_only_min.preferred_age_min == 21
    p_only_max = ProfileUpdate(preferred_age_max=35)
    assert p_only_max.preferred_age_max == 35


def test_profile_update_voice_spark_boundaries():
    """Adversarial: Voice spark duration (0-60s) and URL lengths."""
    # Duration > 60s
    with pytest.raises(ValidationError):
        ProfileUpdate(voice_spark_duration=60.1)

    # Duration < 0s
    with pytest.raises(ValidationError):
        ProfileUpdate(voice_spark_duration=-0.1)

    # Valid duration boundaries
    p_zero = ProfileUpdate(voice_spark_duration=0.0)
    assert p_zero.voice_spark_duration == 0.0
    p_sixty = ProfileUpdate(voice_spark_duration=60.0)
    assert p_sixty.voice_spark_duration == 60.0

    # URL length > 500
    with pytest.raises(ValidationError):
        ProfileUpdate(voice_spark_url="https://media.urheart.app/" + "a" * 500)

    # Prompt length > 120
    with pytest.raises(ValidationError):
        ProfileUpdate(voice_spark_prompt="x" * 121)


def test_profile_update_string_length_and_photo_limits():
    """Adversarial: photos array limits (1-5), name limits (2-60), bio (500)."""
    # Name too short
    with pytest.raises(ValidationError):
        ProfileUpdate(full_name="a")

    # Name too long
    with pytest.raises(ValidationError):
        ProfileUpdate(full_name="a" * 61)

    # Bio too long
    with pytest.raises(ValidationError):
        ProfileUpdate(bio="x" * 501)

    # Photos empty list -> rejected
    with pytest.raises(ValidationError):
        ProfileUpdate(photos=[])

    # Photos > 5 -> rejected
    with pytest.raises(ValidationError):
        ProfileUpdate(photos=[f"https://media.urheart.app/p{i}.jpg" for i in range(6)])

    # Valid 1-5 photos
    p_photos = ProfileUpdate(photos=["https://media.urheart.app/p1.jpg"])
    assert len(p_photos.photos) == 1


def test_profile_update_enum_values():
    """Adversarial: Unknown gender or interested_in types rejected."""
    with pytest.raises(ValidationError):
        ProfileUpdate(gender="Alien")

    with pytest.raises(ValidationError):
        ProfileUpdate(interested_in="Robots")

    with pytest.raises(ValidationError):
        ProfileUpdate(contact_bridge_type="discord")

    # Valid enums
    p = ProfileUpdate(
        gender="Non-Binary",
        interested_in="Everyone",
        contact_bridge_type="signal",
    )
    assert p.gender == "Non-Binary"
    assert p.interested_in == "Everyone"
    assert p.contact_bridge_type == "signal"


# ==============================================================================
# SECTION 3: HTTP Endpoint Adversarial Tests (Authentication & Security)
# ==============================================================================


@pytest.mark.asyncio
async def test_put_profile_unauthenticated_request_rejected(db_session):
    """Adversarial: Missing or invalid authentication token yields HTTP 401."""
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. No Authorization header at all
            r1 = await client.put("/api/v1/profile", json={"bio": "Sneak attack"})
            assert r1.status_code == 401
            assert r1.json()["error_code"] == "UNAUTHORIZED"

            # 2. Garbage Bearer token
            r2 = await client.put(
                "/api/v1/profile",
                headers={"Authorization": "Bearer invalid.jwt.token"},
                json={"bio": "Sneak attack"},
            )
            assert r2.status_code == 401
            assert r2.json()["error_code"] == "INVALID_TOKEN"

            # 3. Expired token
            expired_token = create_access_token(uuid.uuid4(), expires_delta=timedelta(seconds=-60))
            r3 = await client.put(
                "/api/v1/profile",
                headers={"Authorization": f"Bearer {expired_token}"},
                json={"bio": "Sneak attack"},
            )
            assert r3.status_code == 401
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_put_profile_revoked_token_rejected(db_session, make_user):
    """Adversarial: Token with outdated token_version yields HTTP 401 TOKEN_REVOKED."""
    user = make_user(is_profile_completed=True, token_version=2)
    db_session.add(user)
    await db_session.commit()

    # Create token with older token_version = 1
    old_token = create_access_token(user.id, token_version=1)

    app.dependency_overrides[get_db] = lambda: db_session
    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.put(
                "/api/v1/profile",
                headers={"Authorization": f"Bearer {old_token}"},
                json={"bio": "Using revoked token"},
            )
            assert resp.status_code == 401
            assert resp.json()["error_code"] == "TOKEN_REVOKED"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_put_profile_state_machine_guard(db_session, make_user):
    """Adversarial: State transitions between uncompleted and completed seekers.
    - Uncompleted seeker calling PUT /profile -> HTTP 400 PROFILE_NOT_COMPLETED
    - Completed seeker calling POST /profile/create -> HTTP 400 PROFILE_ALREADY_COMPLETED
    """
    uncompleted_user = make_user(is_profile_completed=False)
    completed_user = make_user(is_profile_completed=True)
    db_session.add_all([uncompleted_user, completed_user])
    await db_session.commit()

    token_uncompleted = create_access_token(uncompleted_user.id)
    token_completed = create_access_token(completed_user.id)

    app.dependency_overrides[get_db] = lambda: db_session
    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # Uncompleted user attempts PUT -> MUST FAIL with 400 PROFILE_NOT_COMPLETED
            r1 = await client.put(
                "/api/v1/profile",
                headers={"Authorization": f"Bearer {token_uncompleted}"},
                json={"bio": "I haven't onboarded yet"},
            )
            assert r1.status_code == 400
            assert r1.json()["error_code"] == "PROFILE_NOT_COMPLETED"

            # Completed user attempts POST /create -> MUST FAIL with 400 PROFILE_ALREADY_COMPLETED
            r2 = await client.post(
                "/api/v1/profile/create",
                headers={"Authorization": f"Bearer {token_completed}"},
                json={
                    "full_name": "Completed Seeker",
                    "dob": "1995-01-01",
                    "gender": "Man",
                    "interested_in": "Women",
                    "contact_bridge_type": "whatsapp",
                    "contact_bridge_handle": "+919876543210",
                    "photos": ["https://media.urheart.app/p1.webp"],
                },
            )
            assert r2.status_code == 400
            assert r2.json()["error_code"] == "PROFILE_ALREADY_COMPLETED"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_put_profile_immutability_of_immutable_fields(db_session, make_user):
    """Adversarial: Verify that unalterable/statutory fields (dob, id, auth_id, is_profile_completed)
    CANNOT be maliciously altered via PUT /api/v1/profile."""
    original_id = uuid.uuid4()
    original_auth_id = uuid.uuid4()
    original_dob = date(1996, 7, 20)

    user = make_user(
        id=original_id,
        auth_id=original_auth_id,
        dob=original_dob,
        is_profile_completed=True,
    )
    db_session.add(user)
    await db_session.commit()

    token = create_access_token(user.id)
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.put(
                "/api/v1/profile",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "id": str(uuid.uuid4()),  # Attempt to spoof ID
                    "auth_id": str(uuid.uuid4()),  # Attempt to rebind auth_id
                    "dob": "2005-01-01",  # Attempt to change statutory DOB
                    "is_profile_completed": False,  # Attempt to revert completion status
                    "role": "superadmin",  # Attempt privilege escalation
                    "bio": "Legitimate bio update",
                },
            )
            assert resp.status_code == 200

            # Re-fetch from DB to verify unalterable fields were NOT touched
            stmt = select(User).where(User.id == original_id)
            updated = (await db_session.execute(stmt)).scalar_one()

            assert updated.id == original_id
            assert updated.auth_id == original_auth_id
            assert updated.dob == original_dob
            assert updated.is_profile_completed is True
            assert updated.role == "user"
            assert updated.bio == "Legitimate bio update"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_put_profile_fuzzes_and_persists_coordinates_in_db(db_session, make_user):
    """Adversarial: High-precision coordinates sent in PUT /profile are fuzzed to 2 decimal places in DB."""
    user = make_user(is_profile_completed=True)
    db_session.add(user)
    await db_session.commit()

    token = create_access_token(user.id)
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # Test with location_lat / location_lon alias
            resp = await client.put(
                "/api/v1/profile",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "location_lat": 12.9715987,
                    "location_lon": 77.5945627,
                    "city": "Bengaluru, KA",
                },
            )
            assert resp.status_code == 200
            data = resp.json()["data"]
            assert data["latitude"] == 12.97
            assert data["longitude"] == 77.59
            assert data["location_name"] == "Bengaluru, KA"

            stmt = select(User).where(User.id == user.id)
            refreshed = (await db_session.execute(stmt)).scalar_one()
            assert refreshed.latitude == Decimal("12.97")
            assert refreshed.longitude == Decimal("77.59")
            assert refreshed.location_name == "Bengaluru, KA"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_put_profile_empty_body_no_op(db_session, make_user):
    """Adversarial: Sending empty JSON object {} succeeds and alters nothing."""
    user = make_user(
        full_name="Original Name",
        bio="Original Bio",
        profession="Original Profession",
        is_profile_completed=True,
    )
    db_session.add(user)
    await db_session.commit()

    token = create_access_token(user.id)
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.put(
                "/api/v1/profile",
                headers={"Authorization": f"Bearer {token}"},
                json={},
            )
            assert resp.status_code == 200
            data = resp.json()["data"]
            assert data["full_name"] == "Original Name"
            assert data["bio"] == "Original Bio"
            assert data["profession"] == "Original Profession"

            stmt = select(User).where(User.id == user.id)
            refreshed = (await db_session.execute(stmt)).scalar_one()
            assert refreshed.full_name == "Original Name"
            assert refreshed.bio == "Original Bio"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_put_profile_soft_deleted_user_rejected(db_session, make_user):
    """Adversarial: Soft-deleted user session must be rejected with HTTP 401 USER_NOT_FOUND."""
    from datetime import datetime, timezone
    user = make_user(is_profile_completed=True, deleted_at=datetime.now(timezone.utc))
    db_session.add(user)
    await db_session.commit()

    token = create_access_token(user.id)
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.put(
                "/api/v1/profile",
                headers={"Authorization": f"Bearer {token}"},
                json={"bio": "Trying to edit deleted profile"},
            )
            assert resp.status_code == 401
            assert resp.json()["error_code"] == "USER_NOT_FOUND"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_put_profile_avatar_precedence(db_session, make_user):
    """Adversarial: When both avatar_url and photos are supplied, avatar_url takes precedence."""
    user = make_user(is_profile_completed=True)
    db_session.add(user)
    await db_session.commit()

    token = create_access_token(user.id)
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.put(
                "/api/v1/profile",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "photos": ["https://media.urheart.app/photo1.webp", "https://media.urheart.app/photo2.webp"],
                    "avatar_url": "https://media.urheart.app/custom_avatar.webp",
                },
            )
            assert resp.status_code == 200
            data = resp.json()["data"]
            assert data["avatar_url"] == "https://media.urheart.app/custom_avatar.webp"

            stmt = select(User).where(User.id == user.id)
            refreshed = (await db_session.execute(stmt)).scalar_one()
            assert refreshed.avatar_url == "https://media.urheart.app/custom_avatar.webp"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_put_profile_sql_injection_resilience(db_session, make_user):
    """Adversarial: Malicious SQL injection payloads in string fields do not execute or break ORM."""
    user = make_user(is_profile_completed=True)
    db_session.add(user)
    await db_session.commit()

    token = create_access_token(user.id)
    app.dependency_overrides[get_db] = lambda: db_session

    sqli_payload = "'; DROP TABLE users; --"
    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.put(
                "/api/v1/profile",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "bio": sqli_payload,
                    "city": "Bengaluru'; SELECT * FROM users; --",
                },
            )
            assert resp.status_code == 200

            # Verify users table still exists and record is untouched except for literal text
            stmt = select(User).where(User.id == user.id)
            refreshed = (await db_session.execute(stmt)).scalar_one()
            assert refreshed.bio == sqli_payload
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_put_profile_unicode_and_emojis(db_session, make_user):
    """Adversarial: Devanagari text, Sanskrit mantras, and emojis are safely handled."""
    user = make_user(is_profile_completed=True)
    db_session.add(user)
    await db_session.commit()

    token = create_access_token(user.id)
    app.dependency_overrides[get_db] = lambda: db_session

    unicode_name = "मीरा बाई 🌸"
    unicode_bio = "ॐ भूर्भुवः स्वः तत्सवितुर्वरेण्यं । भर्गो देवस्य धीमहि धियो यो नः प्रचोदयात् ॥ 🕊️✨"

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.put(
                "/api/v1/profile",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "full_name": unicode_name,
                    "bio": unicode_bio,
                },
            )
            assert resp.status_code == 200
            data = resp.json()["data"]
            assert data["full_name"] == unicode_name
            assert data["bio"] == unicode_bio

            stmt = select(User).where(User.id == user.id)
            refreshed = (await db_session.execute(stmt)).scalar_one()
            assert refreshed.full_name == unicode_name
            assert refreshed.bio == unicode_bio
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_put_profile_southern_western_coordinates_fuzzing(db_session, make_user):
    """Adversarial: Negative latitudes (Southern hemisphere) and negative longitudes (Western hemisphere)."""
    user = make_user(is_profile_completed=True)
    db_session.add(user)
    await db_session.commit()

    token = create_access_token(user.id)
    app.dependency_overrides[get_db] = lambda: db_session

    # Rio de Janeiro: -22.9068, -43.1729
    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.put(
                "/api/v1/profile",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "latitude": -22.906847,
                    "longitude": -43.172896,
                },
            )
            assert resp.status_code == 200
            data = resp.json()["data"]
            assert data["latitude"] == -22.91
            assert data["longitude"] == -43.17

            stmt = select(User).where(User.id == user.id)
            refreshed = (await db_session.execute(stmt)).scalar_one()
            assert refreshed.latitude == Decimal("-22.91")
            assert refreshed.longitude == Decimal("-43.17")
    finally:
        app.dependency_overrides.clear()
