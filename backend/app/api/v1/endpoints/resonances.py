from typing import Any, Dict, List
from fastapi import APIRouter, Depends, status
from sqlalchemy import or_, select
from sqlalchemy.orm import aliased
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from ....core.database import get_db
    from ....models.domain.match_and_chat import Match, Swipe
    from ....models.domain.revelation import PhotoRevealConsent
    from ....models.domain.user import User
    from ....schemas.base_response import SanctuaryResponse
    from ....services.feed_service import _mask_to_blurred_derivative
    from ...deps import get_current_user
except (ImportError, ValueError):
    from backend.app.core.database import get_db
    from backend.app.models.domain.match_and_chat import Match, Swipe
    from backend.app.models.domain.revelation import PhotoRevealConsent
    from backend.app.models.domain.user import User
    from backend.app.schemas.base_response import SanctuaryResponse
    from backend.app.services.feed_service import _mask_to_blurred_derivative
    from backend.app.api.deps import get_current_user


router = APIRouter()


@router.get(
    "/incoming",
    response_model=SanctuaryResponse[List[Dict[str, Any]]],
    status_code=status.HTTP_200_OK,
    summary="Retrieve incoming secret admirers and likes",
)
async def get_incoming_resonances(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SanctuaryResponse[List[Dict[str, Any]]]:
    """Fetches seekers who liked or superliked the current seeker and haven't yet been reciprocated."""
    my_swipe = aliased(Swipe)
    my_swipe_exists = (
        select(1)
        .select_from(my_swipe)
        .where(
            my_swipe.actor_id == current_user.id,
            my_swipe.target_id == User.id,
        )
        .exists()
    )

    stmt = (
        select(Swipe, User)
        .join(User, User.id == Swipe.actor_id)
        .where(
            Swipe.target_id == current_user.id,
            Swipe.swipe_type.in_(["like", "superlike"]),
            ~my_swipe_exists,
            User.deleted_at.is_(None),
        )
        .order_by(Swipe.created_at.desc())
        .limit(50)
    )

    results = await db.execute(stmt)
    records = results.all()

    # Bilateral photo reveal consent verification (BNS 2023 § 77 & IT Act 2000 § 66E)
    actor_ids = [actor.id for _, actor in records]
    revealed_actors = set()
    if actor_ids:
        consent_stmt = select(PhotoRevealConsent).where(
            (
                (PhotoRevealConsent.requester_id == current_user.id)
                & (PhotoRevealConsent.target_id.in_(actor_ids))
            )
            | (
                (PhotoRevealConsent.target_id == current_user.id)
                & (PhotoRevealConsent.requester_id.in_(actor_ids))
            ),
            PhotoRevealConsent.status == "accepted",
        )
        consents = (await db.execute(consent_stmt)).scalars().all()
        for c in consents:
            peer_uid = c.target_id if c.requester_id == current_user.id else c.requester_id
            revealed_actors.add(peer_uid)

    incoming_list = []
    for swipe, actor in records:
        is_revealed = actor.id in revealed_actors
        if is_revealed:
            photos = actor.photos or []
            avatar_url = actor.avatar_url or (actor.photos[0] if actor.photos else None)
        else:
            photos = [
                _mask_to_blurred_derivative(p)
                for p in (actor.photos or [])
                if p
            ]
            raw_avatar = actor.avatar_url or (actor.photos[0] if actor.photos else None)
            avatar_url = _mask_to_blurred_derivative(raw_avatar)

        incoming_list.append({
            "swipe_id": swipe.id,
            "seeker_id": str(actor.id),
            "full_name": actor.full_name,
            "bio": actor.bio,
            "photos": photos,
            "avatar_url": avatar_url,
            "is_superlike": swipe.swipe_type == "superlike",
            "direct_letter": swipe.direct_letter_text,
            "created_at": swipe.created_at.isoformat() if swipe.created_at else None,
        })

    return SanctuaryResponse(
        data=incoming_list,
        message="Incoming resonances retrieved.",
    )


@router.get(
    "/mutual",
    response_model=SanctuaryResponse[List[Dict[str, Any]]],
    status_code=status.HTTP_200_OK,
    summary="Retrieve active mutual matches",
)
async def get_mutual_resonances(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SanctuaryResponse[List[Dict[str, Any]]]:
    """Fetches all active mutual connections for the current seeker."""
    stmt = (
        select(Match)
        .where(
            or_(
                Match.user1_id == current_user.id,
                Match.user2_id == current_user.id,
            ),
            Match.is_active == True,
        )
        .order_by(Match.last_message_at.desc().nulls_last(), Match.matched_at.desc())
        .limit(100)
    )

    results = await db.execute(stmt)
    matches = results.scalars().all()

    peer_ids = [
        pid
        for pid in (
            m.user2_id if m.user1_id == current_user.id else m.user1_id
            for m in matches
        )
        if pid is not None
    ]

    peers_map = {}
    if peer_ids:
        users_stmt = select(User).where(User.id.in_(peer_ids), User.deleted_at.is_(None))
        users_res = await db.execute(users_stmt)
        for u in users_res.scalars().all():
            peers_map[u.id] = u

    # Check bilateral photo reveal consent for mutual peers
    revealed_peers = set()
    if peer_ids:
        consent_stmt = select(PhotoRevealConsent).where(
            (
                (PhotoRevealConsent.requester_id == current_user.id)
                & (PhotoRevealConsent.target_id.in_(peer_ids))
            )
            | (
                (PhotoRevealConsent.target_id == current_user.id)
                & (PhotoRevealConsent.requester_id.in_(peer_ids))
            ),
            PhotoRevealConsent.status == "accepted",
        )
        consents = (await db.execute(consent_stmt)).scalars().all()
        for c in consents:
            revealed_peers.add(
                c.target_id if c.requester_id == current_user.id else c.requester_id
            )

    mutual_list = []
    for m in matches:
        peer_id = m.user2_id if m.user1_id == current_user.id else m.user1_id
        if not peer_id or peer_id not in peers_map:
            continue
        peer = peers_map[peer_id]
        is_revealed = peer_id in revealed_peers
        if is_revealed:
            peer_avatar = peer.avatar_url if peer else None
        else:
            peer_avatar = _mask_to_blurred_derivative(peer.avatar_url) if (peer and peer.avatar_url) else None

        mutual_list.append({
            "match_id": str(m.id),
            "peer_id": str(peer_id),
            "peer_name": peer.full_name if peer else "Seeker",
            "peer_avatar": peer_avatar,
            "matched_at": m.matched_at.isoformat() if m.matched_at else None,
            "last_message_at": m.last_message_at.isoformat() if m.last_message_at else None,
            "closure_status": m.closure_status,
        })

    return SanctuaryResponse(
        data=mutual_list,
        message="Mutual resonances retrieved.",
    )
