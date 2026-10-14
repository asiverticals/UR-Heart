from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.exceptions import SanctuaryException
from ..models.domain.user import User

class StreakEngine:
    """Core domain engine managing Mindful Streak 24-hour decay and Accelerometer Slumber Rest Multipliers."""

    def evaluate_streak_decay(self, user: User, now: Optional[datetime] = None) -> bool:
        """Checks if active streak has expired (>24 hours). If so, decays streak and boost points to 0."""
        current_time = now or datetime.now(timezone.utc)
        if user.streak_expires_at is not None:
            # Ensure timezone-aware comparison
            expires_at = user.streak_expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)

            if current_time > expires_at and ((user.streak_count or 0) > 0 or (user.boost_points or 0) > 0):
                user.streak_count = 0
                user.boost_points = 0
                return True
        return False

    def record_daily_activity(self, user: User, now: Optional[datetime] = None) -> bool:
        """Records intentional user activity.
        Increments streak_count and awards +10 boost_points only on the first activity of a new day.
        On subsequent calls within the same day, only refreshes streak_expires_at.
        Returns True if a new day streak was incremented, False if refreshed.
        """
        current_time = now or datetime.now(timezone.utc)
        decayed = self.evaluate_streak_decay(user, now=current_time)

        is_new_day = False
        if decayed or user.streak_expires_at is None:
            is_new_day = True
        else:
            expires_at = user.streak_expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            last_activity_time = expires_at - timedelta(hours=24)
            if current_time.date() > last_activity_time.date():
                is_new_day = True

        if is_new_day:
            user.streak_count = (user.streak_count or 0) + 1
            user.boost_points = (user.boost_points or 0) + 10
            user.streak_expires_at = current_time + timedelta(hours=24)
            return True
        else:
            # Same day: refresh expiration window without inflating streak or boost points
            new_expiry = current_time + timedelta(hours=24)
            if expires_at is None or new_expiry > expires_at:
                user.streak_expires_at = new_expiry
            return False

    def calculate_morning_reward(self, sleep_hours: float, is_verified: bool = True) -> Dict[str, Any]:
        """Calculates tiered rest multiplier M_rest and reward inventory from sleep duration.
        
        If unverified, limits multiplier to base tier (1.0x).
        """
        clamped_hours = max(0.0, min(12.0, float(sleep_hours)))
        if not is_verified:
            multiplier = 1.0
        elif clamped_hours >= 8.0:
            multiplier = 2.0
        elif clamped_hours >= 6.0:
            multiplier = 1.5
        else:
            multiplier = 1.0

        swipes_awarded = int(10 * multiplier)
        boost_points_awarded = 25 if multiplier == 2.0 else int(10 * multiplier)
        direct_letters_awarded = 2 if multiplier == 2.0 else 0

        return {
            "sleep_duration_hours": clamped_hours,
            "multiplier": multiplier,
            "swipes_awarded": swipes_awarded,
            "boost_points_awarded": boost_points_awarded,
            "direct_letters_awarded": direct_letters_awarded,
        }

    def is_harvest_available(self, user: User, now: Optional[datetime] = None) -> bool:
        """Returns True if user has not yet claimed their morning slumber harvest today."""
        current_time = now or datetime.now(timezone.utc)
        if user.last_streak_ad_at is not None:
            last_ad = user.last_streak_ad_at
            if last_ad.tzinfo is None:
                last_ad = last_ad.replace(tzinfo=timezone.utc)
            if last_ad.date() == current_time.date():
                return False
        return True

    def calculate_remaining_seconds(self, user: User, now: Optional[datetime] = None) -> int:
        """Computes remaining seconds before active streak expires."""
        current_time = now or datetime.now(timezone.utc)
        if user.streak_expires_at is None:
            return 0
        expires_at = user.streak_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        diff = int((expires_at - current_time).total_seconds())
        return max(0, diff)

    async def claim_morning_harvest(
        self,
        user: User,
        sleep_hours: float,
        session: AsyncSession,
        now: Optional[datetime] = None,
        is_verified: bool = True,
    ) -> Dict[str, Any]:
        """Validates sleep duration, enforces daily idempotency, and provisions morning harvest rewards atomically."""
        current_time = now or datetime.now(timezone.utc)

        # 1. Bounds check
        if sleep_hours < 0.0 or sleep_hours > 24.0:
            raise SanctuaryException(
                error_code="INVALID_SLEEP_DURATION",
                message="Sleep duration must be between 0.0 and 24.0 hours.",
                status_code=400,
            )

        # 2. Lock user row with SELECT ... FOR UPDATE to prevent concurrent double-claim race conditions
        stmt = select(User).where(User.id == user.id).with_for_update()
        res = await session.execute(stmt)
        locked_user = res.scalar_one_or_none()
        if locked_user is None:
            locked_user = user

        # 3. Daily idempotency check on locked record
        if not self.is_harvest_available(locked_user, now=current_time):
            raise SanctuaryException(
                error_code="MORNING_HARVEST_ALREADY_CLAIMED",
                message="Morning slumber harvest has already been claimed today.",
                status_code=400,
            )

        # 4. Calculate reward yield
        reward = self.calculate_morning_reward(sleep_hours, is_verified=is_verified)

        # 5. Atomic balance provisioning
        locked_user.swipes_remaining = (locked_user.swipes_remaining or 0) + reward["swipes_awarded"]
        locked_user.boost_points = (locked_user.boost_points or 0) + reward["boost_points_awarded"]
        locked_user.direct_letters_count = (locked_user.direct_letters_count or 0) + reward["direct_letters_awarded"]
        locked_user.last_streak_ad_at = current_time

        # 6. Refresh mindful streak
        self.record_daily_activity(locked_user, now=current_time)

        # Synchronize caller user instance if separated from session identity map
        if user is not locked_user:
            user.swipes_remaining = locked_user.swipes_remaining
            user.boost_points = locked_user.boost_points
            user.direct_letters_count = locked_user.direct_letters_count
            user.last_streak_ad_at = locked_user.last_streak_ad_at
            user.streak_count = locked_user.streak_count
            user.streak_expires_at = locked_user.streak_expires_at

        await session.commit()

        multiplier = reward["multiplier"]
        if multiplier == 2.0:
            blessing = "Restorative deep slumber blessed your sanctuary with maximum vital energy."
        elif multiplier == 1.5:
            blessing = "Mindful rest refreshed your intentional daily rhythm."
        else:
            blessing = "A quiet pause yields intentional energy for today's connections."

        return {
            "sleep_duration_hours": reward["sleep_duration_hours"],
            "multiplier": multiplier,
            "swipes_awarded": reward["swipes_awarded"],
            "boost_points_awarded": reward["boost_points_awarded"],
            "direct_letters_awarded": reward["direct_letters_awarded"],
            "new_streak_count": locked_user.streak_count,
            "new_boost_points": locked_user.boost_points,
            "new_swipes_remaining": locked_user.swipes_remaining,
            "new_direct_letters_count": locked_user.direct_letters_count,
            "message": blessing,
        }

streak_engine = StreakEngine()

def get_streak_engine() -> StreakEngine:
    """Dependency provider returning singleton StreakEngine."""
    return streak_engine
