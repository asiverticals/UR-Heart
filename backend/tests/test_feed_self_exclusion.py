import math
import uuid
from datetime import date, datetime, timedelta, timezone
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
from backend.app.models.domain.match_and_chat import Match, Swipe
from backend.app.models.domain.revelation import ContactRevealToken
from backend.app.models.domain.user import User
from backend.app.services.feed_service import FeedService, get_feed_service


@pytest.mark.asyncio
async def test_coordinate_fuzzing_and_haversine():
    """Test 1: Coordinate fuzzing sanitizes raw GPS coordinates to 2 decimal places and clamps distance."""
    feed_svc = FeedService()

    # Raw GPS coordinates in Ayodhya
    raw_lat = 26.792194
    raw_lon = 82.199821

    fuzzed_lat, fuzzed_lon = feed_svc.fuzz_coordinates(raw_lat, raw_lon)
    assert fuzzed_lat == 26.79
    assert fuzzed_lon == 82.20

    # Test clamping: very close coordinates (< 0.5 km) must clamp to 0.5 km
    dist_close = feed_svc.calculate_haversine_distance(26.79, 82.20, 26.7901, 82.2001)
    assert dist_close >= 0.5
    assert dist_close == 0.5

    # Test real distance between Ayodhya (26.79, 82.20) and Lucknow (26.85, 80.95) ~124 km
    dist_far = feed_svc.calculate_haversine_distance(26.79, 82.20, 26.85, 80.95)
    assert 120.0 <= dist_far <= 130.0


@pytest.mark.asyncio
async def test_feed_self_exclusion_perimeter(db_session, make_user):
    """Test 2: Discovery query excludes self, past swiped profiles (<30d), blocked seekers, and incognito seekers."""
    feed_svc = FeedService()

    current_user = make_user(
        full_name="Current Seeker",
        gender="Man",
        interested_in="Women",
        is_profile_completed=True,
        swipes_remaining=10,
        latitude=Decimal("26.79"),
        longitude=Decimal("82.20"),
    )
    db_session.add(current_user)

    # 1. Valid Candidate (Woman interested in Men)
    valid_candidate = make_user(
        full_name="Valid Candidate",
        gender="Woman",
        interested_in="Men",
        is_profile_completed=True,
        is_incognito=False,
        latitude=Decimal("26.80"),
        longitude=Decimal("82.21"),
    )
    db_session.add(valid_candidate)

    # 2. Incomplete Profile
    incomplete_candidate = make_user(
        full_name="Incomplete Candidate",
        gender="Woman",
        interested_in="Men",
        is_profile_completed=False,
    )
    db_session.add(incomplete_candidate)

    # 3. Incognito Seeker
    incognito_candidate = make_user(
        full_name="Incognito Seeker",
        gender="Woman",
        interested_in="Men",
        is_profile_completed=True,
        is_incognito=True,
    )
    db_session.add(incognito_candidate)

    # 4. Swiped Candidate (swiped 5 days ago)
    swiped_candidate = make_user(
        full_name="Swiped Candidate",
        gender="Woman",
        interested_in="Men",
        is_profile_completed=True,
    )
    db_session.add(swiped_candidate)

    # 5. Blocked Candidate (blocked by current_user)
    blocked_candidate = make_user(
        full_name="Blocked Candidate",
        gender="Woman",
        interested_in="Men",
        is_profile_completed=True,
    )
    db_session.add(blocked_candidate)

    # 6. Blocker Candidate (blocked current_user)
    blocker_candidate = make_user(
        full_name="Blocker Candidate",
        gender="Woman",
        interested_in="Men",
        is_profile_completed=True,
    )
    db_session.add(blocker_candidate)

    # 7. Active Match Partner
    match_candidate = make_user(
        full_name="Matched Candidate",
        gender="Woman",
        interested_in="Men",
        is_profile_completed=True,
    )
    db_session.add(match_candidate)

    await db_session.commit()

    # Record swipe on swiped_candidate
    swipe = Swipe(
        actor_id=current_user.id,
        target_id=swiped_candidate.id,
        swipe_type="pass",
        created_at=datetime.now(timezone.utc) - timedelta(days=5),
    )
    db_session.add(swipe)

    # Record block for blocked_candidate
    block1 = BlockedUser(blocker_id=current_user.id, blocked_id=blocked_candidate.id, reason="harassment")
    db_session.add(block1)

    # Record block from blocker_candidate
    block2 = BlockedUser(blocker_id=blocker_candidate.id, blocked_id=current_user.id, reason="spam")
    db_session.add(block2)

    # Record active match
    u1 = min(current_user.id, match_candidate.id)
    u2 = max(current_user.id, match_candidate.id)
    match_rec = Match(user1_id=u1, user2_id=u2, is_active=True)
    db_session.add(match_rec)

    await db_session.commit()

    # Query discovery feed
    feed = await feed_svc.get_discovery_feed(current_user, db_session)
    feed_ids = [p["id"] for p in feed]

    # Verification: Only valid_candidate should be present
    assert valid_candidate.id in feed_ids
    assert current_user.id not in feed_ids
    assert incomplete_candidate.id not in feed_ids
    assert incognito_candidate.id not in feed_ids
    assert swiped_candidate.id not in feed_ids
    assert blocked_candidate.id not in feed_ids
    assert blocker_candidate.id not in feed_ids
    assert match_candidate.id not in feed_ids

    # Distance calculation check
    candidate_profile = next(p for p in feed if p["id"] == valid_candidate.id)
    assert candidate_profile["distance_km"] is not None
    assert candidate_profile["distance_km"] >= 0.5
    assert candidate_profile["is_photo_veiled"] is True


@pytest.mark.asyncio
async def test_reciprocal_orientation_matching(db_session, make_user):
    """Test 3: Reciprocal orientation correctly pairs Man-Woman and excludes non-matching preferences."""
    feed_svc = FeedService()

    # Man seeking Women
    man_seeker = make_user(
        full_name="Arjun",
        gender="Man",
        interested_in="Women",
        is_profile_completed=True,
    )
    db_session.add(man_seeker)

    # Woman seeking Men (Matches Arjun)
    woman_seeking_men = make_user(
        full_name="Meera",
        gender="Woman",
        interested_in="Men",
        is_profile_completed=True,
    )
    db_session.add(woman_seeking_men)

    # Woman seeking Women (Does not match Arjun)
    woman_seeking_women = make_user(
        full_name="Tara",
        gender="Woman",
        interested_in="Women",
        is_profile_completed=True,
    )
    db_session.add(woman_seeking_women)

    # Woman seeking Everyone (Matches Arjun)
    woman_seeking_everyone = make_user(
        full_name="Pooja",
        gender="Woman",
        interested_in="Everyone",
        is_profile_completed=True,
    )
    db_session.add(woman_seeking_everyone)

    # Man seeking Men (Does not match Arjun)
    man_seeking_men = make_user(
        full_name="Dev",
        gender="Man",
        interested_in="Men",
        is_profile_completed=True,
    )
    db_session.add(man_seeking_men)

    await db_session.commit()

    feed = await feed_svc.get_discovery_feed(man_seeker, db_session)
    feed_ids = [p["id"] for p in feed]

    assert woman_seeking_men.id in feed_ids
    assert woman_seeking_everyone.id in feed_ids
    assert woman_seeking_women.id not in feed_ids
    assert man_seeking_men.id not in feed_ids


@pytest.mark.asyncio
async def test_swipe_quota_decrement_and_exhaustion(db_session, make_user):
    """Test 4: Swiping decrements swipes_remaining; reaching 0 raises DAILY_SWIPE_QUOTA_EXHAUSTED."""
    feed_svc = FeedService()

    seeker = make_user(
        full_name="Seeker Quota",
        is_profile_completed=True,
        swipes_remaining=1,
    )
    target1 = make_user(full_name="Target 1", is_profile_completed=True)
    target2 = make_user(full_name="Target 2", is_profile_completed=True)

    db_session.add_all([seeker, target1, target2])
    await db_session.commit()
    await db_session.refresh(seeker)

    # First swipe succeeds
    res1 = await feed_svc.record_swipe(
        current_user=seeker,
        target_id=target1.id,
        action="pass",
        direct_letter=None,
        session=db_session,
    )
    assert res1["swipes_remaining"] == 0
    assert seeker.swipes_remaining == 0

    # Second swipe must raise 403 SanctuaryException
    with pytest.raises(SanctuaryException) as exc_info:
        await feed_svc.record_swipe(
            current_user=seeker,
            target_id=target2.id,
            action="like",
            direct_letter=None,
            session=db_session,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.error_code == "DAILY_SWIPE_QUOTA_EXHAUSTED"


@pytest.mark.asyncio
async def test_mutual_like_creates_match_and_token(db_session, make_user):
    """Test 5: Mutual likes ignite a Match and issue a ContactRevealToken."""
    feed_svc = FeedService()

    user_a = make_user(full_name="User A", is_profile_completed=True, swipes_remaining=5)
    user_b = make_user(full_name="User B", is_profile_completed=True, swipes_remaining=5)

    db_session.add_all([user_a, user_b])
    await db_session.commit()

    # 1. User B likes User A first
    swipe_b = Swipe(
        actor_id=user_b.id,
        target_id=user_a.id,
        swipe_type="like",
    )
    db_session.add(swipe_b)
    await db_session.commit()

    # 2. User A likes User B back
    res = await feed_svc.record_swipe(
        current_user=user_a,
        target_id=user_b.id,
        action="like",
        direct_letter="I felt resonance in your bio.",
        session=db_session,
    )

    assert res["is_match"] is True
    assert res["match_id"] is not None
    assert res["swipes_remaining"] == 4

    # Verify Match entry in database
    u1 = min(user_a.id, user_b.id)
    u2 = max(user_a.id, user_b.id)
    match_stmt = select(Match).where(Match.user1_id == u1, Match.user2_id == u2)
    match_row = (await db_session.execute(match_stmt)).scalar_one_or_none()
    assert match_row is not None
    assert match_row.is_active is True
    assert match_row.id == res["match_id"]

    # Verify ContactRevealToken provisioned
    token_stmt = select(ContactRevealToken).where(ContactRevealToken.match_id == match_row.id)
    token_row = (await db_session.execute(token_stmt)).scalar_one_or_none()
    assert token_row is not None


@pytest.mark.asyncio
async def test_feed_api_endpoints(db_session, make_user):
    """Test 6: Integration testing of /api/v1/feed endpoints with auth and database override."""
    current_user = make_user(
        full_name="API User",
        gender="Man",
        interested_in="Women",
        is_profile_completed=True,
        swipes_remaining=10,
        streak_count=3,
    )
    target = make_user(
        full_name="Target Profile",
        gender="Woman",
        interested_in="Men",
        is_profile_completed=True,
    )
    db_session.add_all([current_user, target])
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. GET /api/v1/feed
            resp = await client.get("/api/v1/feed")
            assert resp.status_code == 200
            data = resp.json()
            assert "profiles" in data
            assert "swipes_remaining" in data
            assert data["swipes_remaining"] == 10
            assert len(data["profiles"]) == 1
            assert data["profiles"][0]["full_name"] == "Target Profile"

            # 2. GET /api/v1/feed/swipes-remaining
            resp_quota = await client.get("/api/v1/feed/swipes-remaining")
            assert resp_quota.status_code == 200
            quota_data = resp_quota.json()
            assert quota_data["swipes_remaining"] == 10
            assert quota_data["streak_count"] == 3
            assert quota_data["seconds_until_refresh"] > 0

            # 3. POST /api/v1/feed/swipe (pass)
            resp_swipe = await client.post(
                "/api/v1/feed/swipe",
                json={
                    "target_id": str(target.id),
                    "action": "pass",
                },
            )
            assert resp_swipe.status_code == 200
            swipe_data = resp_swipe.json()
            assert swipe_data["is_match"] is False
            assert swipe_data["swipes_remaining"] == 9

            # 4. GET /api/v1/feed again (target is now excluded)
            resp_again = await client.get("/api/v1/feed")
            assert resp_again.status_code == 200
            feed_after = resp_again.json()
            assert len(feed_after["profiles"]) == 0
            assert feed_after["swipes_remaining"] == 9
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_swipe_target_validation(db_session, make_user):
    """Test 7: Target validation rejects self-swipes, nonexistent targets, and blocked targets."""
    feed_svc = FeedService()

    current_user = make_user(
        full_name="Valid Seeker",
        is_profile_completed=True,
        swipes_remaining=10,
    )
    blocked_target = make_user(full_name="Blocked Seeker", is_profile_completed=True)
    db_session.add_all([current_user, blocked_target])
    await db_session.commit()

    # Block blocked_target
    block = BlockedUser(blocker_id=current_user.id, blocked_id=blocked_target.id, reason="spam")
    db_session.add(block)
    await db_session.commit()

    # 1. Self-swipe rejection (400)
    with pytest.raises(SanctuaryException) as exc1:
        await feed_svc.record_swipe(
            current_user=current_user,
            target_id=current_user.id,
            action="like",
            direct_letter=None,
            session=db_session,
        )
    assert exc1.value.status_code == 400
    assert exc1.value.error_code == "INVALID_SWIPE_TARGET"
    assert current_user.swipes_remaining == 10

    # 2. Nonexistent target rejection (404)
    fake_id = uuid.uuid4()
    with pytest.raises(SanctuaryException) as exc2:
        await feed_svc.record_swipe(
            current_user=current_user,
            target_id=fake_id,
            action="like",
            direct_letter=None,
            session=db_session,
        )
    assert exc2.value.status_code == 404
    assert exc2.value.error_code == "TARGET_NOT_FOUND"
    assert current_user.swipes_remaining == 10

    # 3. Blocked target rejection (403)
    with pytest.raises(SanctuaryException) as exc3:
        await feed_svc.record_swipe(
            current_user=current_user,
            target_id=blocked_target.id,
            action="like",
            direct_letter=None,
            session=db_session,
        )
    assert exc3.value.status_code == 403
    assert exc3.value.error_code == "SEEKER_BLOCKED"
    assert current_user.swipes_remaining == 10


@pytest.mark.asyncio
async def test_multiple_historical_swipes_handling(db_session, make_user):
    """Test 8: Re-swiping updates existing swipe and reciprocal query with limit(1) ignites match without MultipleResultsFound."""
    feed_svc = FeedService()

    user_a = make_user(full_name="User Alpha", is_profile_completed=True, swipes_remaining=5)
    user_b = make_user(full_name="User Beta", is_profile_completed=True, swipes_remaining=5)
    db_session.add_all([user_a, user_b])
    await db_session.commit()

    # User B likes User A 35 days ago
    swipe_b = Swipe(
        actor_id=user_b.id,
        target_id=user_a.id,
        swipe_type="like",
        created_at=datetime.now(timezone.utc) - timedelta(days=35),
    )
    db_session.add(swipe_b)
    await db_session.commit()

    # User A previously swiped User B with 'pass'
    old_swipe_a = Swipe(
        actor_id=user_a.id,
        target_id=user_b.id,
        swipe_type="pass",
        created_at=datetime.now(timezone.utc) - timedelta(days=35),
    )
    db_session.add(old_swipe_a)
    await db_session.commit()

    # User A now re-swipes User B with 'like'; upsert pattern updates existing row without IntegrityError
    res = await feed_svc.record_swipe(
        current_user=user_a,
        target_id=user_b.id,
        action="like",
        direct_letter=None,
        session=db_session,
    )

    assert res["is_match"] is True
    assert res["match_id"] is not None

    # Verify existing swipe for User A was updated
    updated_a = (
        await db_session.execute(
            select(Swipe).where(Swipe.actor_id == user_a.id, Swipe.target_id == user_b.id)
        )
    ).scalar_one()
    assert updated_a.swipe_type == "like"



@pytest.mark.asyncio
async def test_inactive_match_reactivation(db_session, make_user):
    """Test 9: Re-liking a former partner reactivates an inactive match (is_active = True)."""
    feed_svc = FeedService()

    user_x = make_user(full_name="Seeker X", is_profile_completed=True, swipes_remaining=5)
    user_y = make_user(full_name="Seeker Y", is_profile_completed=True, swipes_remaining=5)
    db_session.add_all([user_x, user_y])
    await db_session.commit()

    # Create an existing deactivated match
    u1 = min(user_x.id, user_y.id)
    u2 = max(user_x.id, user_y.id)
    existing_match = Match(user1_id=u1, user2_id=u2, is_active=False)
    db_session.add(existing_match)

    # User Y likes User X
    swipe_y = Swipe(
        actor_id=user_y.id,
        target_id=user_x.id,
        swipe_type="like",
    )
    db_session.add(swipe_y)
    await db_session.commit()

    # User X likes User Y back
    res = await feed_svc.record_swipe(
        current_user=user_x,
        target_id=user_y.id,
        action="like",
        direct_letter=None,
        session=db_session,
    )

    assert res["is_match"] is True
    assert res["match_id"] == existing_match.id

    # Verify existing match is reactivated in database
    await db_session.refresh(existing_match)
    assert existing_match.is_active is True


@pytest.mark.asyncio
async def test_concurrent_mutual_match_conflict_recovery(db_session, make_user, monkeypatch):
    """Test 10: Atomic conflict-safe handling gracefully recovers from IntegrityError on concurrent mutual likes."""
    from sqlalchemy.exc import IntegrityError

    feed_svc = FeedService()

    user_m = make_user(full_name="Seeker M", is_profile_completed=True, swipes_remaining=5)
    user_n = make_user(full_name="Seeker N", is_profile_completed=True, swipes_remaining=5)
    db_session.add_all([user_m, user_n])
    await db_session.commit()

    # User N likes User M
    swipe_n = Swipe(
        actor_id=user_n.id,
        target_id=user_m.id,
        swipe_type="like",
    )
    db_session.add(swipe_n)
    await db_session.commit()

    u1 = min(user_m.id, user_n.id)
    u2 = max(user_m.id, user_n.id)

    # Insert match behind the scenes to simulate concurrent commit
    concurrent_match = Match(user1_id=u1, user2_id=u2, is_active=True)
    db_session.add(concurrent_match)
    await db_session.commit()

    # Verify that existing match is reused
    res1 = await feed_svc.record_swipe(
        current_user=user_m,
        target_id=user_n.id,
        action="like",
        direct_letter=None,
        session=db_session,
    )
    assert res1["is_match"] is True
    assert res1["match_id"] == concurrent_match.id

    # Now verify the IntegrityError exception recovery path when insert races
    await db_session.delete(concurrent_match)
    await db_session.commit()

    # Create fresh match in DB
    winner_match = Match(user1_id=u1, user2_id=u2, is_active=True)
    db_session.add(winner_match)
    await db_session.commit()

    orig_flush = db_session.flush
    conflict_simulated = False

    async def mock_flush(*args, **kwargs):
        nonlocal conflict_simulated
        if not conflict_simulated and any(isinstance(x, Match) for x in db_session.new):
            conflict_simulated = True
            raise IntegrityError("UNIQUE constraint failed: matches.user1_id, matches.user2_id", params={}, orig=Exception())
        await orig_flush(*args, **kwargs)

    monkeypatch.setattr(db_session, "flush", mock_flush)

    res2 = await feed_svc.record_swipe(
        current_user=user_m,
        target_id=user_n.id,
        action="like",
        direct_letter=None,
        session=db_session,
    )
    assert res2["is_match"] is True
    assert res2["match_id"] == winner_match.id

