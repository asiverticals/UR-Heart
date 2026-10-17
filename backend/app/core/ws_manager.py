import asyncio
from collections import defaultdict
from typing import Dict, Set, Optional
from uuid import UUID
from fastapi import WebSocket, WebSocketDisconnect

class ConnectionManager:
    """Low-footprint, non-blocking in-memory WebSocket connection manager (<5ms RAM).
    
    Coordinates active socket connections per seeker UUID, manages presence,
    and relays real-time text frames without external heavy message brokers.
    """

    def __init__(self) -> None:
        self._active_connections: Dict[UUID, Set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, user_id: UUID, websocket: WebSocket) -> None:
        """Accepts the incoming WebSocket handshake and registers the socket under user_id."""
        await websocket.accept()
        async with self._lock:
            self._active_connections[user_id].add(websocket)

    async def disconnect(self, user_id: UUID, websocket: WebSocket) -> None:
        """Removes the socket registration and cleans up empty sets to prevent memory leakage."""
        async with self._lock:
            if user_id in self._active_connections:
                self._active_connections[user_id].discard(websocket)
                if not self._active_connections[user_id]:
                    del self._active_connections[user_id]

    def is_online(self, user_id: UUID) -> bool:
        """Returns True if seeker currently maintains at least one active WebSocket connection."""
        return len(self._active_connections.get(user_id, set())) > 0

    async def send_direct_json(self, recipient_id: UUID, payload: dict) -> bool:
        """Relays a JSON frame directly to all active socket connections belonging to recipient_id.
        
        Handles dead or dropped sockets gracefully. Returns True if successfully delivered to
        at least one active connection.
        """
        delivered = False
        dead_sockets = []

        async with self._lock:
            sockets = list(self._active_connections.get(recipient_id, set()))

        for ws in sockets:
            try:
                await ws.send_json(payload)
                delivered = True
            except (WebSocketDisconnect, RuntimeError, Exception):
                dead_sockets.append(ws)

        if dead_sockets:
            async with self._lock:
                for dead_ws in dead_sockets:
                    if recipient_id in self._active_connections:
                        self._active_connections[recipient_id].discard(dead_ws)
                if recipient_id in self._active_connections and not self._active_connections[recipient_id]:
                    del self._active_connections[recipient_id]

        return delivered

    async def broadcast_presence(
        self,
        user_id: UUID,
        status: str,
        peer_ids: Optional[Set[UUID]] = None,
    ) -> None:
        """Emits a presence notification frame strictly scoped to mutual active match peers.

        Prevents global broadcast PII leakage across unmatched strangers and adversaries.
        """
        if not peer_ids:
            return

        payload = {
            "type": "presence",
            "user_id": str(user_id),
            "status": status,
        }
        async with self._lock:
            target_sockets = [
                ws
                for uid in peer_ids
                if uid in self._active_connections and uid != user_id
                for ws in self._active_connections[uid]
            ]

        for ws in target_sockets:
            try:
                await ws.send_json(payload)
            except Exception:
                pass

    async def clear(self) -> None:
        """Cleans up all tracked socket connections (useful in test teardown)."""
        async with self._lock:
            self._active_connections.clear()

connection_manager = ConnectionManager()

def get_connection_manager() -> ConnectionManager:
    """FastAPI dependency provider returning the singleton ConnectionManager."""
    return connection_manager
