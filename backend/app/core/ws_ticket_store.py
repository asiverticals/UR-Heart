import asyncio
import secrets
import time
from typing import Dict, Optional
from uuid import UUID

class WsTicketStore:
    """Ephemeral, in-memory single-use ticket store for secure WebSocket connection handshakes.
    
    Prevents long-lived JWT access token leakage in query strings and proxy server logs.
    Enforces a strict 60-second TTL with atomic single-use consumption.
    """

    def __init__(self) -> None:
        self._tickets: Dict[str, dict] = {}
        self._lock = asyncio.Lock()

    async def create_ticket(self, user_id: UUID, ttl_seconds: int = 60) -> str:
        """Generates a 32-byte URL-safe cryptographic token and registers it with expiration."""
        ticket = secrets.token_urlsafe(32)
        now = time.time()
        expires_at = now + ttl_seconds

        async with self._lock:
            # Prune stale tickets to prevent memory accumulation (<5ms RAM)
            stale_keys = [t for t, data in self._tickets.items() if data["expires_at"] < now]
            for k in stale_keys:
                self._tickets.pop(k, None)

            self._tickets[ticket] = {
                "user_id": user_id,
                "expires_at": expires_at,
            }

        return ticket

    async def consume_ticket(self, ticket: str) -> Optional[UUID]:
        """Atomically retrieves and invalidates a single-use ticket.
        
        Returns the associated user_id if valid and unexpired; returns None otherwise.
        """
        now = time.time()
        async with self._lock:
            data = self._tickets.pop(ticket, None)
            if not data:
                return None

            if now > data["expires_at"]:
                return None

            return data["user_id"]

    async def clear(self) -> None:
        """Flushes all tickets (useful in testing suites)."""
        async with self._lock:
            self._tickets.clear()

ws_ticket_store = WsTicketStore()

def get_ws_ticket_store() -> WsTicketStore:
    """FastAPI dependency provider returning the singleton WsTicketStore."""
    return ws_ticket_store
