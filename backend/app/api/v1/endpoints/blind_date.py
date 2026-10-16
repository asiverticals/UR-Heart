from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select, or_, distinct
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from ....core.database import get_db
    from ....models.domain.user import User
    from ....models.domain.blind_date import BlindDateQueue
    from ....models.domain.match_and_chat import Swipe, Message
    from ....models.domain.monetization import ProcessedAdTransaction
    from ....schemas.base_response import SanctuaryResponse
    from ...deps import get_current_user
except (ImportError, ValueError):
    from backend.app.core.database import get_db
    from backend.app.models.domain.user import User
    from backend.app.models.domain.blind_date import BlindDateQueue
    from backend.app.models.domain.match_and_chat import Swipe, Message
    from backend.app.models.domain.monetization import ProcessedAdTransaction
    from backend.app.schemas.base_response import SanctuaryResponse
    from backend.app.api.deps import get_current_user


router = APIRouter()

TARGET_MAU_THRESHOLD = 1_000_000


async def _get_active_mau(session: AsyncSession) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    # Count distinct active users across recorded user activity events and recent signups
    swipes_q = select(Swipe.actor_id.label("uid")).where(Swipe.created_at >= cutoff)
    msgs_q = select(Message.sender_id.label("uid")).where(Message.created_at >= cutoff)
    ads_q = select(ProcessedAdTransaction.user_id.label("uid")).where(ProcessedAdTransaction.created_at >= cutoff)
    new_users_q = select(User.id.label("uid")).where(User.deleted_at.is_(None), User.created_at >= cutoff)

    activity_union = swipes_q.union(msgs_q, ads_q, new_users_q).subquery()

    stmt = (
        select(func.count(distinct(activity_union.c.uid)))
        .select_from(activity_union)
        .join(User, User.id == activity_union.c.uid)
        .where(User.deleted_at.is_(None))
    )
    result = await session.execute(stmt)
    return result.scalar() or 0


@router.get(
    "/eligibility",
    response_model=SanctuaryResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Check blind date speed dating milestone eligibility (Condition C1)",
)
async def check_blind_date_eligibility(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SanctuaryResponse[Dict[str, Any]]:
    """Returns milestone lock status. Blind Date speed dating unlocks upon reaching 1,000,000 MAU."""
    current_mau = await _get_active_mau(db)
    is_eligible = current_mau >= TARGET_MAU_THRESHOLD

    if is_eligible:
        return SanctuaryResponse(
            data={
                "status": "unlocked",
                "current_mau": current_mau,
                "target_mau": TARGET_MAU_THRESHOLD,
                "is_joinable": True,
                "message": "Speed Dating sanctuary is unlocked.",
            },
            message="Milestone achieved. Speed Dating is unlocked.",
        )

    return SanctuaryResponse(
        data={
            "status": "milestone_locked",
            "current_mau": current_mau,
            "target_mau": TARGET_MAU_THRESHOLD,
            "is_joinable": False,
            "message": "Speed Dating sanctuary unlocks upon reaching 1,000,000 seekers.",
        },
        message="Milestone eligibility status retrieved.",
    )


@router.post(
    "/queue/join",
    response_model=SanctuaryResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Join blind date speed dating queue (Condition C1 Gated)",
)
async def join_blind_date_queue(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SanctuaryResponse[Dict[str, Any]]:
    """Gated by Condition C1. Informs seeker whether queue is joinable based on authoritative MAU milestone and persists queue entry."""
    current_mau = await _get_active_mau(db)
    is_eligible = current_mau >= TARGET_MAU_THRESHOLD

    if is_eligible:
        q_stmt = select(BlindDateQueue).where(BlindDateQueue.user_id == current_user.id)
        q_res = await db.execute(q_stmt)
        queue_entry = q_res.scalar_one_or_none()
        if not queue_entry:
            queue_entry = BlindDateQueue(
                user_id=current_user.id,
                gender=current_user.gender,
                interested_in=current_user.interested_in,
                preferred_age_min=current_user.preferred_age_min,
                preferred_age_max=current_user.preferred_age_max,
                status="waiting",
            )
            db.add(queue_entry)
            await db.commit()
            await db.refresh(queue_entry)
        else:
            # Restore entry to waiting state if it previously completed, matched, or cancelled
            if queue_entry.status != "waiting":
                queue_entry.status = "waiting"
                queue_entry.gender = current_user.gender
                queue_entry.interested_in = current_user.interested_in
                queue_entry.preferred_age_min = current_user.preferred_age_min
                queue_entry.preferred_age_max = current_user.preferred_age_max
                queue_entry.joined_at = func.now()
                await db.commit()
                await db.refresh(queue_entry)
        return SanctuaryResponse(
            data={
                "status": "queued",
                "joined": True,
                "current_mau": current_mau,
                "target_mau": TARGET_MAU_THRESHOLD,
                "message": "Seeker successfully entered the Speed Dating queue.",
            },
            message="Seeker joined blind date queue.",
        )

    return SanctuaryResponse(
        data={
            "status": "milestone_locked",
            "joined": False,
            "current_mau": current_mau,
            "target_mau": TARGET_MAU_THRESHOLD,
            "message": "Speed Dating is currently locked until 1,000,000 MAU milestone is attained.",
        },
        message="Speed dating queue is milestone locked.",
    )
