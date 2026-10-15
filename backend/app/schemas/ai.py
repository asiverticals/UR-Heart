from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator

class AICoachRequest(BaseModel):
    messages: List[Dict[str, str]] = Field(
        default_factory=list,
        max_length=50,
        description="Chat dialogue history for contextual coaching (max 50 messages)",
    )
    prompt: Optional[str] = Field(
        None,
        max_length=4000,
        description="Direct user prompt or question for Wingman/Eva (max 4000 characters)",
    )

    @field_validator("messages")
    @classmethod
    def validate_message_length(cls, v: List[Dict[str, str]]) -> List[Dict[str, str]]:
        valid_roles = {"user", "assistant", "system", "model"}
        for msg in v:
            role = msg.get("role", "")
            if role not in valid_roles:
                raise ValueError(f"message role '{role}' must be one of {valid_roles}")
            content = msg.get("content", "")
            if not content or len(content) > 4000:
                raise ValueError("individual message content must be non-empty and <= 4000 characters")
        return v

class AICoachResponse(BaseModel):
    engine: str = Field(..., description="Active reasoning engine used: groq, gemini, openrouter, or offline")
    content: str = Field(..., description="Coaching reflection or suggested mindful dialogue")

class AITranscribeResponse(BaseModel):
    success: bool
    text: str
    engine: str
