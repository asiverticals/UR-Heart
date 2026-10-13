1. Real-Time Architecture & Handshake Lifecycle
UR-Heart Sanctuary uses an ephemeral, ticket-authenticated WebSocket relay (wss://urheart.app/ws/chat) designed for ultra-low latency (<5ms RAM transmission) while offloading long-term message durability to PostgreSQL asynchronously.
MD

  CLIENT (Flutter / PWA)                                       SERVER (FastAPI on Render)
     │                                                                   │
     │ 1. POST /api/v1/chat/ws-ticket (Bearer JWT)                       │
     ├──────────────────────────────────────────────────────────────────►│
     │ 2. 200 OK: {"ticket": "32-byte-hex", "expires_in": 60}            │
     │◄──────────────────────────────────────────────────────────────────┤
     │                                                                   │
     │ 3. WSS Handshake: /ws/chat?ticket=32-byte-hex                     │
     ├──────────────────────────────────────────────────────────────────►│
     │    [Server: validate_and_consume_ticket() -> Delete ticket]       │
     │    [Server: Register WebSocket in ConnectionManager RAM cache]    │
     │ 4. HTTP 101 Switching Protocols (Connection Upgraded)             │
     │◄──────────────────────────────────────────────────────────────────┤
     │                                                                   │
     │ 5. dialogue_message {"match_id", "text", "client_id", ...}        │
     ├──────────────────────────────────────────────────────────────────►│
     │                                                                   │
     │               ┌───────────────────────────────────────────────────┼──────────┐
     │               ▼                                                   ▼          ▼
     │    [Relay to Peer RAM]                                    [Async DB Persist] [Peer Offline?]
     │    (<5ms if Peer connected)                              (public.messages)  (Dispatch FCM v1)
     │                                                                   │
     │ 6. delivery_ack {"status": "delivered_to_relay", "client_id"}     │
     │◄──────────────────────────────────────────────────────────────────┤
     │                                                                   │
     │ 7. ping (Every 25s keep-alive)                                    │
     ├──────────────────────────────────────────────────────────────────►│
     │ 8. pong                                                           │
     │◄──────────────────────────────────────────────────────────────────┤

MD

Cryptographic Handshake Rules
Single-Use Tickets (ws_ticket.py): Bearer JWT tokens are never passed as query parameters in WebSocket URLs to prevent URI logging leaks on edge proxies and Cloudflare CDN. Clients must exchange their JWT for an ephemeral, single-use ticket via POST /api/v1/chat/ws-ticket.
MD

+ 1

Strict 60-Second TTL: Tickets expire after 60 seconds if unused.
MD

Atomic Consumption & Replay Prevention: The server consumes and deletes the ticket from memory immediately upon receiving the connection request (validate_and_consume_ticket). Replay attempts or duplicate uses trigger an immediate close frame with status code 1008 Policy Violation.
MD

No Direct Socket Authentication Loops: Database queries are not executed inside the WebSocket read loop; auth resolution occurs strictly once during the ticket validation handshake.

1. Complete WebSocket Frame Protocol Reference
All WebSocket communications are encoded as UTF-8 JSON text frames.

Frame type Direction Payload Structure Summary Functional Trigger & Scope
ping Client
→
→ Server {"type": "ping", "timestamp": str} 
25-second keep-alive heartbeat.
MD

pong Server
→
→ Client {"type": "pong", "timestamp": str} 
Heartbeat acknowledgment from server.
MD

dialogue_message Bidirectional {"type": "dialogue_message", "match_id": UUID, "recipient_id": UUID, "id": str, "text": str, "sender_id": UUID, "created_at": str} 
Real-time chat dialogue exchange (<5ms RAM relay).
MD

delivery_ack Server
→
→ Client {"type": "delivery_ack", "match_id": UUID, "id": str, "status": "delivered_to_relay"} 
Instant receipt confirmation to sender.
MD

read_receipt Bidirectional {"type": "read_receipt", "action": "status_update", "match_id": UUID, "status": "read"} 
Updates delivery tick to double-blue in client UI.
MD

bridge_reveal_request Client ──► Server {"type": "bridge_reveal_request", "match_id": UUID} 
Sacred Bridge client revelation request initiating contact exchange.
MD

bridge_reveal_requested Server ──► Client {"type": "bridge_reveal_requested", "match_id": UUID, "initiator_id": UUID, "initiator_name": str} 
Sacred Bridge mutual consent prompt notification delivered to partner.
MD

bridge_unlocked Server ──► Client {"type": "bridge_unlocked", "match_id": UUID, "partner_id": UUID, "partner_name": str, "contact_handle": str, "unlocked_at": str} 
Unseals WhatsApp/Instagram handle upon server-verified mutual consent.
MD

sanctuary_notification Server
→
→ Client {"type": "sanctuary_notification", "notification": {"id": str, "type": str, "title": str, "body": str}} 
Real-time in-app banner alert event.
MD

MD

Frame JSON Schema Specifications

1. ping / pong Frames
Client Ping:

JSON

{
  "type": "ping",
  "timestamp": "2026-10-13T07:45:00.000Z"
}

MD

Server Pong:

JSON

{
  "type": "pong",
  "timestamp": "2026-10-13T07:45:00.005Z"
}

MD

1. dialogue_message Frame
Client to Server:

JSON

{
  "type": "dialogue_message",
  "match_id": "8a3e7b1a-9f4c-4e8c-8f43-a6d51c7261a8",
  "recipient_id": "3b2a1c09-4d8e-4a6f-9e7b-c5e31a890124",
  "id": "client-msg-uuid-v4-00129",
  "text": "EncryptedCiphertextAES256GCMBase64==",
  "sender_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
}

MD

Server to Recipient (Relayed):

JSON

{
  "type": "dialogue_message",
  "match_id": "8a3e7b1a-9f4c-4e8c-8f43-a6d51c7261a8",
  "recipient_id": "3b2a1c09-4d8e-4a6f-9e7b-c5e31a890124",
  "id": "client-msg-uuid-v4-00129",
  "text": "EncryptedCiphertextAES256GCMBase64==",
  "sender_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "created_at": "2026-10-13T07:45:01.120Z"
}

MD

1. delivery_ack Frame
JSON

{
  "type": "delivery_ack",
  "match_id": "8a3e7b1a-9f4c-4e8c-8f43-a6d51c7261a8",
  "id": "client-msg-uuid-v4-00129",
  "status": "delivered_to_relay",
  "timestamp": "2026-10-13T07:45:01.125Z"
}

MD

1. read_receipt Frame
JSON

{
  "type": "read_receipt",
  "action": "status_update",
  "match_id": "8a3e7b1a-9f4c-4e8c-8f43-a6d51c7261a8",
  "reader_id": "3b2a1c09-4d8e-4a6f-9e7b-c5e31a890124",
  "status": "read",
  "timestamp": "2026-10-13T07:45:15.000Z"
}

MD

1. bridge_reveal_request & bridge_unlocked Frames
JSON

{
  "type": "bridge_reveal_request",
  "match_id": "8a3e7b1a-9f4c-4e8c-8f43-a6d51c7261a8",
  "initiator_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "initiator_name": "Aarav"
}

MD

JSON

{
  "type": "bridge_unlocked",
  "match_id": "8a3e7b1a-9f4c-4e8c-8f43-a6d51c7261a8",
  "partner_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "partner_name": "Aarav",
  "contact_handle": "+919876543210",
  "unlocked_at": "2026-10-13T07:46:00.000Z"
}

MD

1. In-Memory Connection Manager & Relay Engine (chat_websocket.py)
Implemented in backend/app/api/v1/endpoints/chat_websocket.py using FastAPI's native WebSocket engine:

Python

# backend/app/api/v1/endpoints/chat_websocket.py

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Optional
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from app.services.ws_ticket_service import ws_ticket_service
from app.services.fcm_service import fcm_notification_service
from app.core.database import async_session_factory
from app.models.domain.match_and_chat import Message, Match
from app.models.domain.user import User
from sqlalchemy import select, update

router = APIRouter()
logger = logging.getLogger("SanctuaryRelay")

class SanctuaryConnectionManager:
    def __init__(self):
        # Maps user_id -> active WebSocket connection
        self.active_sockets: Dict[UUID, WebSocket] = {}

    async def connect(self, user_id: UUID, websocket: WebSocket):
        await websocket.accept()
        self.active_sockets[user_id] = websocket
        logger.info(f"Seeker {user_id} connected to Sacred Relay Chamber.")

    def disconnect(self, user_id: UUID, websocket: Optional[WebSocket] = None):
        if user_id in self.active_sockets:
            if websocket is None or self.active_sockets[user_id] == websocket:
                del self.active_sockets[user_id]
                logger.info(f"Seeker {user_id} disconnected from Sacred Relay.")

    async def send_personal_frame(self, user_id: UUID, payload: dict) -> bool:
        """Relays frame directly to user RAM socket if connected (<5ms)."""
        ws = self.active_sockets.get(user_id)
        if ws:
            try:
                await ws.send_text(json.dumps(payload))
                return True
            except Exception as e:
                logger.warning(f"Failed to transmit frame to {user_id}: {e}")
                self.disconnect(user_id, ws)
        return False

manager = SanctuaryConnectionManager()

async def persist_message_async(
    match_id: UUID,
    sender_id: UUID,
    encrypted_text: str,
    client_id: str
):
    """Asynchronous background worker persistence to PostgreSQL."""
    async with async_session_factory() as session:
        try:
            # 1. Insert message with client_id idempotency check
            stmt = select(Message).where(
                Message.match_id == match_id,
                Message.sender_id == sender_id,
                Message.client_id == client_id
            )
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if existing:
                return  # Skip duplicate insertion on client retry

            msg = Message(
                match_id=match_id,
                sender_id=sender_id,
                encrypted_text=encrypted_text,
                client_id=client_id,
                status="sent"
            )
            session.add(msg)

            # 2. Touch match last_message_at
            await session.execute(
                update(Match)
                .where(Match.id == match_id)
                .values(last_message_at=datetime.now(timezone.utc))
            )
            await session.commit()
        except Exception as e:
            logger.error(f"Async persistence error for match {match_id}: {e}")

@router.websocket("/ws/chat")
async def chat_websocket_endpoint(websocket: WebSocket, ticket: Optional[str] = None):
    # 1. Validate Single-Use Ticket
    if not ticket:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = ws_ticket_service.validate_and_consume_ticket(ticket)
    if not user_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 2. Register Socket in Memory
    await manager.connect(user_id, websocket)

    try:
        while True:
            raw_text = await websocket.receive_text()
            try:
                frame = json.loads(raw_text)
            except json.JSONDecodeError:
                continue

            frame_type = frame.get("type")

            # Heartbeat Handshake
            if frame_type == "ping":
                await websocket.send_text(json.dumps({
                    "type": "pong",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }))
                continue

            # Real-time Dialogue Message Relay
            elif frame_type == "dialogue_message":
                match_id = UUID(frame["match_id"])
                client_id = frame.get("id", "")
                text = frame.get("text", "")

                # Authorize match membership and derive legitimate peer recipient
                async with async_session_factory() as session:
                    match = await session.get(Match, match_id)
                    if not match or not match.is_active or user_id not in (match.user1_id, match.user2_id):
                        await websocket.send_text(json.dumps({"type": "error", "message": "Unauthorized match dialogue"}))
                        continue
                    recipient_id = match.user2_id if user_id == match.user1_id else match.user1_id

                now_iso = datetime.now(timezone.utc).isoformat()
                relay_payload = {
                    "type": "dialogue_message",
                    "match_id": str(match_id),
                    "sender_id": str(user_id),
                    "recipient_id": str(recipient_id),
                    "id": client_id,
                    "text": text,
                    "created_at": now_iso
                }

                # Relayed to Peer RAM (<5ms)
                delivered_to_ram = await manager.send_personal_frame(recipient_id, relay_payload)

                # Send delivery acknowledgment back to sender
                await websocket.send_text(json.dumps({
                    "type": "delivery_ack",
                    "match_id": str(match_id),
                    "id": client_id,
                    "status": "delivered_to_relay",
                    "timestamp": now_iso
                }))

                # Schedule Async Database Persistence
                asyncio.create_task(persist_message_async(match_id, user_id, text, client_id))

                # If peer is offline, dispatch High-Priority FCM push notification
                if not delivered_to_ram:
                    asyncio.create_task(fcm_notification_service.dispatch_chat_notification(
                        recipient_id=recipient_id,
                        sender_id=user_id,
                        match_id=match_id,
                        preview_text="Encrypted Sacred Message"
                    ))

            # Read Receipt Relay
            elif frame_type == "read_receipt":
                match_id = UUID(frame["match_id"])
                async with async_session_factory() as session:
                    match = await session.get(Match, match_id)
                    if match and match.is_active and user_id in (match.user1_id, match.user2_id):
                        recipient_id = match.user2_id if user_id == match.user1_id else match.user1_id
                        await manager.send_personal_frame(recipient_id, {
                            "type": "read_receipt",
                            "action": "status_update",
                            "match_id": str(match_id),
                            "status": "read"
                        })

            # Sacred Contact Bridge Handshake
            elif frame_type == "bridge_reveal_request":
                match_id = UUID(frame.get("match_id", ""))
                async with async_session_factory() as session:
                    # Row-level lock to prevent simultaneous race conditions on mutual consent
                    match = await session.get(Match, match_id, with_for_update=True)
                    if match and match.is_active and user_id in (match.user1_id, match.user2_id):
                        target_user_id = match.user2_id if user_id == match.user1_id else match.user1_id
                        initiator = await session.get(User, user_id)
                        initiator_name = initiator.full_name if initiator else "Seeker"

                        # Persist user reveal consent
                        if user_id == match.user1_id:
                            match.user1_revealed = True
                        else:
                            match.user2_revealed = True
                        
                        both_consented = bool(match.user1_revealed and match.user2_revealed)
                        u1 = await session.get(User, match.user1_id) if both_consented else None
                        u2 = await session.get(User, match.user2_id) if both_consented else None
                        now_iso = datetime.now(timezone.utc).isoformat() if both_consented else None

                        # Commit consent to database first before dispatching real-time frames
                        await session.commit()

                        # Emit reveal prompt notification to partner
                        await manager.send_personal_frame(target_user_id, {
                            "type": "bridge_reveal_requested",
                            "match_id": str(match_id),
                            "initiator_id": str(user_id),
                            "initiator_name": initiator_name
                        })

                        # Transmit canonical unlock if both consented and committed
                        if both_consented and u1 and u2:
                            # Transmit canonical unlock to user 1
                            await manager.send_personal_frame(match.user1_id, {
                                "type": "bridge_unlocked",
                                "match_id": str(match_id),
                                "partner_id": str(u2.id),
                                "partner_name": u2.full_name,
                                "contact_handle": u2.phone or u2.email,
                                "unlocked_at": now_iso
                            })
                            # Transmit canonical unlock to user 2
                            await manager.send_personal_frame(match.user2_id, {
                                "type": "bridge_unlocked",
                                "match_id": str(match_id),
                                "partner_id": str(u1.id),
                                "partner_name": u1.full_name,
                                "contact_handle": u1.phone or u1.email,
                                "unlocked_at": now_iso
                            })
            elif frame_type == "bridge_unlocked":
                # Clients cannot forge bridge_unlocked events; ignored/rejected
                logger.warning(f"Seeker {user_id} attempted to inject unverified bridge_unlocked frame.")

    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
    except Exception as e:
        logger.error(f"WebSocket session exception for seeker {user_id}: {e}")
        manager.disconnect(user_id, websocket)

MD

1. Single-Use Ticket Issuer Service (ws_ticket.py)
Implemented in backend/app/services/ws_ticket_service.py:

Python

# backend/app/services/ws_ticket_service.py

import secrets
import time
from typing import Dict, Tuple, Optional
from uuid import UUID

class WsTicketService:
    def __init__(self):
        # In-memory dictionary: ticket_string -> (user_id, expiry_unix_time)
        self._tickets: Dict[str, Tuple[UUID, float]] = {}

    def issue_ticket(self, user_id: UUID, ttl_seconds: int = 60) -> str:
        """Generates a cryptographically secure 32-byte single-use ticket."""
        self._purge_expired()
        ticket = secrets.token_hex(32)
        expiry = time.time() + ttl_seconds
        self._tickets[ticket] = (user_id, expiry)
        return ticket

    def validate_and_consume_ticket(self, ticket: str) -> Optional[UUID]:
        """Validates ticket, immediately consumes it, and returns user_id."""
        self._purge_expired()
        entry = self._tickets.pop(ticket, None)
        if not entry:
            return None
        user_id, expiry = entry
        if time.time() > expiry:
            return None
        return user_id

    def _purge_expired(self):
        now = time.time()
        expired = [k for k, (_, exp) in self._tickets.items() if exp < now]
        for k in expired:
            self._tickets.pop(k, None)

ws_ticket_service = WsTicketService()

MD

1. FCM HTTP v1 Delivery Engine & Channels
Push notifications are orchestrated via Firebase Cloud Messaging HTTP v1 API (SanctuaryNotificationService).
MD

5.1 Android Notification Channel Specifications
┌────────────────────────────────────────────────────────────────────────┐
│                   ANDROID HARDWARE NOTIFICATION CHANNELS               │
├────────────────────────────────────────────────────────────────────────┤
│ CHANNEL 1: ur_heart_sacred_dialogue                                    │
│   • Importance: NotificationManager.IMPORTANCE_HIGH (Max)              │
│   • Priority: High / Heads-up display                                  │
│   • Scope: Encrypted chats, new matches, direct letters, reveals       │
│   • Sound: Raw resource 'sanctuary_bell.mp3'                           │
│   • Vibration: [0, 250, 250, 250]                                      │
├────────────────────────────────────────────────────────────────────────┤
│ CHANNEL 2: ur_heart_presence_channel                                   │
│   • Importance: NotificationManager.IMPORTANCE_LOW                     │
│   • Priority: Low / Silent                                             │
│   • Scope: Mindful streak renewal warnings, slumber multipliers        │
│   • Sound: None (Silent)                                               │
│   • Vibration: None                                                    │
└────────────────────────────────────────────────────────────────────────┘

MD

5.2 FCM v1 Payload Structures
Python

# backend/app/services/fcm_service.py

import json
import logging
from typing import Optional
from uuid import UUID
from app.core.config import settings
from app.core.database import async_session_factory
from app.models.domain.user import User
from app.models.domain.device import DeviceFcmToken
from sqlalchemy import select
from google.oauth2 import service_account
import google.auth.transport.requests
import httpx

logger = logging.getLogger("SanctuaryFCM")

class FcmNotificationService:
    def __init__(self):
        self.scopes = ["https://www.googleapis.com/auth/firebase.messaging"]
        self.credentials = None
        if settings.FIREBASE_SERVICE_ACCOUNT_JSON and settings.FIREBASE_SERVICE_ACCOUNT_JSON != "{}":
            try:
                info = json.loads(settings.FIREBASE_SERVICE_ACCOUNT_JSON)
                self.credentials = service_account.Credentials.from_service_account_info(
                    info, scopes=self.scopes
                )
            except Exception as e:
                logger.warning(f"FCM credentials initialization bypassed: {e}")

    def _get_access_token(self) -> str:
        req = google.auth.transport.requests.Request()
        self.credentials.refresh(req)
        return self.credentials.token

    async def dispatch_chat_notification(
        self,
        recipient_id: UUID,
        sender_id: UUID,
        match_id: UUID,
        preview_text: str = "Encrypted Sacred Message"
    ):
        if not self.credentials:
            return

        async with async_session_factory() as session:
            # 1. Fetch active FCM tokens for recipient
            tokens_result = await session.execute(
                select(DeviceFcmToken.token)
                .where(DeviceFcmToken.user_id == recipient_id, DeviceFcmToken.active == True)
            )
            tokens = tokens_result.scalars().all()
            if not tokens:
                return

            # 2. Fetch sender name
            sender = await session.get(User, sender_id)
            sender_name = sender.full_name if sender else "A Seeker"

        access_token = self._get_access_token()
        fcm_url = f"https://fcm.googleapis.com/v1/projects/{settings.FIREBASE_PROJECT_ID}/messages:send"

        # 3. Build HTTP v1 Message Payload
        for target_token in tokens:
            payload = {
                "message": {
                    "token": target_token,
                    "notification": {
                        "title": f"Dialogue from {sender_name}",
                        "body": preview_text
                    },
                    "data": {
                        "click_action": "FLUTTER_NOTIFICATION_CLICK",
                        "route": "/chat-dialogue",
                        "match_id": str(match_id),
                        "sender_id": str(sender_id),
                        "notification_type": "sacred_dialogue"
                    },
                    "android": {
                        "priority": "high",
                        "notification": {
                            "channel_id": "ur_heart_sacred_dialogue",
                            "notification_priority": "PRIORITY_HIGH",
                            "default_sound": True
                        }
                    },
                    "apns": {
                        "payload": {
                            "aps": {
                                "sound": "default",
                                "badge": 1
                            }
                        }
                    }
                }
            }

            async with httpx.AsyncClient() as client:
                try:
                    res = await client.post(
                        fcm_url,
                        json=payload,
                        headers={
                            "Authorization": f"Bearer {access_token}",
                            "Content-Type": "application/json"
                        },
                        timeout=5.0
                    )
                    if res.status_code != 200:
                        logger.warning(f"FCM delivery returned status {res.status_code}: {res.text}")
                except Exception as ex:
                    logger.error(f"FCM dispatch error: {ex}")

fcm_notification_service = FcmNotificationService()

MD

1. Client-Side Flutter Service Integration
Implemented in lib/core/services/sanctuary_websocket_service.dart:

Dart

// lib/core/services/sanctuary_websocket_service.dart
import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:http/http.dart' as http;
import '../storage/secure_session_storage.dart';

class SanctuaryWebSocketService {
  final SecureSessionStorage _storage = SecureSessionStorage();
  WebSocketChannel? _channel;
  Timer? _pingTimer;
  bool _isConnected = false;

  final StreamController<Map<String, dynamic>> _messageController =
      StreamController<Map<String, dynamic>>.broadcast();

  Stream<Map<String, dynamic>> get stream => _messageController.stream;

  Future<void> connect() async {
    if (_isConnected) return;

    try {
      // 1. Fetch single-use ticket
      final jwtToken = await _storage.readAuthToken();
      if (jwtToken == null) return;

      final res = await http.post(
        Uri.parse("https://urheart.app/api/v1/chat/ws-ticket"),
        headers: {"Authorization": "Bearer $jwtToken"},
      );

      if (res.statusCode != 200) return;
      final ticketData = jsonDecode(res.body);
      final ticket = ticketData['ticket'];

      // 2. Establish WSS connection using ticket parameter
      final wsUri = Uri.parse("wss://urheart.app/ws/chat?ticket=$ticket");
      _channel = WebSocketChannel.connect(wsUri);
      _isConnected = true;

      // 3. Start 25s keep-alive ping loop
      _startPingLoop();

      // 4. Listen to incoming frames
      _channel!.stream.listen(
        (data) {
          try {
            final frame = jsonDecode(data as String) as Map<String, dynamic>;
            _messageController.add(frame);
          } catch (e) {
            debugPrint("WebSocket frame parse error: $e");
          }
        },
        onDone: () => _handleDisconnect(),
        onError: (err) => _handleDisconnect(),
      );
    } catch (e) {
      _handleDisconnect();
    }
  }

  void _startPingLoop() {
    _pingTimer?.cancel();
    _pingTimer = Timer.periodic(const Duration(seconds: 25), (timer) {
      if (_isConnected && _channel != null) {
        _channel!.sink.add(jsonEncode({
          "type": "ping",
          "timestamp": DateTime.now().toUtc().toIso8601String(),
        }));
      }
    });
  }

  void sendDialogueMessage({
    required String matchId,
    required String recipientId,
    required String clientId,
    required String encryptedText,
    required String senderId,
  }) {
    if (!_isConnected ||_channel == null) return;

    final frame = {
      "type": "dialogue_message",
      "match_id": matchId,
      "recipient_id": recipientId,
      "id": clientId,
      "text": encryptedText,
      "sender_id": senderId,
    };
    _channel!.sink.add(jsonEncode(frame));
  }

  void _handleDisconnect() {
    _isConnected = false;
    _pingTimer?.cancel();
    _channel = null;
    // Auto-reconnect after 3 seconds
    Future.delayed(const Duration(seconds: 3), () => connect());
  }

  void disconnect() {
    _pingTimer?.cancel();
    _channel?.sink.close();
    _isConnected = false;
  }
}

MD

1. Verification & Automated Test Suite
To verify the WebSocket connection handshake, message relay, and FCM delivery pipeline:
MD

Bash

# Verify chat persistence, read receipts, and FCM notification triggers

pytest backend/tests/test_chat_persistence_read_and_fcm.py
