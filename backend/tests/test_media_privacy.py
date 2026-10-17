import uuid
from datetime import date
import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.security import create_access_token
from backend.app.main import app
from backend.app.models.domain.match_and_chat import Match
from backend.app.models.domain.revelation import PhotoRevealConsent
from backend.app.models.domain.user import User
from backend.app.services.feed_service import FeedService, _mask_to_blurred_derivative
from backend.app.services.storage_service import (
    CloudflareR2StorageService,
    get_storage_service,
)

@pytest.fixture
def test_storage():
    """Generates a configured test CloudflareR2StorageService instance."""
    return CloudflareR2StorageService(
        account_id="test-account",
        access_key_id="test-key",
        secret_access_key="test-secret",
        bucket_name="ur-heart-media",
        public_domain="https://media.urheart.app",
    )

# ---------------------------------------------------------------------------
# 1. Modesty Veil Photo Blur Derivative Unit & Service Tests
# ---------------------------------------------------------------------------

def test_mask_to_blurred_derivative_behavior():
    """Unit test: _mask_to_blurred_derivative converts photo URLs to blurred thumbnails idempotently."""
    assert _mask_to_blurred_derivative(None) is None
    assert _mask_to_blurred_derivative("") is None

    # Standard extension transformation
    raw_webp = "https://media.urheart.app/users/u1/moments/slot_1.webp"
    blurred_webp = _mask_to_blurred_derivative(raw_webp)
    assert blurred_webp == "https://media.urheart.app/users/u1/moments/slot_1_blurred.webp"

    # Other extensions (.jpg, .png)
    raw_jpg = "https://media.urheart.app/users/u1/avatar/primary.jpg"
    assert _mask_to_blurred_derivative(raw_jpg) == "https://media.urheart.app/users/u1/avatar/primary_blurred.jpg"

    # Idempotent: does not double-append _blurred
    assert _mask_to_blurred_derivative(blurred_webp) == blurred_webp

    # FeedService staticmethod alias
    assert FeedService.mask_to_blurred_derivative(raw_webp) == blurred_webp


@pytest.mark.asyncio
async def test_discovery_feed_masks_photos_when_veiled(db_session: AsyncSession, make_user):
    """Assert discovery feed returns _blurred.webp and NEVER raw CDN URLs when is_photo_veiled == True."""
    feed_svc = FeedService()
    seeker = make_user(full_name="Seeker", gender="Woman", interested_in="Men", is_profile_completed=True, swipes_remaining=10)
    candidate_id = uuid.uuid4()
    candidate = make_user(
        id=candidate_id,
        full_name="Candidate Seeker",
        gender="Man",
        interested_in="Women",
        is_profile_completed=True,
        photos=[
            f"https://media.urheart.app/users/{candidate_id}/moments/slot_1.webp",
            f"https://media.urheart.app/users/{candidate_id}/moments/slot_2.jpg",
        ],
        avatar_url=f"https://media.urheart.app/users/{candidate_id}/avatar/primary.webp",
        voice_spark_url=f"https://media.urheart.app/users/{candidate_id}/voice/spark.m4a",
    )
    db_session.add_all([seeker, candidate])
    await db_session.commit()

    feed = await feed_svc.get_discovery_feed(seeker, db_session)
    assert len(feed) == 1
    prof = feed[0]

    # Verify photo veil masking
    assert prof["is_photo_veiled"] is True
    assert len(prof["photos"]) == 2

    # Assert blurred derivatives are returned
    assert prof["photos"][0] == f"https://media.urheart.app/users/{candidate_id}/moments/slot_1_blurred.webp"
    assert prof["photos"][1] == f"https://media.urheart.app/users/{candidate_id}/moments/slot_2_blurred.jpg"
    assert prof["avatar_url"] == f"https://media.urheart.app/users/{candidate_id}/avatar/primary_blurred.webp"

    # Assert raw CDN URLs are NEVER exposed in cleartext
    assert f"slot_1.webp" not in prof["photos"][0]
    assert f"slot_2.jpg" not in prof["photos"][1]
    assert f"primary.webp" not in prof["avatar_url"]


# ---------------------------------------------------------------------------
# 2. Voice Spark Proxy Protection in Feed and Revelation Endpoints
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_discovery_feed_voice_spark_proxy_protection(db_session: AsyncSession, make_user):
    """Assert discovery feed replaces raw public CDN voice URLs with authenticated streaming proxy."""
    feed_svc = FeedService()
    seeker = make_user(full_name="Seeker", gender="Woman", interested_in="Men", is_profile_completed=True, swipes_remaining=10)
    candidate_id = uuid.uuid4()
    raw_cdn_audio = f"https://media.urheart.app/users/{candidate_id}/voice/spark.m4a"

    candidate = make_user(
        id=candidate_id,
        full_name="Voice Candidate",
        gender="Man",
        interested_in="Women",
        is_profile_completed=True,
        voice_spark_url=raw_cdn_audio,
    )
    db_session.add_all([seeker, candidate])
    await db_session.commit()

    feed = await feed_svc.get_discovery_feed(seeker, db_session)
    assert len(feed) == 1
    prof = feed[0]

    # Assert proxy endpoint format
    expected_proxy = f"/api/v1/media/voice/{candidate_id}/spark.m4a"
    assert prof["voice_spark_url"] == expected_proxy

    # Assert raw CDN URL is NEVER returned
    assert "https://media.urheart.app" not in prof["voice_spark_url"]
    assert prof["voice_spark_url"] != raw_cdn_audio


@pytest.mark.asyncio
async def test_discovery_feed_http_endpoint_media_privacy(db_session: AsyncSession, make_user):
    """Assert GET /api/v1/feed HTTP endpoint returns masked photos and proxy voice spark."""
    seeker = make_user(full_name="Seeker", gender="Woman", interested_in="Men", is_profile_completed=True, swipes_remaining=10)
    candidate_id = uuid.uuid4()
    candidate = make_user(
        id=candidate_id,
        full_name="HTTP Candidate",
        gender="Man",
        interested_in="Women",
        is_profile_completed=True,
        photos=[f"https://media.urheart.app/users/{candidate_id}/moments/slot_1.webp"],
        avatar_url=f"https://media.urheart.app/users/{candidate_id}/avatar/primary.webp",
        voice_spark_url=f"https://media.urheart.app/users/{candidate_id}/voice/spark.m4a",
    )
    db_session.add_all([seeker, candidate])
    await db_session.commit()

    token = create_access_token(seeker.id)
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
            headers={"Authorization": f"Bearer {token}"},
        ) as client:
            resp = await client.get("/api/v1/feed")
            assert resp.status_code == 200
            feed_data = resp.json()["profiles"]
            assert len(feed_data) == 1
            prof = feed_data[0]

            assert prof["is_photo_veiled"] is True
            assert prof["photos"][0].endswith("_blurred.webp")
            assert "slot_1.webp" not in prof["photos"][0]
            assert prof["avatar_url"].endswith("_blurred.webp")
            assert "primary.webp" not in prof["avatar_url"]

            assert prof["voice_spark_url"] == f"/api/v1/media/voice/{candidate_id}/spark.m4a"
            assert "https://media.urheart.app" not in prof["voice_spark_url"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_revelation_profile_voice_spark_proxy_protection(db_session: AsyncSession, make_user, test_storage):
    """Assert GET /api/v1/revelation/profile/{id} returns proxy path and NEVER raw CDN voice URL."""
    seeker = make_user(full_name="Seeker", is_profile_completed=True)
    target_id = uuid.uuid4()
    raw_cdn_audio = f"https://media.urheart.app/users/{target_id}/voice/spark.m4a"

    target = make_user(
        id=target_id,
        full_name="Target Seeker",
        is_profile_completed=True,
        photos=[f"https://media.urheart.app/users/{target_id}/moments/slot_1.webp"],
        avatar_url=f"https://media.urheart.app/users/{target_id}/avatar/primary.webp",
        voice_spark_url=raw_cdn_audio,
    )
    db_session.add_all([seeker, target])
    await db_session.commit()

    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_storage_service] = lambda: test_storage

    token = create_access_token(seeker.id)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
            headers={"Authorization": f"Bearer {token}"},
        ) as client:
            resp = await client.get(f"/api/v1/revelation/profile/{target_id}")
            assert resp.status_code == 200
            data = resp.json()["data"]

            # Unrevealed profile masks photos
            assert data["is_photo_veiled"] is True
            assert data["photos"] == []
            assert data["avatar_url"] is None

            # Voice spark is served via authenticated proxy path, NEVER raw CDN
            expected_proxy = f"/api/v1/media/voice/{target_id}/spark.m4a"
            assert data["voice_spark_url"] == expected_proxy
            assert "https://media.urheart.app" not in data["voice_spark_url"]

            # Now test revealed state: create bilateral photo consent
            consent = PhotoRevealConsent(
                requester_id=seeker.id,
                target_id=target_id,
                status="accepted",
            )
            db_session.add(consent)
            await db_session.commit()

            resp_rev = await client.get(f"/api/v1/revelation/profile/{target_id}")
            assert resp_rev.status_code == 200
            data_rev = resp_rev.json()["data"]

            assert data_rev["is_photo_veiled"] is False
            # Voice spark remains protected behind authenticated proxy even when photos are revealed
            assert data_rev["voice_spark_url"] == expected_proxy
            assert "https://media.urheart.app" not in data_rev["voice_spark_url"]
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 3. Media Voice Streaming Proxy Authentication & Authorization Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_voice_proxy_authentication_enforcement(db_session: AsyncSession, make_user, test_storage):
    """Assert streaming proxy rejects unauthenticated requests or invalid tokens with HTTP 401."""
    user = make_user(full_name="User", is_profile_completed=True)
    db_session.add(user)
    await db_session.commit()

    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_storage_service] = lambda: test_storage

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False,
        ) as client:
            # 1. No credentials and no query param token -> 401
            resp_no_auth = await client.get(f"/api/v1/media/voice/{user.id}/spark.m4a")
            assert resp_no_auth.status_code == 401

            # 2. Invalid Bearer token -> 401
            resp_bad_bearer = await client.get(
                f"/api/v1/media/voice/{user.id}/spark.m4a",
                headers={"Authorization": "Bearer not.a.valid.jwt"},
            )
            assert resp_bad_bearer.status_code == 401

            # 3. Invalid query param token -> 401
            resp_bad_query = await client.get(
                f"/api/v1/media/voice/{user.id}/spark.m4a?token=not.a.valid.jwt"
            )
            assert resp_bad_query.status_code == 401
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_voice_proxy_self_access_via_bearer_and_query_param(db_session: AsyncSession, make_user, test_storage):
    """Assert streaming proxy allows seeker self-access via both Bearer header and ?token= query parameter."""
    user = make_user(full_name="Self Seeker", is_profile_completed=True)
    db_session.add(user)
    await db_session.commit()

    token = create_access_token(user.id)

    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_storage_service] = lambda: test_storage

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False,
        ) as client:
            # 1. Self access via Bearer header
            resp_bearer = await client.get(
                f"/api/v1/media/voice/{user.id}/spark.m4a",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp_bearer.status_code == 307
            location_bearer = resp_bearer.headers.get("location")
            assert f"users/{user.id}/voice/spark.m4a" in location_bearer
            assert "X-Amz-Signature=" in location_bearer

            # 2. Self access via query parameter token
            resp_query = await client.get(
                f"/api/v1/media/voice/{user.id}/spark.m4a?token={token}"
            )
            assert resp_query.status_code == 307
            location_query = resp_query.headers.get("location")
            assert f"users/{user.id}/voice/spark.m4a" in location_query
            assert "X-Amz-Signature=" in location_query
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_voice_proxy_authorization_matched_vs_unmatched(db_session: AsyncSession, make_user, test_storage):
    """Assert streaming proxy allows active mutual match access and rejects unmatched seekers with HTTP 403."""
    user_a = make_user(full_name="User A", is_profile_completed=True)
    user_b = make_user(full_name="User B (Matched)", is_profile_completed=True)
    user_c = make_user(full_name="User C (Unmatched)", is_profile_completed=True)
    user_d = make_user(full_name="User D (Inactive Match)", is_profile_completed=True)

    db_session.add_all([user_a, user_b, user_c, user_d])
    await db_session.flush()

    # Active match between A and B
    active_match = Match(
        user1_id=min(user_a.id, user_b.id),
        user2_id=max(user_a.id, user_b.id),
        is_active=True,
    )
    # Inactive/closed match between A and D
    inactive_match = Match(
        user1_id=min(user_a.id, user_d.id),
        user2_id=max(user_a.id, user_d.id),
        is_active=False,
    )
    db_session.add_all([active_match, inactive_match])
    await db_session.commit()

    token_a = create_access_token(user_a.id)

    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_storage_service] = lambda: test_storage

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False,
        ) as client:
            # 1. User A accesses matched User B via Bearer header -> 307
            resp_matched_bearer = await client.get(
                f"/api/v1/media/voice/{user_b.id}/spark.m4a",
                headers={"Authorization": f"Bearer {token_a}"},
            )
            assert resp_matched_bearer.status_code == 307
            assert f"users/{user_b.id}/voice/spark.m4a" in resp_matched_bearer.headers.get("location")

            # 2. User A accesses matched User B via ?token= query parameter -> 307
            resp_matched_query = await client.get(
                f"/api/v1/media/voice/{user_b.id}/spark.m4a?token={token_a}"
            )
            assert resp_matched_query.status_code == 307
            assert f"users/{user_b.id}/voice/spark.m4a" in resp_matched_query.headers.get("location")

            # 3. User A accesses unmatched User C -> 403 Forbidden
            resp_unmatched = await client.get(
                f"/api/v1/media/voice/{user_c.id}/spark.m4a",
                headers={"Authorization": f"Bearer {token_a}"},
            )
            assert resp_unmatched.status_code == 403
            assert "Unauthorized" in resp_unmatched.json()["detail"]

            # 4. User A accesses inactive match User D -> 403 Forbidden
            resp_inactive = await client.get(
                f"/api/v1/media/voice/{user_d.id}/spark.m4a",
                headers={"Authorization": f"Bearer {token_a}"},
            )
            assert resp_inactive.status_code == 403

            # 5. Invalid filename rejected -> 400 Bad Request
            resp_invalid_fn = await client.get(
                f"/api/v1/media/voice/{user_a.id}/malicious_file.sh",
                headers={"Authorization": f"Bearer {token_a}"},
            )
            assert resp_invalid_fn.status_code == 400
            assert "Invalid voice spark asset requested." in resp_invalid_fn.json()["detail"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_voice_proxy_rejects_revoked_session_token(db_session: AsyncSession, make_user, test_storage):
    """Assert streaming proxy rejects tokens with stale token_version after session revocation."""
    user = make_user(full_name="Revoked Seeker", is_profile_completed=True)
    user.token_version = 1
    db_session.add(user)
    await db_session.commit()

    old_token = create_access_token(user.id, token_version=1)

    # Invalidate session by incrementing token_version in db
    user.token_version = 2
    await db_session.commit()

    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_storage_service] = lambda: test_storage

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False,
        ) as client:
            # Rejection via Bearer header
            resp_bearer = await client.get(
                f"/api/v1/media/voice/{user.id}/spark.m4a",
                headers={"Authorization": f"Bearer {old_token}"},
            )
            assert resp_bearer.status_code == 401

            # Rejection via query param
            resp_query = await client.get(
                f"/api/v1/media/voice/{user.id}/spark.m4a?token={old_token}"
            )
            assert resp_query.status_code == 401
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_discovery_feed_handles_empty_photos_and_null_avatar(db_session: AsyncSession, make_user):
    """Assert feed cleanly handles candidate with empty photos and null avatar without errors."""
    feed_svc = FeedService()
    seeker = make_user(full_name="Seeker", gender="Woman", interested_in="Men", is_profile_completed=True, swipes_remaining=10)
    candidate_id = uuid.uuid4()
    candidate = make_user(
        id=candidate_id,
        full_name="Empty Photos Candidate",
        gender="Man",
        interested_in="Women",
        is_profile_completed=True,
        photos=[],
        avatar_url=None,
        voice_spark_url=None,
    )
    db_session.add_all([seeker, candidate])
    await db_session.commit()

    feed = await feed_svc.get_discovery_feed(seeker, db_session)
    assert len(feed) == 1
    prof = feed[0]

    assert prof["is_photo_veiled"] is True
    assert prof["photos"] == []
    assert prof["avatar_url"] is None
    assert prof["voice_spark_url"] is None
