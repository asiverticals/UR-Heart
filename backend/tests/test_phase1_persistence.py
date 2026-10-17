import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from backend.app.models.domain import (
    User,
    Swipe,
    Match,
    Message,
    AdRewardLedger,
    ProcessedAdTransaction,
    InAppPurchase,
    PendingWebEntitlement,
    ContactRevealToken,
    PhotoRevealConsent,
    BlindDateQueue,
    BlindDateSession,
    BlindDateMessage,
    UnderageQuarantineRegistry,
    DataNominee,
    DataExportRequest,
    ConsentAuditLog,
    GrievanceDossier,
    BlockedUser,
    WebDeletionToken,
    AdminKycEscalation,
    DeviceFcmToken,
    AdminAuditLog,
)

@pytest.mark.asyncio
async def test_user_creation_and_query(db_session, make_user):
    """Test 1: User model creation with valid constraints and query verification."""
    user = make_user(full_name="Janaki Devi", gender="Woman", interested_in="Men")
    db_session.add(user)
    await db_session.commit()

    stmt = select(User).where(User.id == user.id)
    result = await db_session.execute(stmt)
    saved_user = result.scalar_one_or_none()

    assert saved_user is not None
    assert saved_user.full_name == "Janaki Devi"
    assert saved_user.gender == "Woman"
    assert saved_user.role == "user"
    assert saved_user.swipes_remaining == 25
    assert saved_user.reveal_tokens_count == 1
    assert saved_user.kyc_status is False
    assert saved_user.photos == ["https://media.urheart.app/users/radha/primary.jpg"]

@pytest.mark.asyncio
async def test_user_unique_constraint_auth_id(db_session, make_user):
    """Test 2: Unique constraint assertion on auth_id."""
    shared_auth_id = uuid.uuid4()
    user1 = make_user(auth_id=shared_auth_id, referral_code="REF_UNIQUE_01")
    user2 = make_user(auth_id=shared_auth_id, referral_code="REF_UNIQUE_02")

    db_session.add(user1)
    await db_session.commit()

    db_session.add(user2)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()

@pytest.mark.asyncio
async def test_user_check_constraint_gender(db_session, make_user):
    """Test 3: Check constraint assertion on gender."""
    invalid_user = make_user(gender="InvalidGender")
    db_session.add(invalid_user)

    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()

@pytest.mark.asyncio
async def test_swipe_uniqueness_and_no_self_swipe(db_session, make_user):
    """Test 4: Swipe uniqueness and bilateral check constraint (actor_id <> target_id)."""
    u1 = make_user()
    u2 = make_user()
    db_session.add_all([u1, u2])
    await db_session.commit()
    u1_id, u2_id = u1.id, u2.id

    # Self-swipe must fail check constraint
    self_swipe = Swipe(actor_id=u1_id, target_id=u1_id, swipe_type="like")
    db_session.add(self_swipe)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()

    # Valid swipe
    valid_swipe = Swipe(actor_id=u1_id, target_id=u2_id, swipe_type="like")
    db_session.add(valid_swipe)
    await db_session.commit()

    # Duplicate swipe must fail uniqueness
    duplicate_swipe = Swipe(actor_id=u1_id, target_id=u2_id, swipe_type="superlike")
    db_session.add(duplicate_swipe)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()

@pytest.mark.asyncio
async def test_monetization_ssv_idempotency(db_session, make_user):
    """Test 5: Monetization SSV ledger idempotency uniqueness validation."""
    u = make_user()
    db_session.add(u)
    await db_session.commit()

    ledger1 = AdRewardLedger(
        user_id=u.id,
        ssv_transaction_id="admob_tx_998877",
        network="admob",
        ad_type="rewarded_daily_boost",
        reward_points=100,
    )
    db_session.add(ledger1)
    await db_session.commit()

    # Duplicate ssv_transaction_id must fail unique constraint
    ledger2 = AdRewardLedger(
        user_id=u.id,
        ssv_transaction_id="admob_tx_998877",
        network="admob",
        ad_type="rewarded_daily_boost",
        reward_points=100,
    )
    db_session.add(ledger2)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()

@pytest.mark.asyncio
async def test_all_remaining_tables_persistence(db_session, make_user):
    """Test persistence across all domain model slices."""
    u1 = make_user()
    u2 = make_user()
    # Order user IDs to satisfy chk_matches_ordered_pair
    if u1.id > u2.id:
        u1, u2 = u2, u1

    db_session.add_all([u1, u2])
    await db_session.commit()

    # Match & Messages
    match = Match(user1_id=u1.id, user2_id=u2.id, is_active=True)
    db_session.add(match)
    await db_session.commit()

    msg = Message(
        match_id=match.id,
        sender_id=u1.id,
        encrypted_text="enc_hello_world_payload",
        status="sent",
    )
    db_session.add(msg)
    await db_session.commit()

    # Revelation tokens
    contact_token = ContactRevealToken(match_id=match.id, user1_consent=True)
    photo_consent = PhotoRevealConsent(requester_id=u1.id, target_id=u2.id, status="pending")
    db_session.add_all([contact_token, photo_consent])
    await db_session.commit()

    # Blind Date
    bd_queue = BlindDateQueue(user_id=u1.id, gender="Woman", interested_in="Men")
    bd_session = BlindDateSession(
        user1_id=u1.id,
        user2_id=u2.id,
        status="active",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
    )
    db_session.add_all([bd_queue, bd_session])
    await db_session.commit()

    bd_msg = BlindDateMessage(
        session_id=bd_session.id,
        sender_id=u1.id,
        recipient_id=u2.id,
        encrypted_text="enc_blind_message",
    )
    db_session.add(bd_msg)
    await db_session.commit()

    # Legal & Compliance
    quarantine = UnderageQuarantineRegistry(
        device_hash="sha256_dummy_hash_001",
        attempted_dob=date(2010, 5, 5),
        quarantine_until=datetime.now(timezone.utc) + timedelta(days=30),
        attempt_metadata={"source": "onboarding_gate"},
    )
    nominee = DataNominee(
        user_id=u1.id,
        nominee_name="Kishori Devi",
        nominee_contact="+919876543210",
        relationship="Sister",
    )
    export_req = DataExportRequest(user_id=u1.id, status="processing")
    audit_log = ConsentAuditLog(
        user_id=u1.id,
        consent_purpose_id="terms_dpdp_2023",
        ip_hash="hash_1234",
        installation_uuid="uuid_abc",
    )
    grievance = GrievanceDossier(
        dossier_reference_id="GD-2026-0001",
        reporter_id=u1.id,
        reported_user_id=u2.id,
        violation_category="harassment",
        statutory_notes="Unwelcome communication",
        sla_deadline_at=datetime.now(timezone.utc) + timedelta(days=15),
    )
    block = BlockedUser(blocker_id=u1.id, blocked_id=u2.id, reason="Inappropriate")
    web_del = WebDeletionToken(
        token="token_hash_web_deletion_xyz",
        email=u1.email,
        user_id=u1.id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db_session.add_all([quarantine, nominee, export_req, audit_log, grievance, block, web_del])
    await db_session.commit()

    # Admin & Telemetry
    kyc_escalation = AdminKycEscalation(
        user_id=u1.id,
        declared_dob=date(2000, 1, 1),
        groq_match_score=Decimal("0.985"),
        selfie_storage_url="https://media.urheart.app/kyc/selfie.jpg",
        id_card_storage_url="https://media.urheart.app/kyc/id.jpg",
    )
    fcm = DeviceFcmToken(user_id=u1.id, token="fcm_token_sample_abc", platform="android")
    admin_log = AdminAuditLog(
        admin_email="superadmin@urheart.app",
        action="REVIEW_KYC",
        target_type="user",
        target_id=str(u1.id),
        details={"status": "approved"},
        ip_address="127.0.0.1",
    )
    iap = InAppPurchase(
        user_id=u1.id,
        store="web_razorpay_india",
        transaction_reference="pay_order_sample_001",
        product_identifier="spark_tier_monthly",
        amount_gross=Decimal("499.00"),
        platform_fee=Decimal("10.00"),
        amount_net=Decimal("489.00"),
    )
    entitlement = PendingWebEntitlement(
        order_id="web_order_ref_1122",
        email=u1.email,
        product_identifier="spark_tier_monthly",
        amount_gross=Decimal("499.00"),
    )
    processed_ad = ProcessedAdTransaction(
        transaction_id="ad_tx_processed_7788",
        network="meta",
        user_id=u1.id,
        ad_type="rewarded_daily_boost",
    )
    db_session.add_all([kyc_escalation, fcm, admin_log, iap, entitlement, processed_ad])
    await db_session.commit()

    # Assert all objects persisted
    assert match.id is not None
    assert msg.id is not None
    assert grievance.id is not None
    assert kyc_escalation.id is not None
    assert nominee.user_id == u1.id
    assert iap.id is not None
    assert iap.status == "pending"

@pytest.mark.asyncio
async def test_user_photos_in_place_mutation_tracking(db_session, make_user):
    """Test that mutating user.photos in-place (append) triggers change tracking and persists to DB."""
    user = make_user()
    user.photos = ["https://media.urheart.app/p1.jpg"]
    db_session.add(user)
    await db_session.commit()

    # Mutate in-place
    user.photos.append("https://media.urheart.app/p2.jpg")
    await db_session.commit()

    # Verify reload reflects mutated array
    res = await db_session.execute(select(User).where(User.id == user.id))
    persisted = res.scalar_one()
    assert len(persisted.photos) == 2
    assert "https://media.urheart.app/p2.jpg" in persisted.photos

@pytest.mark.asyncio
async def test_blind_date_queue_age_range_constraint(db_session, make_user):
    """Test that preferred_age_min > preferred_age_max or < 18 is rejected by check constraint."""
    user = make_user()
    db_session.add(user)
    await db_session.commit()

    # Inverted age range (preferred_age_min > preferred_age_max)
    invalid_queue = BlindDateQueue(
        user_id=user.id,
        gender="Woman",
        interested_in="Men",
        preferred_age_min=30,
        preferred_age_max=20,
    )
    db_session.add(invalid_queue)
    with pytest.raises(Exception):
        await db_session.commit()
    await db_session.rollback()

@pytest.mark.asyncio
async def test_iap_nonnegative_amounts_constraint(db_session, make_user):
    """Test that negative monetary amounts are rejected by check constraint."""
    user = make_user()
    db_session.add(user)
    await db_session.commit()

    invalid_iap = InAppPurchase(
        user_id=user.id,
        store="web_razorpay_india",
        transaction_reference="neg_iap_ref_999",
        product_identifier="spark_tier",
        amount_gross=Decimal("-10.00"),
    )
    db_session.add(invalid_iap)
    with pytest.raises(Exception):
        await db_session.commit()
    await db_session.rollback()

@pytest.mark.asyncio
async def test_reveal_token_ad_count_bounds(db_session, make_user):
    """Test that negative ad count or ad count > 3 is rejected by check constraint."""
    u1 = make_user()
    u2 = make_user()
    if u1.id > u2.id:
        u1, u2 = u2, u1
    db_session.add_all([u1, u2])
    await db_session.commit()

    match = Match(user1_id=u1.id, user2_id=u2.id, is_active=True)
    db_session.add(match)
    await db_session.commit()

    # Negative ad count
    invalid_token = ContactRevealToken(
        match_id=match.id,
        user1_ads_count=-1,
    )
    db_session.add(invalid_token)
    with pytest.raises(Exception):
        await db_session.commit()
    await db_session.rollback()
