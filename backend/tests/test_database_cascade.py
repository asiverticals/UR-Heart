import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from sqlalchemy import select
from backend.app.models.domain import (
    User,
    Swipe,
    Match,
    Message,
    AdRewardLedger,
    DataNominee,
    GrievanceDossier,
    BlockedUser,
    DeviceFcmToken,
    WebDeletionToken,
    InAppPurchase,
)

@pytest.mark.asyncio
async def test_user_cascade_deletions(db_session, make_user):
    """Test that deleting a User cascades deletion to all associated relational rows."""
    u1 = make_user()
    u2 = make_user()
    if u1.id > u2.id:
        u1, u2 = u2, u1

    db_session.add_all([u1, u2])
    await db_session.commit()

    # 1. Swipes
    swipe = Swipe(actor_id=u1.id, target_id=u2.id, swipe_type="like")
    db_session.add(swipe)

    # 2. Match and Message
    match = Match(user1_id=u1.id, user2_id=u2.id, is_active=True)
    db_session.add(match)
    await db_session.flush()

    msg = Message(match_id=match.id, sender_id=u1.id, encrypted_text="enc_cascade_test")
    db_session.add(msg)

    # 3. AdRewardLedger
    ledger = AdRewardLedger(
        user_id=u1.id,
        ssv_transaction_id="cascade_ssv_123",
        network="meta",
        ad_type="rewarded_daily_boost",
        reward_points=50,
    )
    db_session.add(ledger)

    # 4. DataNominee
    nominee = DataNominee(
        user_id=u1.id,
        nominee_name="Nominee Person",
        nominee_contact="+919800000000",
        relationship="Brother",
    )
    db_session.add(nominee)

    # 5. BlockedUser
    block = BlockedUser(blocker_id=u1.id, blocked_id=u2.id, reason="Testing cascade")
    db_session.add(block)

    # 6. DeviceFcmToken
    fcm = DeviceFcmToken(user_id=u1.id, token="token_cascade_fcm_1", platform="ios")
    db_session.add(fcm)

    # 7. WebDeletionToken
    web_del = WebDeletionToken(
        token="token_cascade_web_del_1",
        email=u1.email,
        user_id=u1.id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db_session.add(web_del)

    await db_session.commit()

    # Delete User u1
    await db_session.delete(u1)
    await db_session.commit()

    # Verify u1 is gone
    res_u1 = await db_session.execute(select(User).where(User.id == u1.id))
    assert res_u1.scalar_one_or_none() is None

    # Verify u2 remains
    res_u2 = await db_session.execute(select(User).where(User.id == u2.id))
    assert res_u2.scalar_one_or_none() is not None

    # Verify all cascaded rows are purged
    res_swipes = await db_session.execute(select(Swipe).where(Swipe.actor_id == u1.id))
    assert res_swipes.scalar_one_or_none() is None

    res_matches = await db_session.execute(select(Match).where(Match.id == match.id))
    assert res_matches.scalar_one_or_none() is None

    res_messages = await db_session.execute(select(Message).where(Message.id == msg.id))
    assert res_messages.scalar_one_or_none() is None

    res_ledger = await db_session.execute(select(AdRewardLedger).where(AdRewardLedger.user_id == u1.id))
    assert res_ledger.scalar_one_or_none() is None

    res_nominee = await db_session.execute(select(DataNominee).where(DataNominee.user_id == u1.id))
    assert res_nominee.scalar_one_or_none() is None

    res_block = await db_session.execute(select(BlockedUser).where(BlockedUser.blocker_id == u1.id))
    assert res_block.scalar_one_or_none() is None

    res_fcm = await db_session.execute(select(DeviceFcmToken).where(DeviceFcmToken.user_id == u1.id))
    assert res_fcm.scalar_one_or_none() is None

    res_web_del = await db_session.execute(select(WebDeletionToken).where(WebDeletionToken.user_id == u1.id))
    assert res_web_del.scalar_one_or_none() is None

@pytest.mark.asyncio
async def test_on_delete_set_null_preservation(db_session, make_user):
    """Test that ON DELETE SET NULL preserves records (GrievanceDossier, Match closer)."""
    u1 = make_user()
    u2 = make_user()
    if u1.id > u2.id:
        u1, u2 = u2, u1

    closer = make_user()
    db_session.add_all([u1, u2, closer])
    await db_session.commit()

    # Match closed by 'closer'
    match = Match(
        user1_id=u1.id,
        user2_id=u2.id,
        is_active=False,
        closure_status="closed_with_grace",
        closed_by_user_id=closer.id,
    )
    db_session.add(match)

    # Grievance dossier reported by u1 against u2
    dossier = GrievanceDossier(
        dossier_reference_id="GD-CASCADE-001",
        reporter_id=u1.id,
        reported_user_id=u2.id,
        violation_category="fraud",
        statutory_notes="Suspicious financial request",
        sla_deadline_at=datetime.now(timezone.utc) + timedelta(days=15),
    )
    # InAppPurchase made by u1
    iap = InAppPurchase(
        user_id=u1.id,
        store="web_razorpay_india",
        transaction_reference="cascade_iap_ref_001",
        product_identifier="spark_tier_monthly",
        amount_gross=Decimal("499.00"),
        platform_fee=Decimal("10.00"),
        amount_net=Decimal("489.00"),
    )
    db_session.add_all([dossier, iap])
    await db_session.commit()

    match_id = match.id
    dossier_id = dossier.id
    iap_id = iap.id

    # Delete closer user
    await db_session.delete(closer)
    await db_session.commit()

    # Refresh match from DB to observe ON DELETE SET NULL on closed_by_user_id
    await db_session.refresh(match)
    assert match.closed_by_user_id is None

    # Delete user u1
    await db_session.delete(u1)
    await db_session.commit()

    # Grievance dossier still exists per IT Rules 2021 statutory requirement, reporter_id is NULL
    await db_session.refresh(dossier)
    assert dossier.reporter_id is None
    assert dossier.reported_user_id == u2.id

    # InAppPurchase still exists per statutory tax/financial compliance, user_id is NULL
    await db_session.refresh(iap)
    assert iap.user_id is None
    assert iap.transaction_reference == "cascade_iap_ref_001"
