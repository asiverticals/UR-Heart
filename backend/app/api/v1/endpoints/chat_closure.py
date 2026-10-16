from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.exceptions import SanctuaryException
from ....core.ws_manager import ConnectionManager, get_connection_manager
from ....models.domain.match_and_chat import Match, Message
from ....models.domain.user import User
from ....schemas.base_response import SanctuaryResponse
from ....schemas.chat import MessageItemResponse, PassWithGraceClosureRequest
from ...deps import get_current_user

router = APIRouter()

VALID_CLOSURE_TEMPLATES = {
    "grace_paths_diverge",
    "grace_not_aligned",
    "grace_holding_space",
}


@router.post(
    "/close-with-grace",
    response_model=SanctuaryResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Mindful dialogue closure protocol with curated departure thought",
)
async def close_dialogue_with_grace(
    payload: PassWithGraceClosureRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    manager: ConnectionManager = Depends(get_connection_manager),
) -> SanctuaryResponse[dict]:
    """Transitions a kinship dialogue to 'closed_with_grace' with zero algorithmic penalty.

    Replaces sudden unmatching and ghosting shocks with an intentional, dignified departure.
    Dispatches a real-time system closure notification frame to the connected peer socket.
    """
    if payload.closure_template_key not in VALID_CLOSURE_TEMPLATES:
        raise SanctuaryException(
            error_code="INVALID_CLOSURE_TEMPLATE",
            message=f"Closure template '{payload.closure_template_key}' is not permitted.",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={"allowed": list(VALID_CLOSURE_TEMPLATES)},
        )

    stmt = select(Match).where(Match.id == payload.match_id)
    res = await db.execute(stmt)
    match = res.scalar_one_or_none()

    if not match:
        raise SanctuaryException(
            error_code="MATCH_NOT_FOUND",
            message="Dialogue match not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    # Authorization: Seeker must be a participant in the match
    if current_user.id not in (match.user1_id, match.user2_id):
        raise SanctuaryException(
            error_code="FORBIDDEN_NOT_PARTICIPANT",
            message="You are not an authorized participant in this dialogue.",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    # Idempotent response if match is already closed
    if not match.is_active or match.closure_status == "closed_with_grace":
        closed_at_iso = (
            match.closed_at.isoformat()
            if match.closed_at
            else datetime.now(timezone.utc).isoformat()
        )
        return SanctuaryResponse(
            data={"success": True, "closed_at": closed_at_iso, "idempotent": True},
            message="Dialogue was already concluded with grace.",
        )

    now = datetime.now(timezone.utc)
    match.is_active = False
    match.closure_status = "closed_with_grace"
    match.closed_by_user_id = current_user.id
    match.closed_at = now
    match.closure_template_key = payload.closure_template_key
    match.closure_note = payload.closure_note

    await db.commit()
    await db.refresh(match)

    # Dispatch real-time system closure frame to peer
    peer_id = match.user2_id if match.user1_id == current_user.id else match.user1_id
    closure_frame = {
        "type": "dialogue_closed",
        "match_id": str(match.id),
        "template_key": payload.closure_template_key,
        "closed_by_user_id": str(current_user.id),
    }
    await manager.send_direct_json(peer_id, closure_frame)
    await manager.send_direct_json(current_user.id, closure_frame)

    return SanctuaryResponse(
        data={"success": True, "closed_at": match.closed_at.isoformat()},
        message="Dialogue dissolved with mindful grace.",
    )


@router.get(
    "/messages/{match_id}",
    response_model=SanctuaryResponse[List[MessageItemResponse]],
    status_code=status.HTTP_200_OK,
    summary="Fetch encrypted dialogue message history for an authorized match",
)
async def get_dialogue_messages(
    match_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SanctuaryResponse[List[MessageItemResponse]]:
    """Retrieves chronologically ordered encrypted messages for an authorized dialogue chamber."""
    stmt = select(Match).where(Match.id == match_id)
    res = await db.execute(stmt)
    match = res.scalar_one_or_none()

    if not match:
        raise SanctuaryException(
            error_code="MATCH_NOT_FOUND",
            message="Dialogue match not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    if current_user.id not in (match.user1_id, match.user2_id):
        raise SanctuaryException(
            error_code="FORBIDDEN_NOT_PARTICIPANT",
            message="You are not an authorized participant in this dialogue.",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    msg_stmt = (
        select(Message)
        .where(Message.match_id == match_id)
        .order_by(Message.created_at.asc(), Message.id.asc())
        .limit(limit)
        .offset(offset)
    )
    msg_res = await db.execute(msg_stmt)
    messages = msg_res.scalars().all()

    items = [MessageItemResponse.model_validate(m) for m in messages]
    return SanctuaryResponse(
        data=items,
        meta={
            "is_active": match.is_active,
            "closure_status": match.closure_status,
            "closure_template_key": match.closure_template_key,
        },
        message="Dialogue messages retrieved successfully.",
    )
