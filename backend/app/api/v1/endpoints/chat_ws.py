import asyncio
import json
import time
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select, or_, and_, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.config import settings
from ....core.database import AsyncSessionLocal, get_db
from ....core.ws_ticket_store import ws_ticket_store, get_ws_ticket_store, WsTicketStore
from ....core.ws_manager import connection_manager, get_connection_manager, ConnectionManager
from ....models.domain.user import User
from ....models.domain.match_and_chat import Match, Message
from ....schemas.base_response import SanctuaryResponse
from ....schemas.chat import WsTicketResponse
from ....services.fcm_service import fcm_service
from ...deps import get_current_user

# HTTP Router mounted under /api/v1/chat
router = APIRouter()

# WebSocket Router mounted at root for /ws/chat
ws_router = APIRouter()

async def get_db_session(websocket: WebSocket) -> AsyncGenerator[AsyncSession, None]:
    """Resolves an async database session, utilizing FastAPI test overrides if present."""
    override = websocket.app.dependency_overrides.get(get_db)
    if override:
        res = override()
        if isinstance(res, AsyncSession):
            yield res
        elif hasattr(res, "__anext__"):
            async for s in res:
                yield s
        elif hasattr(res, "__iter__"):
            for s in res:
                yield s
        else:
            yield res
    else:
        async with AsyncSessionLocal() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

async def _verify_active_match(
    session: AsyncSession,
    match_id: UUID,
    user_a: UUID,
    user_b: UUID,
) -> Optional[Match]:
    """Verifies that an active dialogue match exists between the two participants."""
    stmt = select(Match).where(
        Match.id == match_id,
        Match.is_active == True,
        or_(
            and_(Match.user1_id == user_a, Match.user2_id == user_b),
            and_(Match.user2_id == user_a, Match.user1_id == user_b),
        ),
    )
    res = await session.execute(stmt)
    return res.scalar_one_or_none()

@router.post(
    "/ws-ticket",
    response_model=SanctuaryResponse[WsTicketResponse],
    summary="Issue single-use ephemeral WebSocket relay handshake ticket",
)
async def issue_ws_ticket(
    current_user: User = Depends(get_current_user),
    ticket_store: WsTicketStore = Depends(get_ws_ticket_store),
) -> SanctuaryResponse[WsTicketResponse]:
    """Issues a 60-second single-use cryptographic token for authenticating WebSocket connections.
    
    Prevents leaking long-lived JWT access tokens into URL query strings and proxy server logs.
    """
    ttl = settings.WS_TICKET_EXPIRE_SECONDS
    ticket = await ticket_store.create_ticket(current_user.id, ttl_seconds=ttl)
    ws_url = settings.WS_BASE_URL
    return SanctuaryResponse(
        data=WsTicketResponse(
            ticket=ticket,
            expires_in=ttl,
            expires_in_seconds=ttl,
            ws_url=ws_url,
            endpoint_url=ws_url,
        ),
        message="Ephemeral WebSocket ticket generated successfully.",
    )

async def _handle_chat_websocket(
    websocket: WebSocket,
    ticket: str,
    ticket_store: WsTicketStore,
    manager: ConnectionManager,
) -> None:
    """Core WebSocket handshake and non-blocking text message relay handler."""
    # 1. Ephemeral Single-Use Ticket Handshake
    user_id = await ticket_store.consume_ticket(ticket)
    if user_id is None:
        await websocket.close(code=4401, reason="Invalid or expired ticket")
        return

    # 2. Accept & Register Connection
    await manager.connect(user_id, websocket)

    try:
        while True:
            try:
                data = await websocket.receive_json()
            except (WebSocketDisconnect, RuntimeError):
                break
            except (json.JSONDecodeError, ValueError):
                await websocket.send_json({
                    "type": "error",
                    "error_code": "INVALID_FRAME",
                    "message": "Malformed JSON frame received.",
                })
                continue

            if not isinstance(data, dict):
                await websocket.send_json({
                    "type": "error",
                    "error_code": "INVALID_FRAME",
                    "message": "Frame must be a JSON object.",
                })
                continue

            frame_type = data.get("type")

            # A. Heartbeat / Liveness Ping-Pong
            if frame_type == "heartbeat":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": time.time(),
                })

            # B. Typing Indicator
            elif frame_type == "typing":
                match_id_str = data.get("match_id")
                recipient_id_str = data.get("recipient_id")
                is_typing = data.get("is_typing", True)

                if match_id_str and recipient_id_str:
                    try:
                        recipient_uuid = UUID(str(recipient_id_str))
                        match_uuid = UUID(str(match_id_str))

                        async for session in get_db_session(websocket):
                            match_record = await _verify_active_match(
                                session, match_uuid, user_id, recipient_uuid
                            )
                            if match_record:
                                await manager.send_direct_json(
                                    recipient_uuid,
                                    {
                                        "type": "typing",
                                        "match_id": str(match_uuid),
                                        "sender_id": str(user_id),
                                        "is_typing": bool(is_typing),
                                    },
                                )
                            else:
                                await websocket.send_json({
                                    "type": "error",
                                    "error_code": "MATCH_NOT_FOUND_OR_INACTIVE",
                                    "message": "Seeker is not an active participant in this dialogue match.",
                                    "match_id": str(match_uuid),
                                })
                            break
                    except ValueError:
                        pass

            # C. Real-time Dialogue Message
            elif frame_type == "message":
                match_id_str = data.get("match_id")
                recipient_id_str = data.get("recipient_id")
                encrypted_text = data.get("encrypted_text")
                client_id = data.get("client_id")

                # Protocol-level text-only validation
                if not isinstance(encrypted_text, str) or not (1 <= len(encrypted_text) <= 4096):
                    await websocket.send_json({
                        "type": "error",
                        "error_code": "INVALID_MESSAGE_PAYLOAD",
                        "message": "Encrypted text payload must be between 1 and 4096 characters.",
                    })
                    continue

                if not match_id_str or not recipient_id_str:
                    await websocket.send_json({
                        "type": "error",
                        "error_code": "MISSING_REQUIRED_FIELDS",
                        "message": "match_id and recipient_id are required.",
                    })
                    continue

                try:
                    match_uuid = UUID(str(match_id_str))
                    recipient_uuid = UUID(str(recipient_id_str))
                except ValueError:
                    await websocket.send_json({
                        "type": "error",
                        "error_code": "INVALID_UUID_FORMAT",
                        "message": "Invalid UUID format for match_id or recipient_id.",
                    })
                    continue

                # Database Match Authorization & Persistence
                async for session in get_db_session(websocket):
                    match_record = await _verify_active_match(
                        session, match_uuid, user_id, recipient_uuid
                    )

                    if not match_record:
                        await websocket.send_json({
                            "type": "error",
                            "error_code": "MATCH_NOT_FOUND_OR_INACTIVE",
                            "message": "Seeker is not an active participant in this dialogue match.",
                            "client_id": client_id,
                            "match_id": str(match_uuid),
                        })
                        break

                    # Persist message to public.messages
                    msg = Message(
                        match_id=match_uuid,
                        sender_id=user_id,
                        encrypted_text=encrypted_text,
                        client_id=str(client_id) if client_id else None,
                        status="sent",
                    )
                    session.add(msg)
                    match_record.last_message_at = func.now()
                    await session.commit()
                    await session.refresh(msg)

                    # Relay frame to active peer socket if online
                    delivered = await manager.send_direct_json(
                        recipient_uuid,
                        {
                            "type": "message",
                            "id": msg.id,
                            "match_id": str(match_uuid),
                            "sender_id": str(user_id),
                            "encrypted_text": encrypted_text,
                            "client_id": client_id,
                            "created_at": msg.created_at.isoformat() if msg.created_at else datetime.now(timezone.utc).isoformat(),
                        },
                    )

                    msg_id = msg.id
                    if delivered:
                        msg.status = "delivered"
                        await session.commit()
                    else:
                        # Recipient offline -> dispatch FCM background push
                        asyncio.create_task(
                            fcm_service.send_multicast_push(
                                user_id=recipient_uuid,
                                title="UR-Heart Sanctuary",
                                body="A thoughtful reflection has arrived in your dialogue.",
                                data_payload={"match_id": str(match_uuid), "type": "chat_message"},
                                channel_id="channel_kinship_dialogue",
                            )
                        )

                    # Acknowledge sender with delivery status
                    await websocket.send_json({
                        "type": "ack",
                        "client_id": client_id,
                        "id": msg_id,
                        "status": "delivered" if delivered else "sent",
                    })
                    break

            # D. Read Receipt
            elif frame_type == "read_receipt":
                match_id_str = data.get("match_id")
                recipient_id_str = data.get("recipient_id")

                if match_id_str and recipient_id_str:
                    try:
                        match_uuid = UUID(str(match_id_str))
                        recipient_uuid = UUID(str(recipient_id_str))

                        async for session in get_db_session(websocket):
                            match_record = await _verify_active_match(
                                session, match_uuid, user_id, recipient_uuid
                            )
                            if not match_record:
                                await websocket.send_json({
                                    "type": "error",
                                    "error_code": "MATCH_NOT_FOUND_OR_INACTIVE",
                                    "message": "Seeker is not an active participant in this dialogue match.",
                                    "match_id": str(match_uuid),
                                })
                                break

                            update_stmt = (
                                update(Message)
                                .where(
                                    Message.match_id == match_uuid,
                                    Message.sender_id == recipient_uuid,
                                    Message.status != "read",
                                )
                                .values(status="read")
                            )
                            await session.execute(update_stmt)
                            await session.commit()

                            # Notify original sender that their messages were read
                            await manager.send_direct_json(
                                recipient_uuid,
                                {
                                    "type": "read_receipt",
                                    "match_id": str(match_uuid),
                                    "reader_id": str(user_id),
                                },
                            )
                            break
                    except ValueError:
                        pass

            # E. Unsupported Frame Type
            else:
                await websocket.send_json({
                    "type": "error",
                    "error_code": "INVALID_FRAME_TYPE",
                    "message": f"Unsupported frame type: '{frame_type}'.",
                })

    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(user_id, websocket)

@ws_router.websocket("/ws/chat")
async def websocket_chat_gateway(
    websocket: WebSocket,
    ticket: str = Query(..., description="Single-use ephemeral ticket"),
    ticket_store: WsTicketStore = Depends(get_ws_ticket_store),
    manager: ConnectionManager = Depends(get_connection_manager),
) -> None:
    """Primary WebSocket gateway endpoint (wss://urheart.app/ws/chat?ticket=...)."""
    await _handle_chat_websocket(websocket, ticket, ticket_store, manager)

@router.websocket("/ws")
async def websocket_chat_subroute(
    websocket: WebSocket,
    ticket: str = Query(..., description="Single-use ephemeral ticket"),
    ticket_store: WsTicketStore = Depends(get_ws_ticket_store),
    manager: ConnectionManager = Depends(get_connection_manager),
) -> None:
    """Alias WebSocket gateway mounted at /api/v1/chat/ws?ticket=..."""
    await _handle_chat_websocket(websocket, ticket, ticket_store, manager)
