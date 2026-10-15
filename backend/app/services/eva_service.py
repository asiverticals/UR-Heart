import json
import logging
import re
from typing import Any, Dict, Optional

from .ai_service import AIService

logger = logging.getLogger("urheart.eva")

EVA_SYSTEM_INSTRUCTION = (
    "You are Eva, the mindful consciousness guide of UR-Heart. "
    "Transform the seeker's rough bio notes into authentic, poetic, and grounded prose (under 400 characters). "
    "Do not fabricate facts. Preserve declared profession, education, and hobbies. Maintain vulnerability and intentionality. "
    "Respond strictly with valid JSON without markdown fences:\n"
    '{"polished_bio": "...", "reflection_prompt": "..."}'
)


class EvaService:
    """Eva AI Profile Reflection Engine for conscious bio refinement."""

    def __init__(self, ai_service: Optional[AIService] = None) -> None:
        self.ai_service = ai_service or AIService()

    async def polish_bio(
        self,
        raw_bio: str,
        profession: Optional[str] = None,
        education: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Transforms rough bio drafts into conscious, authentic prose under 400 characters."""
        context_parts = [f"Seeker's raw bio notes: \"{raw_bio.strip()}\""]
        if profession:
            context_parts.append(f"Profession: {profession}")
        if education:
            context_parts.append(f"Education: {education}")

        user_content = "\n".join(context_parts)
        messages = [
            {"role": "system", "content": EVA_SYSTEM_INSTRUCTION},
            {"role": "user", "content": user_content},
        ]

        try:
            completion = await self.ai_service.generate_completion(
                messages=messages,
                temperature=0.6,
                max_tokens=400,
            )
            raw_content = completion.get("content", "").strip()
            engine = completion.get("engine", "groq")

            # Clean markdown code blocks if AI wrapped the JSON
            cleaned_json = re.sub(r"^```(?:json)?\s*", "", raw_content, flags=re.MULTILINE)
            cleaned_json = re.sub(r"\s*```$", "", cleaned_json, flags=re.MULTILINE).strip()

            parsed = json.loads(cleaned_json)
            if not isinstance(parsed, dict):
                raise ValueError("Eva response did not parse to a JSON object")

            polished_bio = str(parsed.get("polished_bio") or "").strip()
            reflection_prompt = str(
                parsed.get("reflection_prompt") or "What stillness do you wish to cultivate today?"
            ).strip()

            # Bound length to 500 characters
            if len(polished_bio) > 500:
                polished_bio = polished_bio[:497] + "..."

            if not polished_bio:
                polished_bio = raw_bio.strip()

            return {
                "polished_bio": polished_bio,
                "reflection_prompt": reflection_prompt,
                "engine": engine,
            }
        except Exception as e:
            logger.warning("Eva bio polish failed: %s; returning graceful fallback", e)
            return {
                "polished_bio": raw_bio.strip(),
                "reflection_prompt": "What presence do you wish to invite into your sanctuary?",
                "engine": "fallback",
            }
