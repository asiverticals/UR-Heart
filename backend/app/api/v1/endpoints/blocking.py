import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.exceptions import SanctuaryException
from ....models.domain.legal import BlockedUser
from ....models.domain.match_and_chat import Match
from ....models.domain.user import User
from ....schemas.base_response import SanctuaryResponse
from ...deps import get_current_user

router = APIRouter()


class BlockUserRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=100, description="Optional reason for blocking")


@router.post(
    "/{target_id}/block",
    response_model=SanctuaryResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Block abusive seeker (Apple 1.2 & Google UGC compliance)",
)
async def block_user(
    target_id: uuid.UUID = Path(..., description="UUID of the seeker to block"),
    payload: Optional[BlockUserRequest] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SanctuaryResponse[Dict[str, Any]]:
    """Blocks an abusive seeker, severing mutual resonance and active chat dialogues."""
    if current_user.id == target_id:
        raise SanctuaryException(
            error_code="CANNOT_BLOCK_SELF",
            message="Seeker cannot block their own persona.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # 1. Target existence check
    target_res = await session.execute(select(User).where(User.id == target_id))
    target_user = target_res.scalar_one_or_none()
    if not target_user:
        raise SanctuaryException(
            error_code="TARGET_NOT_FOUND",
            message="Target seeker does not exist.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    # 2. Check if already blocked
    existing_stmt = select(BlockedUser).where(
        BlockedUser.blocker_id == current_user.id,
        BlockedUser.blocked_id == target_id,
    )
    existing_res = await session.execute(existing_stmt)
    if not existing_res.scalar_one_or_none():
        reason = payload.reason if payload and payload.reason else "user_action"
        block_record = BlockedUser(
            blocker_id=current_user.id,
            blocked_id=target_id,
            reason=reason,
        )
        session.add(block_record)

    # 3. Sever any active match dialogue (preserve historical closure reason of closed matches)
    await session.execute(
        update(Match)
        .where(
            (
                ((Match.user1_id == current_user.id) & (Match.user2_id == target_id))
                | ((Match.user1_id == target_id) & (Match.user2_id == current_user.id))
            )
            & (Match.is_active.is_(True))
        )
        .values(
            is_active=False,
            closure_status="unmatched",
            closure_note="blocked_by_user",
            closed_by_user_id=current_user.id,
            closed_at=func.now(),
        )
    )
    await session.commit()

    return SanctuaryResponse(
        data={"blocked": True, "target_id": str(target_id)},
        message="Seeker has been successfully blocked.",
    )


@router.delete(
    "/{target_id}/block",
    response_model=SanctuaryResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Unblock seeker",
)
async def unblock_user(
    target_id: uuid.UUID = Path(..., description="UUID of the seeker to unblock"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SanctuaryResponse[Dict[str, Any]]:
    """Unblocks a previously blocked seeker."""
    del_stmt = delete(BlockedUser).where(
        BlockedUser.blocker_id == current_user.id,
        BlockedUser.blocked_id == target_id,
    )
    res = await session.execute(del_stmt)
    await session.commit()

    return SanctuaryResponse(
        data={"unblocked": True, "target_id": str(target_id), "rows_affected": res.rowcount},
        message="Seeker has been unblocked.",
    )


@router.get(
    "/blocked",
    response_model=SanctuaryResponse[List[str]],
    status_code=status.HTTP_200_OK,
    summary="List blocked seekers",
)
async def list_blocked_users(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SanctuaryResponse[List[str]]:
    """Returns list of UUIDs blocked by the current authenticated seeker."""
    stmt = select(BlockedUser.blocked_id).where(BlockedUser.blocker_id == current_user.id)
    res = await session.execute(stmt)
    blocked_ids = [str(uid) for uid in res.scalars().all()]

    return SanctuaryResponse(
        data=blocked_ids,
        message="Blocked seekers list retrieved.",
    )
