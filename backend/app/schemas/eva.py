from typing import Optional
from pydantic import BaseModel, Field, field_validator


class EvaBioPolishRequest(BaseModel):
    """Payload for Eva AI mindful profile bio refinement."""
    raw_bio: str = Field(..., min_length=10, max_length=500, description="Raw seeker draft bio notes")
    profession: Optional[str] = Field(None, max_length=100, description="Seeker declared profession")
    education: Optional[str] = Field(None, max_length=100, description="Seeker declared education")

    @field_validator("raw_bio")
    @classmethod
    def validate_raw_bio_stripped(cls, v: str) -> str:
        non_ws_count = sum(1 for c in v if not c.isspace())
        if non_ws_count < 10:
            raise ValueError("raw_bio must contain at least 10 non-whitespace characters")
        return v


class EvaBioPolishResponse(BaseModel):
    """Refined bio prose and mindful contemplation prompt from Eva AI."""
    polished_bio: str = Field(..., description="Refined, authentic, and conscious bio prose (<= 500 chars)")
    reflection_prompt: str = Field(..., description="Mindful contemplation prompt for connection intentionality")
    engine: str = Field(default="groq", description="AI reasoning engine used (groq, gemini, openrouter, offline)")
