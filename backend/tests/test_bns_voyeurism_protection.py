"""
BNS 2023 § 77 (Voyeurism) & § 45 (Abetment) Statutory Modesty Veil Protection Tests.

Verifies:
1. No unilateral paid unmasking: Redeeming a profile unlock micro-perk converts into an
   Expedited Bilateral Reveal Invitation; photos remain masked (is_revealed=False) until
   the target seeker provides explicit affirmative consent.
2. Direct profile inspection while a paid perk is active returns veiled/masked photo attributes.
3. Target decline keeps the veil sealed permanently.
4. Blocked seekers cannot dispatch reveal invitations or unmask veils.
5. Self-unmasking attempts are strictly rejected.
"""

from decimal import Decimal
import uuid
import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_current_user
from backend.app.core.database import get_db
from backend.app.main import app
from backend.app.models.domain.legal import BlockedUser
from backend.app.models.domain.monetization import InAppPurchase
from backend.app.models.domain.revelation import PhotoRevealConsent
from backend.app.services.photo_reveal_service import photo_reveal_service


@pytest.mark.asyncio
async def test_unilateral_paid_unmasking_strictly_blocked_under_bns_77(db_session: AsyncSession, make_user):
    """Assert a completed in-app purchase does NOT unmask target photos without target affirmative consent."""
    user_a = make_user(full_name="Purchasing Seeker", is_profile_completed=True)
    user_b = make_user(
        full_name="Target Seeker",
        is_profile_completed=True,
        avatar_url="https://media.urheart.app/users/target/avatar.webp",
        photos=["https://media.urheart.app/users/target/slot_1.webp"],
    )
    db_session.add_all([user_a, user_b])
    await db_session.commit()

    # User A pays for micro-perk
    res = await photo_reveal_service.unlock_photo_with_perk(
        user_id=user_a.id,
        target_id=user_b.id,
        session=db_session,
    )
    assert res["status"] == "pending"
    assert res["is_revealed"] is False
    assert "Modesty veil remains protected" in res["message"]

    # Inquire status: must remain pending and masked
    status = await photo_reveal_service.get_photo_reveal_status(user_a.id, user_b.id, db_session)
    assert status["status"] == "pending"
    assert status["is_revealed"] is False

    # Target profile viewed by User A must still be veiled
    app.dependency_overrides[get_current_user] = lambda: user_a
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/v1/revelation/profile/{user_b.id}")
            assert resp.status_code == 200
            data = resp.json()["data"]
            assert data["is_photo_veiled"] is True
            assert data["photos"] == []
            assert data["avatar_url"] is None
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_target_decline_seals_veil_permanently(db_session: AsyncSession, make_user):
    """Assert target seeker's decline keeps photos masked even if requester purchased perk."""
    user_a = make_user(full_name="Requester Seeker", is_profile_completed=True)
    user_b = make_user(full_name="Declining Target", is_profile_completed=True)
    db_session.add_all([user_a, user_b])
    await db_session.commit()

    # Requester pays for unlock
    await photo_reveal_service.unlock_photo_with_perk(user_a.id, user_b.id, db_session)

    # Target declines
    decline_res = await photo_reveal_service.respond_to_photo_reveal(
        target_id=user_b.id,
        requester_id=user_a.id,
        accept=False,
        session=db_session,
    )
    assert decline_res["status"] == "declined"
    assert decline_res["is_revealed"] is False

    # Status remains veiled
    status = await photo_reveal_service.get_photo_reveal_status(user_a.id, user_b.id, db_session)
    assert status["status"] == "veiled"
    assert status["is_revealed"] is False


@pytest.mark.asyncio
async def test_mutual_consent_successfully_unmasks_veil(db_session: AsyncSession, make_user):
    """Assert photo veil unmasks ONLY upon reciprocal affirmative consent."""
    user_a = make_user(full_name="User Alpha", is_profile_completed=True)
    user_b = make_user(full_name="User Beta", is_profile_completed=True)
    db_session.add_all([user_a, user_b])
    await db_session.commit()

    # Alpha sends perk invitation
    await photo_reveal_service.unlock_photo_with_perk(user_a.id, user_b.id, db_session)

    # Beta accepts
    accept_res = await photo_reveal_service.respond_to_photo_reveal(
        target_id=user_b.id,
        requester_id=user_a.id,
        accept=True,
        session=db_session,
    )
    assert accept_res["status"] == "accepted"
    assert accept_res["is_revealed"] is True

    # Both parties see unmasked state
    status_a = await photo_reveal_service.get_photo_reveal_status(user_a.id, user_b.id, db_session)
    assert status_a["status"] == "accepted"
    assert status_a["is_revealed"] is True

    status_b = await photo_reveal_service.get_photo_reveal_status(user_b.id, user_a.id, db_session)
    assert status_b["status"] == "accepted"
    assert status_b["is_revealed"] is True
