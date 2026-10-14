import uuid
from decimal import Decimal
import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy import select

from backend.app.api.deps import get_current_user
from backend.app.core.database import get_db
from backend.app.core.exceptions import SanctuaryException
from backend.app.main import app
from backend.app.models.domain.legal import BlockedUser
from backend.app.models.domain.monetization import InAppPurchase
from backend.app.models.domain.revelation import PhotoRevealConsent
from backend.app.models.domain.user import User
from backend.app.services.photo_reveal_service import PhotoRevealService, get_photo_reveal_service

@pytest.mark.asyncio
async def test_photo_reveal_request_pending(db_session, make_user):
    """Test 1: User A requests reveal -> status is 'pending' and is_revealed is False."""
    service = PhotoRevealService()

    user_a = make_user(full_name="User A", is_profile_completed=True)
    user_b = make_user(full_name="User B", is_profile_completed=True)
    db_session.add_all([user_a, user_b])
    await db_session.commit()

    res = await service.request_photo_reveal(user_a.id, user_b.id, db_session)
    assert res["status"] == "pending"
    assert res["is_revealed"] is False
    assert res["target_id"] == user_b.id

    # Verify status via get_photo_reveal_status
    status = await service.get_photo_reveal_status(user_a.id, user_b.id, db_session)
    assert status["status"] == "pending"
    assert status["is_revealed"] is False

    # From user_b's perspective, they haven't requested, so it is veiled
    status_b = await service.get_photo_reveal_status(user_b.id, user_a.id, db_session)
    assert status_b["status"] == "veiled"
    assert status_b["is_revealed"] is False

@pytest.mark.asyncio
async def test_photo_reveal_accept(db_session, make_user):
    """Test 2: User B accepts -> status transitions to 'accepted' and is_revealed becomes True."""
    service = PhotoRevealService()

    user_a = make_user(full_name="User A", is_profile_completed=True)
    user_b = make_user(full_name="User B", is_profile_completed=True)
    db_session.add_all([user_a, user_b])
    await db_session.commit()

    # User A requests reveal
    await service.request_photo_reveal(user_a.id, user_b.id, db_session)

    # User B accepts reveal request from User A
    res = await service.respond_to_photo_reveal(
        target_id=user_b.id,
        requester_id=user_a.id,
        accept=True,
        session=db_session,
    )
    assert res["status"] == "accepted"
    assert res["is_revealed"] is True

    # Both seekers should now see unmasked photos
    status_a = await service.get_photo_reveal_status(user_a.id, user_b.id, db_session)
    assert status_a["status"] == "accepted"
    assert status_a["is_revealed"] is True

    status_b = await service.get_photo_reveal_status(user_b.id, user_a.id, db_session)
    assert status_b["status"] == "accepted"
    assert status_b["is_revealed"] is True

@pytest.mark.asyncio
async def test_photo_reveal_mutual_cross_requests(db_session, make_user):
    """Test 3: Mutual cross-requests (A requests B, B requests A) auto-resolves to 'accepted'."""
    service = PhotoRevealService()

    user_a = make_user(full_name="Seeker A", is_profile_completed=True)
    user_b = make_user(full_name="Seeker B", is_profile_completed=True)
    db_session.add_all([user_a, user_b])
    await db_session.commit()

    # User A requests reveal from User B
    res_a = await service.request_photo_reveal(user_a.id, user_b.id, db_session)
    assert res_a["status"] == "pending"
    assert res_a["is_revealed"] is False

    # User B requests reveal from User A -> automatically unmasks veil
    res_b = await service.request_photo_reveal(user_b.id, user_a.id, db_session)
    assert res_b["status"] == "accepted"
    assert res_b["is_revealed"] is True
    assert "Mutual resonance" in res_b["message"]

    # Verify both seekers have accepted reveal status
    status_a = await service.get_photo_reveal_status(user_a.id, user_b.id, db_session)
    assert status_a["status"] == "accepted"
    assert status_a["is_revealed"] is True

@pytest.mark.asyncio
async def test_photo_reveal_decline(db_session, make_user):
    """Test 4: Declining reveal sets status to 'declined' and remains veiled."""
    service = PhotoRevealService()

    user_a = make_user(full_name="Seeker A", is_profile_completed=True)
    user_b = make_user(full_name="Seeker B", is_profile_completed=True)
    db_session.add_all([user_a, user_b])
    await db_session.commit()

    await service.request_photo_reveal(user_a.id, user_b.id, db_session)

    # User B declines
    res = await service.respond_to_photo_reveal(
        target_id=user_b.id,
        requester_id=user_a.id,
        accept=False,
        session=db_session,
    )
    assert res["status"] == "declined"
    assert res["is_revealed"] is False

    status = await service.get_photo_reveal_status(user_a.id, user_b.id, db_session)
    assert status["is_revealed"] is False

@pytest.mark.asyncio
async def test_photo_reveal_idempotent_re_request(db_session, make_user):
    """Test 5: Re-requesting with existing pending record returns idempotent status without duplicate rows."""
    service = PhotoRevealService()

    user_a = make_user(full_name="Seeker A", is_profile_completed=True)
    user_b = make_user(full_name="Seeker B", is_profile_completed=True)
    db_session.add_all([user_a, user_b])
    await db_session.commit()

    res1 = await service.request_photo_reveal(user_a.id, user_b.id, db_session)
    assert res1["status"] == "pending"

    # Second call returns existing pending record without crashing
    res2 = await service.request_photo_reveal(user_a.id, user_b.id, db_session)
    assert res2["status"] == "pending"
    assert res2["is_revealed"] is False

    # Check only 1 record exists in table
    records = (
        await db_session.execute(
            select(PhotoRevealConsent).where(
                PhotoRevealConsent.requester_id == user_a.id,
                PhotoRevealConsent.target_id == user_b.id,
            )
        )
    ).scalars().all()
    assert len(records) == 1

@pytest.mark.asyncio
async def test_photo_reveal_validations(db_session, make_user):
    """Test 6 & 7: Rejects self-reveal requests and interactions between bilaterally blocked seekers."""
    service = PhotoRevealService()

    user_a = make_user(full_name="Seeker A", is_profile_completed=True)
    user_b = make_user(full_name="Seeker B", is_profile_completed=True)
    db_session.add_all([user_a, user_b])
    await db_session.commit()

    # Self-reveal
    with pytest.raises(SanctuaryException) as exc_self:
        await service.request_photo_reveal(user_a.id, user_a.id, db_session)
    assert exc_self.value.error_code == "CANNOT_REVEAL_SELF"
    assert exc_self.value.status_code == 400

    # Non-existent target
    random_id = uuid.uuid4()
    with pytest.raises(SanctuaryException) as exc_404:
        await service.request_photo_reveal(user_a.id, random_id, db_session)
    assert exc_404.value.error_code == "TARGET_NOT_FOUND"
    assert exc_404.value.status_code == 404

    # Blocked seekers
    block = BlockedUser(blocker_id=user_b.id, blocked_id=user_a.id, reason="harassment")
    db_session.add(block)
    await db_session.commit()

    with pytest.raises(SanctuaryException) as exc_blocked:
        await service.request_photo_reveal(user_a.id, user_b.id, db_session)
    assert exc_blocked.value.error_code == "SEEKER_BLOCKED"
    assert exc_blocked.value.status_code == 403

@pytest.mark.asyncio
async def test_photo_reveal_micro_perk_unlock(db_session, make_user):
    """Test 8: Micro-perk purchase unlocks photo veil with status='purchased_unlock'."""
    service = PhotoRevealService()

    user_a = make_user(full_name="Seeker A", is_profile_completed=True)
    user_b = make_user(full_name="Seeker B", is_profile_completed=True)
    db_session.add_all([user_a, user_b])
    await db_session.commit()

    # User A unlocks User B with ₹39 micro-perk
    res = await service.unlock_photo_with_perk(user_a.id, user_b.id, db_session)
    assert res["status"] == "purchased_unlock"
    assert res["is_revealed"] is True

    # Status check confirms unmasking
    status = await service.get_photo_reveal_status(user_a.id, user_b.id, db_session)
    assert status["status"] == "purchased_unlock"
    assert status["is_revealed"] is True

@pytest.mark.asyncio
async def test_photo_reveal_api_endpoints(db_session, make_user):
    """Test 9: FastAPI endpoints /request, /respond, /status, /unlock-perk, and /profile integration."""
    user_a = make_user(
        full_name="Ananya Seeker",
        is_profile_completed=True,
        latitude=Decimal("26.79"),
        longitude=Decimal("82.20"),
    )
    user_b = make_user(
        full_name="Devendra Seeker",
        is_profile_completed=True,
        avatar_url="https://media.urheart.app/users/devendra/avatar.webp",
        latitude=Decimal("26.85"),
        longitude=Decimal("80.95"),
    )
    db_session.add_all([user_a, user_b])
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user_a
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Request reveal
            req_res = await client.post(
                "/api/v1/revelation/photo/request",
                json={"target_id": str(user_b.id)},
            )
            assert req_res.status_code == 200
            assert req_res.json()["data"]["status"] == "pending"
            assert req_res.json()["data"]["is_revealed"] is False

            # 2. Check status
            st_res = await client.get(f"/api/v1/revelation/photo/status/{user_b.id}")
            assert st_res.status_code == 200
            assert st_res.json()["data"]["status"] == "pending"
            assert st_res.json()["data"]["is_revealed"] is False

            # 3. Get public profile (still veiled: withhold raw photos and avatar)
            prof_res = await client.get(f"/api/v1/revelation/profile/{user_b.id}")
            assert prof_res.status_code == 200
            prof_data = prof_res.json()["data"]
            assert prof_data["full_name"] == "Devendra Seeker"
            assert prof_data["is_photo_veiled"] is True
            assert prof_data["photos"] == []
            assert prof_data["avatar_url"] is None
            assert prof_data["distance_km"] is not None

            # 4. Switch auth context to User B and respond with accept
            app.dependency_overrides[get_current_user] = lambda: user_b
            resp_res = await client.post(
                "/api/v1/revelation/photo/respond",
                json={"requester_id": str(user_a.id), "accept": True},
            )
            assert resp_res.status_code == 200
            assert resp_res.json()["data"]["status"] == "accepted"
            assert resp_res.json()["data"]["is_revealed"] is True

            # 5. Switch back to User A: profile is now unmasked with photos
            app.dependency_overrides[get_current_user] = lambda: user_a
            prof_res2 = await client.get(f"/api/v1/revelation/profile/{user_b.id}")
            assert prof_res2.status_code == 200
            assert prof_res2.json()["data"]["is_photo_veiled"] is False
            assert len(prof_res2.json()["data"]["photos"]) == 1
            assert prof_res2.json()["data"]["avatar_url"] is not None

            # 6. Test micro-perk unlock endpoint with purchase reference
            user_c = make_user(full_name="Third Seeker", is_profile_completed=True)
            db_session.add(user_c)
            await db_session.commit()

            tx_token = "pay_razorpay_mock_12345678"
            perk_res = await client.post(
                "/api/v1/revelation/photo/unlock-perk",
                json={"target_id": str(user_c.id), "purchase_reference": tx_token},
            )
            assert perk_res.status_code == 200
            assert perk_res.json()["data"]["status"] == "purchased_unlock"
            assert perk_res.json()["data"]["is_revealed"] is True

            # 7. Test purchase reference replay prevention (reject reused reference)
            perk_replay_res = await client.post(
                "/api/v1/revelation/photo/unlock-perk",
                json={"target_id": str(user_c.id), "purchase_reference": tx_token},
            )
            assert perk_replay_res.status_code == 400
            assert "PURCHASE_REFERENCE_ALREADY_USED" in perk_replay_res.json()["error_code"]

            # 8. Test blocked seeker cannot unlock photos via perk
            user_d = make_user(full_name="Blocked Seeker", is_profile_completed=True)
            db_session.add(user_d)
            await db_session.commit()
            block_rec = BlockedUser(blocker_id=user_d.id, blocked_id=user_a.id, reason="harassment")
            db_session.add(block_rec)
            await db_session.commit()

            perk_blocked_res = await client.post(
                "/api/v1/revelation/photo/unlock-perk",
                json={"target_id": str(user_d.id), "purchase_reference": "pay_mock_blocked_99"},
            )
            assert perk_blocked_res.status_code == 403
            assert perk_blocked_res.json()["error_code"] == "SEEKER_BLOCKED"

            # 9. Test get_photo_reveal_status returns veiled if blocked
            status_blocked_res = await client.get(f"/api/v1/revelation/photo/status/{user_d.id}")
            assert status_blocked_res.status_code == 200
            assert status_blocked_res.json()["data"]["status"] == "veiled"
            assert status_blocked_res.json()["data"]["is_revealed"] is False
    finally:
        app.dependency_overrides.clear()
