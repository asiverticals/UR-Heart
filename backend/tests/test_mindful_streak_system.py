import pytest
from datetime import datetime, timezone, timedelta
from httpx import ASGITransport
import httpx

from backend.app.core.exceptions import SanctuaryException
from backend.app.main import app
from backend.app.api.deps import get_current_user
from backend.app.core.database import get_db
from backend.app.services.streak_engine import StreakEngine

@pytest.mark.asyncio
async def test_streak_increment_within_24h(db_session, make_user):
    """Test 1: Active user engaging daily increments streak and advances streak_expires_at by 24h."""
    engine = StreakEngine()
    user = make_user(streak_count=3, boost_points=30, is_profile_completed=True)
    now = datetime(2026, 10, 14, 12, 0, 0, tzinfo=timezone.utc)
    user.streak_expires_at = now + timedelta(hours=10)
    db_session.add(user)
    await db_session.commit()

    engine.record_daily_activity(user, now=now)
    assert user.streak_count == 4
    assert user.boost_points == 40
    assert user.streak_expires_at == now + timedelta(hours=24)

@pytest.mark.asyncio
async def test_streak_decay_after_24h_inactivity(db_session, make_user):
    """Test 2: Inactive user beyond 24-hour window decays streak and resets boost points to 0."""
    engine = StreakEngine()
    user = make_user(streak_count=7, boost_points=120, is_profile_completed=True)
    now = datetime(2026, 10, 14, 12, 0, 0, tzinfo=timezone.utc)
    # Expired 2 hours ago
    user.streak_expires_at = now - timedelta(hours=2)
    db_session.add(user)
    await db_session.commit()

    decayed = engine.evaluate_streak_decay(user, now=now)
    assert decayed is True
    assert user.streak_count == 0
    assert user.boost_points == 0

    # Recording activity immediately after decay starts fresh at streak 1
    engine.record_daily_activity(user, now=now)
    assert user.streak_count == 1
    assert user.boost_points == 10
    assert user.streak_expires_at == now + timedelta(hours=24)

def test_slumber_rest_multipliers():
    """Test 3: Piecewise rest multiplier M_rest and reward yield across duration tiers."""
    engine = StreakEngine()

    # Tier 1: < 6.0 hours -> 1.0x (10 swipes, 10 points, 0 letters)
    r1 = engine.calculate_morning_reward(5.5)
    assert r1["multiplier"] == 1.0
    assert r1["swipes_awarded"] == 10
    assert r1["boost_points_awarded"] == 10
    assert r1["direct_letters_awarded"] == 0

    # Tier 2: 6.0 <= t < 8.0 hours -> 1.5x (15 swipes, 15 points, 0 letters)
    r2 = engine.calculate_morning_reward(7.0)
    assert r2["multiplier"] == 1.5
    assert r2["swipes_awarded"] == 15
    assert r2["boost_points_awarded"] == 15
    assert r2["direct_letters_awarded"] == 0

    # Tier 3: >= 8.0 hours -> 2.0x (20 swipes, 25 points, 2 letters)
    r3 = engine.calculate_morning_reward(8.5)
    assert r3["multiplier"] == 2.0
    assert r3["swipes_awarded"] == 20
    assert r3["boost_points_awarded"] == 25
    assert r3["direct_letters_awarded"] == 2

    # Unverified: >= 8.0 hours but unverified -> base tier 1.0x (10 swipes, 10 points, 0 letters)
    r_unverified = engine.calculate_morning_reward(8.5, is_verified=False)
    assert r_unverified["multiplier"] == 1.0
    assert r_unverified["swipes_awarded"] == 10
    assert r_unverified["boost_points_awarded"] == 10
    assert r_unverified["direct_letters_awarded"] == 0

@pytest.mark.asyncio
async def test_morning_harvest_once_per_day_idempotency(db_session, make_user):
    """Test 4: Attempting to claim morning harvest twice on the same calendar day raises 400."""
    engine = StreakEngine()
    user = make_user(swipes_remaining=10, boost_points=50, is_profile_completed=True)
    db_session.add(user)
    await db_session.commit()

    day1 = datetime(2026, 10, 14, 8, 30, 0, tzinfo=timezone.utc)

    # First claim succeeds
    claim1 = await engine.claim_morning_harvest(user, 7.5, db_session, now=day1)
    assert claim1["multiplier"] == 1.5
    assert claim1["swipes_awarded"] == 15
    assert user.swipes_remaining == 25
    assert user.last_streak_ad_at == day1

    # Second claim on same calendar day raises MORNING_HARVEST_ALREADY_CLAIMED
    with pytest.raises(SanctuaryException) as exc_info:
        await engine.claim_morning_harvest(user, 8.0, db_session, now=day1 + timedelta(hours=1))
    assert exc_info.value.error_code == "MORNING_HARVEST_ALREADY_CLAIMED"
    assert exc_info.value.status_code == 400

@pytest.mark.asyncio
async def test_morning_harvest_clamping_and_bounds(db_session, make_user):
    """Test 5: Clamping: sleep hours are strictly bounded between 0.0 and 12.0 hours."""
    engine = StreakEngine()
    user = make_user(is_profile_completed=True)
    db_session.add(user)
    await db_session.commit()

    day = datetime(2026, 10, 14, 7, 0, 0, tzinfo=timezone.utc)

    # Excess sleep (e.g., 18 hours) is clamped to 12.0 hours (2.0x multiplier)
    reward = engine.calculate_morning_reward(18.0)
    assert reward["sleep_duration_hours"] == 12.0
    assert reward["multiplier"] == 2.0

    # Negative or extreme values outside 0-24 reject
    with pytest.raises(SanctuaryException) as exc:
        await engine.claim_morning_harvest(user, -2.0, db_session, now=day)
    assert exc.value.error_code == "INVALID_SLEEP_DURATION"

@pytest.mark.asyncio
async def test_streak_api_endpoints_integration(db_session, make_user):
    """Test 6: Integration tests for /api/v1/streak/status, /claim-morning-harvest, and /heartbeat."""
    now = datetime(2026, 10, 14, 8, 0, 0, tzinfo=timezone.utc)
    user = make_user(
        full_name="Circadian Seeker",
        streak_count=5,
        boost_points=80,
        swipes_remaining=10,
        direct_letters_count=1,
        is_profile_completed=True,
    )
    user.streak_expires_at = now + timedelta(hours=14)
    db_session.add(user)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. GET /status
            status_res = await client.get("/api/v1/streak/status")
            assert status_res.status_code == 200
            st_data = status_res.json()["data"]
            assert st_data["streak_count"] == 5
            assert st_data["boost_points"] == 80
            assert st_data["is_active"] is True
            assert st_data["morning_harvest_available"] is True

            # 2. POST /claim-morning-harvest (Deep Slumber 8.2h -> 2.0x)
            harvest_res = await client.post(
                "/api/v1/streak/claim-morning-harvest",
                json={"sleep_duration_hours": 8.2},
            )
            assert harvest_res.status_code == 200
            h_data = harvest_res.json()["data"]
            assert h_data["multiplier"] == 2.0
            assert h_data["swipes_awarded"] == 20
            assert h_data["boost_points_awarded"] == 25
            assert h_data["direct_letters_awarded"] == 2
            assert h_data["new_streak_count"] == 6
            assert h_data["new_swipes_remaining"] == 30
            assert h_data["new_direct_letters_count"] == 3

            # 3. Duplicate harvest on same day fails
            dup_res = await client.post(
                "/api/v1/streak/claim-morning-harvest",
                json={"sleep_duration_hours": 7.0},
            )
            assert dup_res.status_code == 400
            assert dup_res.json()["error_code"] == "MORNING_HARVEST_ALREADY_CLAIMED"

            # 4. POST /heartbeat refreshes streak window on same day without duplicate increment
            hb_res = await client.post("/api/v1/streak/heartbeat")
            assert hb_res.status_code == 200
            hb_data = hb_res.json()["data"]
            assert hb_data["streak_count"] == 6
            assert hb_data["boost_points"] == 115
            assert hb_data["is_active"] is True
    finally:
        app.dependency_overrides.clear()
