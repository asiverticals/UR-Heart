"""
Adversarial Media Privacy & Storage Test Suite (BNS 77 & IT Act 66E Compliance)
Validates that:
1. Incoming & mutual resonances never leak unrevealed actor photos or clear avatars (VULN-MEDIA-01).
2. Seeker profile creation and updates strictly reject cross-tenant media key hijacking (VULN-MEDIA-02).
3. Clear photos are protected behind bilateral reveal consent proxies, preventing CDN reversal (VULN-MEDIA-03).
4. Photo reveal response endpoint strictly enforces bilateral block validation (VULN-MEDIA-04).
5. KYC biometric presigned upload URLs sign Content-Length constraints (VULN-MEDIA-05).
6. Voice spark streaming redirects set strict Referrer-Policy and Cache-Control, supporting single-use tokens (VULN-MEDIA-06).
"""

import uuid
from datetime import date
from decimal import Decimal
import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_current_user
from backend.app.core.database import get_db
from backend.app.core.exceptions import SanctuaryException
from backend.app.core.security import create_access_token
from backend.app.main import app
from backend.app.models.domain.legal import BlockedUser
from backend.app.models.domain.match_and_chat import Match, Swipe
from backend.app.models.domain.revelation import PhotoRevealConsent
from backend.app.models.domain.user import User
from backend.app.services.feed_service import _mask_to_blurred_derivative
from backend.app.services.photo_reveal_service import PhotoRevealService
from backend.app.services.storage_service import (
    CloudflareR2StorageService,
    get_storage_service,
)


@pytest.fixture
def test_storage():
    return CloudflareR2StorageService(
        account_id="test-account",
        access_key_id="test-key",
        secret_access_key="test-secret",
        bucket_name="ur-heart-media",
        public_domain="https://media.urheart.app",
    )


# ---------------------------------------------------------------------------
# Test 1: Incoming Resonances Photo Masking (VULN-MEDIA-01)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_incoming_resonances_must_not_leak_unveiled_photos_or_avatar(
    db_session: AsyncSession, make_user
):
    """VULN-MEDIA-01: Assert GET /api/v1/resonances/incoming masks unrevealed actor photos and avatar."""
    recipient = make_user(full_name="Recipient Seeker", is_profile_completed=True)
    actor_id = uuid.uuid4()
    actor = make_user(
        id=actor_id,
        full_name="Actor Seeker",
        is_profile_completed=True,
        photos=[f"https://media.urheart.app/users/{actor_id}/moments/slot_1.webp"],
        avatar_url=f"https://media.urheart.app/users/{actor_id}/avatar/primary.webp",
    )
    db_session.add_all([recipient, actor])
    await db_session.commit()
    swipe = Swipe(actor_id=actor.id, target_id=recipient.id, swipe_type="like")
    db_session.add(swipe)
    await db_session.commit()

    token = create_access_token(recipient.id)
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/v1/resonances/incoming",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            data = resp.json()["data"]
            assert len(data) == 1
            item = data[0]

            # Raw unblurred photos must NEVER appear in incoming responses without reveal consent
            for photo in item.get("photos", []):
                assert not photo.endswith("slot_1.webp"), "Raw unblurred photo leaked in incoming resonances"
                assert "_blurred." in photo or photo == "", "Photos must be blurred derivative when veiled"
            if item.get("avatar_url"):
                assert "_blurred." in item["avatar_url"], "Avatar must be blurred derivative when veiled"

            # When bilateral reveal consent is accepted, raw photos are accessible
            consent = PhotoRevealConsent(
                requester_id=recipient.id,
                target_id=actor.id,
                status="accepted",
            )
            db_session.add(consent)
            await db_session.commit()

            resp_revealed = await client.get(
                "/api/v1/resonances/incoming",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp_revealed.status_code == 200
            item_rev = resp_revealed.json()["data"][0]
            assert any("slot_1.webp" in p for p in item_rev["photos"])
            assert "primary.webp" in item_rev["avatar_url"]
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test 2: Mutual Resonances Avatar Masking (VULN-MEDIA-01)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_mutual_resonances_must_not_leak_unveiled_avatar(
    db_session: AsyncSession, make_user
):
    """VULN-MEDIA-01: Assert GET /api/v1/resonances/mutual veils peer avatar unless reveal consent accepted."""
    user1 = make_user(full_name="User 1", is_profile_completed=True)
    user2 = make_user(
        full_name="User 2",
        is_profile_completed=True,
        avatar_url=f"https://media.urheart.app/users/{uuid.uuid4()}/avatar/primary.webp",
    )
    db_session.add_all([user1, user2])
    await db_session.commit()

    match = Match(
        user1_id=min(user1.id, user2.id),
        user2_id=max(user1.id, user2.id),
        is_active=True,
    )
    db_session.add(match)
    await db_session.commit()

    token = create_access_token(user1.id)
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/v1/resonances/mutual",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            data = resp.json()["data"]
            assert len(data) == 1
            peer = data[0]
            assert "_blurred." in peer["peer_avatar"], "Mutual peer avatar must be veiled without consent"
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test 3: Cross-Tenant Media Ownership Enforcement (VULN-MEDIA-02)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_profile_update_rejects_cross_tenant_media_urls(
    db_session: AsyncSession, make_user
):
    """VULN-MEDIA-02: Assert PUT /api/v1/profile rejects attempts to bind foreign user media assets."""
    attacker = make_user(full_name="Attacker", is_profile_completed=True)
    victim = make_user(full_name="Victim", is_profile_completed=True)
    db_session.add_all([attacker, victim])
    await db_session.commit()

    token = create_access_token(attacker.id)
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            # 1. Attacker attempts to bind victim's photos
            resp_photos = await client.put(
                "/api/v1/profile",
                headers={"Authorization": f"Bearer {token}"},
                json={"photos": [f"https://media.urheart.app/users/{victim.id}/moments/slot_1.webp"]},
            )
            assert resp_photos.status_code == 403
            assert resp_photos.json()["error_code"] == "CROSS_TENANT_MEDIA_FORBIDDEN"

            # 2. Attacker attempts to bind victim's avatar
            resp_avatar = await client.put(
                "/api/v1/profile",
                headers={"Authorization": f"Bearer {token}"},
                json={"avatar_url": f"https://media.urheart.app/users/{victim.id}/avatar/primary.webp"},
            )
            assert resp_avatar.status_code == 403
            assert resp_avatar.json()["error_code"] == "CROSS_TENANT_MEDIA_FORBIDDEN"

            # 3. Attacker attempts to bind victim's voice spark URL
            resp_voice = await client.put(
                "/api/v1/profile",
                headers={"Authorization": f"Bearer {token}"},
                json={"voice_spark_url": f"https://media.urheart.app/users/{victim.id}/voice/spark.m4a"},
            )
            assert resp_voice.status_code == 403
            assert resp_voice.json()["error_code"] == "CROSS_TENANT_MEDIA_FORBIDDEN"

            # 4. Attacker attempts to bind victim's voice proxy path
            resp_voice_proxy = await client.put(
                "/api/v1/profile",
                headers={"Authorization": f"Bearer {token}"},
                json={"voice_spark_url": f"/api/v1/media/voice/{victim.id}/spark.m4a"},
            )
            assert resp_voice_proxy.status_code == 403
            assert resp_voice_proxy.json()["error_code"] == "CROSS_TENANT_MEDIA_FORBIDDEN"

            # 5. Attacker can successfully bind their OWN media
            resp_own = await client.put(
                "/api/v1/profile",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "photos": [f"https://media.urheart.app/users/{attacker.id}/moments/slot_1.webp"],
                    "avatar_url": f"https://media.urheart.app/users/{attacker.id}/avatar/primary.webp",
                    "voice_spark_url": f"https://media.urheart.app/users/{attacker.id}/voice/spark.m4a",
                },
            )
            assert resp_own.status_code == 200
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test 4: Profile Create Cross-Tenant Media Ownership Enforcement (VULN-MEDIA-02)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_profile_create_rejects_cross_tenant_media_urls(
    db_session: AsyncSession, make_user
):
    """VULN-MEDIA-02: Assert POST /api/v1/profile/create rejects foreign user media keys."""
    attacker = make_user(full_name="New Attacker", is_profile_completed=False)
    victim = make_user(full_name="Victim User", is_profile_completed=True)
    db_session.add_all([attacker, victim])
    await db_session.commit()

    token = create_access_token(attacker.id)
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/profile/create",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "full_name": "Attacker Onboarding",
                    "dob": "1997-03-20",
                    "gender": "Man",
                    "interested_in": "Women",
                    "contact_bridge_type": "telegram",
                    "contact_bridge_handle": "@attacker",
                    "photos": [f"https://media.urheart.app/users/{victim.id}/moments/slot_1.webp"],
                },
            )
            assert resp.status_code == 403
            assert resp.json()["error_code"] == "CROSS_TENANT_MEDIA_FORBIDDEN"
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test 5: Bilateral Block Validation in Reveal Response (VULN-MEDIA-04)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_respond_to_photo_reveal_rejects_when_blocked(
    db_session: AsyncSession, make_user
):
    """VULN-MEDIA-04: Assert respond_to_photo_reveal rejects acceptance when parties are bilaterally blocked."""
    service = PhotoRevealService()
    user_a = make_user(full_name="User A", is_profile_completed=True)
    user_b = make_user(full_name="User B", is_profile_completed=True)
    db_session.add_all([user_a, user_b])
    await db_session.commit()

    # User A requests reveal from User B
    await service.request_photo_reveal(user_a.id, user_b.id, db_session)

    # User A blocks User B
    block = BlockedUser(blocker_id=user_a.id, blocked_id=user_b.id, reason="harassment")
    db_session.add(block)
    await db_session.commit()

    # User B attempts to accept reveal request while blocked
    with pytest.raises(SanctuaryException) as exc_info:
        await service.respond_to_photo_reveal(
            target_id=user_b.id,
            requester_id=user_a.id,
            accept=True,
            session=db_session,
        )
    assert exc_info.value.status_code == 403
    assert exc_info.value.error_code == "SEEKER_BLOCKED"


# ---------------------------------------------------------------------------
# Test 6: KYC Presigned Upload Content-Length Enforcement (VULN-MEDIA-05)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_kyc_presigned_upload_signs_content_length(
    db_session: AsyncSession, make_user, test_storage
):
    """VULN-MEDIA-05: Assert KYC presigned upload signs Content-Length constraint."""
    user = make_user(full_name="KYC User", is_profile_completed=True)
    db_session.add(user)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_storage_service] = lambda: test_storage

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/v1/kyc/presigned-upload")
            assert resp.status_code == 200
            upload_url = resp.json()["upload_url"]
            assert "content-length" in upload_url.lower(), "Presigned PUT URL must sign Content-Length"
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test 7: Voice Proxy Referrer Policy & Cache-Control (VULN-MEDIA-06)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_voice_proxy_redirect_sets_strict_referrer_policy(
    db_session: AsyncSession, make_user, test_storage
):
    """VULN-MEDIA-06: Assert 307 redirect sets Referrer-Policy and Cache-Control headers to protect token."""
    user = make_user(full_name="Voice User", is_profile_completed=True)
    db_session.add(user)
    await db_session.commit()

    app.dependency_overrides[get_storage_service] = lambda: test_storage
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False,
        ) as client:
            resp = await client.get(f"/api/v1/media/voice/{user.id}/spark.m4a")
            assert resp.status_code == 307
            assert resp.headers.get("referrer-policy") in ("no-referrer", "strict-origin-when-cross-origin")
            assert "no-store" in resp.headers.get("cache-control", "")
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test 8: Ephemeral Single-Use Audio Token (VULN-MEDIA-06)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_single_use_audio_token_issuance_and_consumption(
    db_session: AsyncSession, make_user, test_storage
):
    """VULN-MEDIA-06: Assert single-use audio tokens can only be redeemed once."""
    user = make_user(full_name="Token User", is_profile_completed=True)
    db_session.add(user)
    await db_session.commit()

    app.dependency_overrides[get_storage_service] = lambda: test_storage
    token = create_access_token(user.id)
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False,
        ) as client:
            # 1. Issue audio token
            resp_issue = await client.post(
                "/api/v1/media/voice/token",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp_issue.status_code == 200
            audio_token = resp_issue.json()["token"]

            # 2. First consumption succeeds with 307 redirect
            resp_play1 = await client.get(
                f"/api/v1/media/voice/{user.id}/spark.m4a?token={audio_token}"
            )
            assert resp_play1.status_code == 307

            # 3. Second consumption of single-use token fails with 401
            resp_play2 = await client.get(
                f"/api/v1/media/voice/{user.id}/spark.m4a?token={audio_token}"
            )
            assert resp_play2.status_code == 401
            assert "already been consumed" in resp_play2.json()["detail"]
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test 9: Access-Controlled Clear Photo Proxy & Reveal Consent (VULN-MEDIA-03)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_photo_access_proxy_requires_bilateral_reveal_consent(
    db_session: AsyncSession, make_user, test_storage
):
    """VULN-MEDIA-03: Assert GET /api/v1/media/photo/{id}/slot_1.webp requires bilateral consent."""
    user_a = make_user(full_name="User A", is_profile_completed=True)
    user_b = make_user(full_name="User B", is_profile_completed=True)
    db_session.add_all([user_a, user_b])
    await db_session.commit()

    app.dependency_overrides[get_storage_service] = lambda: test_storage
    app.dependency_overrides[get_db] = lambda: db_session
    token_a = create_access_token(user_a.id)

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False,
        ) as client:
            # 1. User A accesses User B's clear photo without consent -> 403 Forbidden
            resp_forbidden = await client.get(
                f"/api/v1/media/photo/{user_b.id}/slot_1.webp",
                headers={"Authorization": f"Bearer {token_a}"},
            )
            assert resp_forbidden.status_code == 403
            assert "Bilateral photo reveal consent required" in resp_forbidden.json()["detail"]

            # 2. Invalid filename pattern -> 400 Bad Request
            resp_bad_fn = await client.get(
                f"/api/v1/media/photo/{user_b.id}/malicious.sh",
                headers={"Authorization": f"Bearer {token_a}"},
            )
            assert resp_bad_fn.status_code == 400

            # 3. User A accesses own clear photo -> 307 Allowed
            resp_own = await client.get(
                f"/api/v1/media/photo/{user_a.id}/slot_1.webp",
                headers={"Authorization": f"Bearer {token_a}"},
            )
            assert resp_own.status_code == 307
            assert "slot_1.webp" in resp_own.headers.get("location")
            assert resp_own.headers.get("referrer-policy") in ("no-referrer", "strict-origin-when-cross-origin")
            assert "no-store" in resp_own.headers.get("cache-control", "")

            # 4. Bilateral consent accepted between A and B
            consent = PhotoRevealConsent(
                requester_id=user_a.id,
                target_id=user_b.id,
                status="accepted",
            )
            db_session.add(consent)
            await db_session.commit()

            resp_allowed = await client.get(
                f"/api/v1/media/photo/{user_b.id}/slot_1.webp",
                headers={"Authorization": f"Bearer {token_a}"},
            )
            assert resp_allowed.status_code == 307
            assert f"users/{user_b.id}/moments/slot_1.webp" in resp_allowed.headers.get("location")
            assert resp_allowed.headers.get("referrer-policy") in ("no-referrer", "strict-origin-when-cross-origin")
            assert "no-store" in resp_allowed.headers.get("cache-control", "")
    finally:
        app.dependency_overrides.clear()
