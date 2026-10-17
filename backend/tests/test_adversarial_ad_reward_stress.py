"""
Adversarial Stress Harness: AdRewardLedger Check Constraints & Parity.
Empirically executed by challenger_m2_retest.

Tests:
1. 100% of all 22 valid ad types persist cleanly.
2. Typos, near-matches, and case-variations are strictly rejected.
3. SQL injection, XSS, and command injection strings are strictly rejected.
4. Empty strings, whitespace, newlines, and null bytes are strictly rejected.
5. Unicode homoglyphs and emojis are strictly rejected.
6. Unknown monetization perks and unauthorized actions are strictly rejected.
7. Network check constraint enforcement.
8. Positive reward points constraint enforcement (rejects <= 0).
"""

import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, DataError

from backend.app.models.domain import User, AdRewardLedger

ALL_22_LEGITIMATE_AD_TYPES = [
    "quick_reflection",
    "deep_resonance",
    "sacred_bridge_reveal",
    "whatsapp_reveal",
    "morning_harvest_unlock",
    "daily_streak_boost",
    "rewarded_daily_boost",
    "rewarded_reveal",
    "rewarded_extra_swipes",
    "rewarded_streak_freeze",
    "rewarded_blind_date_extend",
    "extra_swipes",
    "daily_harvest_boost",
    "instant_reveal_key",
    "super_like",
    "instant_bridge_pass",
    "streak_freeze",
    "rewind_pass",
    "compass_teleport",
    "ad_free_24h",
    "profile_spotlight",
    "incognito_hour",
]

ADVERSARIAL_ILLEGAL_AD_TYPES = [
    # Subtly wrong typos / near-matches
    "quick_reflections",
    "quick reflection",
    "quick-reflection",
    "deepresonance",
    "extra_swipe",
    "superlike",
    "instantbridgepass",
    "streakfreeze",
    "rewindpass",
    "compassteleport",
    "adfree24h",
    "ad_free",
    "daily_boost",
    "rewarded_boost",
    # Case variations (must be exact lower_snake_case)
    "QUICK_REFLECTION",
    "Quick_Reflection",
    "EXTRA_SWIPES",
    "Super_Like",
    "Instant_Reveal_Key",
    "INCOGNITO_HOUR",
    # Injection attempts
    "' OR '1'='1",
    "'; DROP TABLE ad_reward_ledger; --",
    "quick_reflection' --",
    "\" OR \"\"=\"",
    "<script>alert(1)</script>",
    "{{ 7 * 7 }}",
    # Empty & whitespace
    "",
    " ",
    "   ",
    "\t",
    "\n",
    "\r\n",
    " quick_reflection ",
    # Null bytes & control characters
    "quick_reflection\x00",
    "\x00",
    # Unicode homoglyphs & emojis
    "sacred_bridge_revеal",  # Cyrillic 'е' (U+0435)
    "quіck_reflection",     # Cyrillic 'і' (U+0456)
    "🔥reward🔥",
    "💎_boost",
    # Unauthorized perks & fake names
    "free_coins",
    "god_mode",
    "infinite_swipes",
    "admin_bypass",
    "test_ad",
    "fake_ad_type",
    "null",
    "undefined",
    "NaN",
]


@pytest.mark.asyncio
async def test_all_22_legitimate_ad_types_empirically_pass(db_session, make_user):
    """Verify that every single one of the 22 legitimate ad types commits and round-trips successfully."""
    user = make_user()
    db_session.add(user)
    await db_session.commit()

    for idx, ad_type in enumerate(ALL_22_LEGITIMATE_AD_TYPES):
        tx_id = f"tx_stress_legit_{idx}_{uuid.uuid4().hex[:8]}"
        ledger = AdRewardLedger(
            user_id=user.id,
            ssv_transaction_id=tx_id,
            network="admob",
            ad_type=ad_type,
            reward_points=10,
        )
        db_session.add(ledger)
        await db_session.commit()

        # Query back directly
        stmt = select(AdRewardLedger).where(AdRewardLedger.ssv_transaction_id == tx_id)
        res = await db_session.execute(stmt)
        record = res.scalar_one_or_none()
        assert record is not None
        assert record.ad_type == ad_type
        assert record.reward_points == 10


@pytest.mark.asyncio
async def test_adversarial_illegal_ad_types_strictly_rejected(db_session, make_user):
    """Verify that every adversarial, invalid, typo, or injection string is strictly rejected."""
    user = make_user()
    db_session.add(user)
    await db_session.commit()

    rejections = 0
    for idx, illegal_ad_type in enumerate(ADVERSARIAL_ILLEGAL_AD_TYPES):
        async with db_session.begin_nested():
            tx_id = f"tx_stress_illegal_{idx}_{uuid.uuid4().hex[:8]}"
            ledger = AdRewardLedger(
                user_id=user.id,
                ssv_transaction_id=tx_id,
                network="admob",
                ad_type=illegal_ad_type,
                reward_points=10,
            )
            db_session.add(ledger)
            with pytest.raises((IntegrityError, DataError)) as exc_info:
                await db_session.flush()
            rejections += 1

    assert rejections == len(ADVERSARIAL_ILLEGAL_AD_TYPES)


@pytest.mark.asyncio
async def test_invalid_networks_strictly_rejected(db_session, make_user):
    """Verify that unknown or forged ad network identifiers are strictly rejected."""
    user = make_user()
    db_session.add(user)
    await db_session.commit()

    invalid_networks = [
        "fake_network",
        "google_ads",
        "unity_ads",
        "ironsource",
        "applovin",
        "",
        "ADMOB",
        "meta_audience",
    ]

    for net in invalid_networks:
        async with db_session.begin_nested():
            ledger = AdRewardLedger(
                user_id=user.id,
                ssv_transaction_id=f"tx_bad_net_{uuid.uuid4().hex[:8]}",
                network=net,
                ad_type="quick_reflection",
                reward_points=10,
            )
            db_session.add(ledger)
            with pytest.raises(IntegrityError):
                await db_session.flush()


@pytest.mark.asyncio
async def test_non_positive_reward_points_rejected(db_session, make_user):
    """Verify that reward_points <= 0 violates chk_positive_reward constraint."""
    user = make_user()
    db_session.add(user)
    await db_session.commit()

    invalid_points = [0, -1, -50, -9999]

    for pts in invalid_points:
        async with db_session.begin_nested():
            ledger = AdRewardLedger(
                user_id=user.id,
                ssv_transaction_id=f"tx_bad_pts_{pts}_{uuid.uuid4().hex[:8]}",
                network="admob",
                ad_type="quick_reflection",
                reward_points=pts,
            )
            db_session.add(ledger)
            with pytest.raises(IntegrityError):
                await db_session.flush()
