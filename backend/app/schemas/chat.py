from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

class DialogueMessageSend(BaseModel):
    """End-to-end encrypted message dispatch with client-side idempotency anchor."""
    model_config = ConfigDict(extra="forbid")

    match_id: UUID = Field(..., description="Active dialogue match identifier")
    recipient_id: UUID = Field(..., description="Kinship peer recipient UUID")
    encrypted_text: str = Field(..., min_length=1, max_length=4096, description="Signal-protocol ciphertext")
    client_id: str = Field(..., min_length=1, max_length=64, description="Client-side UUID for idempotency")

class MessageItemResponse(BaseModel):
    """Sanitized persisted message item returned across dialogue history."""
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: int
    match_id: UUID
    sender_id: UUID
    encrypted_text: str
    status: str
    client_id: Optional[str] = None
    created_at: datetime

class PassWithGraceClosureRequest(BaseModel):
    """Gentle dialogue closure payload dissolving connection with intentional closure note."""
    model_config = ConfigDict(extra="forbid")

    closure_template_key: str = Field(..., max_length=50, description="Pre-scripted sanctuary closure template identifier")
    closure_note: Optional[str] = Field(None, max_length=300, description="Optional custom farewell message")

class WsTicketResponse(BaseModel):
    """Single-use ephemeral WebSocket relay authentication ticket."""
    model_config = ConfigDict(extra="ignore")

    ticket: str = Field(..., description="Single-use 32-byte cryptographic token")
    expires_in: int = Field(default=60, description="Ticket validity window in seconds")
    expires_in_seconds: int = Field(default=60, description="Ticket validity window in seconds (legacy)")
    ws_url: str = Field(default="wss://urheart.app/ws/chat", description="WSS target gateway URL")
    endpoint_url: str = Field(default="wss://urheart.app/ws/chat", description="WSS target gateway URL (legacy)")
