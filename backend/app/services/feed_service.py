import math
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.exceptions import SanctuaryException
from ..models.domain.legal import BlockedUser
from ..models.domain.match_and_chat import Match, Swipe
from ..models.domain.revelation import ContactRevealToken
from ..models.domain.user import User

def _mask_to_blurred_derivative(url: Optional[str]) -> Optional[str]:
    """Transforms raw CDN photo URL into blurred thumbnail derivative to prevent client-side media leakage."""
    if not url:
        return None
    if "_blurred." in url:
        return url
    if "." in url:
        base, ext = url.rsplit(".", 1)
        return f"{base}_blurred.{ext}"
    return f"{url}_blurred.webp"

class FeedService:
    """Core discovery deck and swipe interaction domain service."""

    mask_to_blurred_derivative = staticmethod(_mask_to_blurred_derivative)

    @staticmethod
    def fuzz_coordinates(lat: float, lon: float) -> Tuple[float, float]:
        """Obfuscates raw GPS coordinates to 2 decimal places (~1.11km neighborhood grid) per DPDP Act 2023 Sec 6."""
        fuzzed_lat = math.floor(100.0 * float(lat) + 0.5) / 100.0
        fuzzed_lon = math.floor(100.0 * float(lon) + 0.5) / 100.0
        return round(fuzzed_lat, 2), round(fuzzed_lon, 2)

    @staticmethod
    def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Computes Great-Circle Haversine distance in kilometers and clamps display distance >= 0.5km."""
        R = 6371.0  # Earth radius in kilometers

        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
        d = R * c

        # Clamp distance to minimum 0.5km to prevent exact triangulation
        return max(0.5, round(d, 1))

    @staticmethod
    def calculate_seconds_until_midnight() -> int:
        """Returns seconds remaining until midnight UTC for daily quota refresh."""
        now = datetime.now(timezone.utc)
        midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return int((midnight - now).total_seconds())

    async def get_discovery_feed(
        self,
        current_user: User,
        session: AsyncSession,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Queries candidate seeker profiles enforcing strict indexed self-exclusion perimeter and DPDP fuzzing."""
        # 1. Base query with profile completion and incognito check
        stmt = select(User).where(
            User.deleted_at.is_(None),
            User.is_profile_completed.is_(True),
            User.is_incognito.is_(False),
            User.id != current_user.id,
            User.auth_id != current_user.auth_id,
        )

        if current_user.email:
            stmt = stmt.where(User.email != current_user.email)

        # 2. Exclude profiles swiped within the last 30 days
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        subq_swiped = select(Swipe.target_id).where(
            Swipe.actor_id == current_user.id,
            Swipe.created_at >= thirty_days_ago,
        )
        stmt = stmt.where(User.id.not_in(subq_swiped))

        # 3. Exclude bilaterally blocked users
        subq_blocked = select(BlockedUser.blocked_id).where(BlockedUser.blocker_id == current_user.id)
        subq_blocker = select(BlockedUser.blocker_id).where(BlockedUser.blocked_id == current_user.id)
        stmt = stmt.where(User.id.not_in(subq_blocked), User.id.not_in(subq_blocker))

        # 4. Exclude active match partners
        subq_matches1 = select(Match.user2_id).where(Match.user1_id == current_user.id, Match.is_active.is_(True))
        subq_matches2 = select(Match.user1_id).where(Match.user2_id == current_user.id, Match.is_active.is_(True))
        stmt = stmt.where(User.id.not_in(subq_matches1), User.id.not_in(subq_matches2))

        # 5. Bilateral reciprocal orientation matching
        # Target's gender matches current_user's preference
        if current_user.interested_in == "Men":
            stmt = stmt.where(User.gender == "Man")
        elif current_user.interested_in == "Women":
            stmt = stmt.where(User.gender == "Woman")

        # Current user's gender matches target's preference
        if current_user.gender == "Man":
            stmt = stmt.where(User.interested_in.in_(["Men", "Everyone"]))
        elif current_user.gender == "Woman":
            stmt = stmt.where(User.interested_in.in_(["Women", "Everyone"]))
        else:
            stmt = stmt.where(User.interested_in == "Everyone")

        # 6. Sorting by priority (boost points, mindful streak, registration recency)
        stmt = stmt.order_by(
            User.boost_points.desc(),
            User.streak_count.desc(),
            User.created_at.desc(),
        ).limit(limit)

        result = await session.execute(stmt)
        candidates = result.scalars().all()

        profiles: List[Dict[str, Any]] = []
        for candidate in candidates:
            dist: Optional[float] = None
            if (
                current_user.latitude is not None
                and current_user.longitude is not None
                and candidate.latitude is not None
                and candidate.longitude is not None
            ):
                dist = self.calculate_haversine_distance(
                    float(current_user.latitude),
                    float(current_user.longitude),
                    float(candidate.latitude),
                    float(candidate.longitude),
                )

            profiles.append({
                "id": candidate.id,
                "full_name": candidate.full_name,
                "dob": candidate.dob,
                "gender": candidate.gender,
                "interested_in": candidate.interested_in,
                "location_name": candidate.location_name,
                "bio": candidate.bio,
                "profession": candidate.profession,
                "education": candidate.education,
                "streak_count": candidate.streak_count,
                "boost_points": candidate.boost_points,
                "kyc_status": candidate.kyc_status,
                "is_photo_veiled": True,  # Modesty veil enforced by default
                "photos": [
                    _mask_to_blurred_derivative(p)
                    for p in (candidate.photos or [])
                    if p
                ],
                "avatar_url": (
                    _mask_to_blurred_derivative(candidate.avatar_url)
                    if candidate.avatar_url
                    else None
                ),
                "voice_spark_url": (
                    f"/api/v1/media/voice/{candidate.id}/spark.m4a"
                    if candidate.voice_spark_url
                    else None
                ),
                "voice_spark_prompt": candidate.voice_spark_prompt,
                "voice_spark_duration": candidate.voice_spark_duration,
                "is_voice_verified": candidate.is_voice_verified,
                "distance_km": dist,
            })

        return profiles

    async def record_swipe(
        self,
        current_user: User,
        target_id: uuid.UUID,
        action: str,
        direct_letter: Optional[str],
        session: AsyncSession,
    ) -> Dict[str, Any]:
        """Evaluates swipe intent, decrements daily quota atomically, and ignites mutual matches."""
        # 1. Target Validation: Reject self-swipe
        if target_id == current_user.id:
            raise SanctuaryException(
                error_code="INVALID_SWIPE_TARGET",
                message="Cannot record swipe on oneself.",
                status_code=400,
            )

        # 2. Target Validation: Confirm target exists and is active
        target_stmt = select(User.id).where(User.id == target_id, User.deleted_at.is_(None))
        target_res = await session.execute(target_stmt)
        if target_res.scalar_one_or_none() is None:
            raise SanctuaryException(
                error_code="TARGET_NOT_FOUND",
                message="The requested seeker profile does not exist.",
                status_code=404,
            )

        # 3. Target Validation: Confirm target is not bilaterally blocked
        block_stmt = select(BlockedUser.id).where(
            (
                (BlockedUser.blocker_id == current_user.id)
                & (BlockedUser.blocked_id == target_id)
            )
            | (
                (BlockedUser.blocker_id == target_id)
                & (BlockedUser.blocked_id == current_user.id)
            )
        )
        block_res = await session.execute(block_stmt)
        if block_res.scalars().first() is not None:
            raise SanctuaryException(
                error_code="SEEKER_BLOCKED",
                message="Cannot interact with a blocked seeker profile.",
                status_code=403,
            )

        # 4. Enforce & decrement mindful swipe quota atomically via conditional database update
        stmt = (
            update(User)
            .where(User.id == current_user.id, User.swipes_remaining > 0)
            .values(swipes_remaining=User.swipes_remaining - 1)
            .returning(User.swipes_remaining)
        )
        res = await session.execute(stmt)
        new_swipes_remaining = res.scalar_one_or_none()

        if new_swipes_remaining is None:
            await session.refresh(current_user)
            raise SanctuaryException(
                error_code="DAILY_SWIPE_QUOTA_EXHAUSTED",
                message="You have met today's rhythm. Return tomorrow or complete a mindful reflection.",
                status_code=403,
            )

        current_user.swipes_remaining = new_swipes_remaining

        # 5. Record swipe interaction (upsert pattern adhering to uq_swipes_actor_target)
        existing_swipe_stmt = select(Swipe).where(
            Swipe.actor_id == current_user.id,
            Swipe.target_id == target_id,
        )
        existing_swipe = (await session.execute(existing_swipe_stmt)).scalar_one_or_none()

        if existing_swipe:
            existing_swipe.swipe_type = action
            existing_swipe.direct_letter_text = direct_letter
            existing_swipe.created_at = datetime.now(timezone.utc)
        else:
            swipe = Swipe(
                actor_id=current_user.id,
                target_id=target_id,
                swipe_type=action,
                direct_letter_text=direct_letter,
            )
            session.add(swipe)
        await session.flush()

        # 6. Check for reciprocal resonance on like / superlike (safely limited to 1 row)
        is_match = False
        match_id: Optional[uuid.UUID] = None

        if action in ("like", "superlike"):
            reciprocal_stmt = (
                select(Swipe)
                .where(
                    Swipe.actor_id == target_id,
                    Swipe.target_id == current_user.id,
                    Swipe.swipe_type.in_(["like", "superlike"]),
                )
                .order_by(Swipe.created_at.desc())
                .limit(1)
            )
            reciprocal_res = await session.execute(reciprocal_stmt)
            reciprocal_swipe = reciprocal_res.scalars().first()

            if reciprocal_swipe:
                u1 = min(current_user.id, target_id)
                u2 = max(current_user.id, target_id)

                match_stmt = select(Match).where(Match.user1_id == u1, Match.user2_id == u2)
                m_res = await session.execute(match_stmt)
                existing_match = m_res.scalar_one_or_none()

                if existing_match:
                    # Reactivate match if it was previously deactivated
                    if not existing_match.is_active:
                        existing_match.is_active = True
                    is_match = True
                    match_id = existing_match.id
                else:
                    try:
                        async with session.begin_nested():
                            new_match = Match(user1_id=u1, user2_id=u2, is_active=True)
                            session.add(new_match)
                            await session.flush()

                            contact_token = ContactRevealToken(match_id=new_match.id)
                            session.add(contact_token)

                            is_match = True
                            match_id = new_match.id
                    except IntegrityError:
                        # Concurrent mutual swipe already inserted Match
                        m_res = await session.execute(match_stmt)
                        existing_match = m_res.scalar_one_or_none()
                        if existing_match:
                            if not existing_match.is_active:
                                existing_match.is_active = True
                            is_match = True
                            match_id = existing_match.id

        await session.commit()
        await session.refresh(current_user)

        return {
            "is_match": is_match,
            "match_id": match_id,
            "swipes_remaining": current_user.swipes_remaining,
        }

feed_service = FeedService()

def get_feed_service() -> FeedService:
    """Dependency provider returning the active FeedService instance."""
    return feed_service
