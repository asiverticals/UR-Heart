import logging
from typing import Any, Dict, List, Optional
import httpx

from ..core.config import settings
from ..core.exceptions import SanctuaryException

logger = logging.getLogger("urheart.ai")


class AIService:
    """Multi-Engine AI Reasoning Cluster: Groq LPU -> Google Gemini -> OpenRouter Free Failover & Whisper Voice."""

    def __init__(self) -> None:
        self.groq_api_key = settings.GROQ_API_KEY
        self.groq_api_url = settings.GROQ_API_URL
        self.groq_voice_key = settings.GROQ_VOICE_API_KEY or settings.GROQ_API_KEY
        self.groq_whisper_url = settings.GROQ_WHISPER_URL
        self.openrouter_api_key = settings.OPENROUTER_API_KEY
        self.openrouter_api_url = settings.OPENROUTER_API_URL
        self.gemini_api_key = settings.GEMINI_API_KEY
        self.gemini_api_url = settings.GEMINI_API_URL.rstrip("/")

    async def generate_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 512,
    ) -> Dict[str, Any]:
        """Generates completion with automated cascade: Groq -> Gemini -> OpenRouter -> Offline Sandbox."""
        # 1. Primary: Groq LPU (Llama 3.3)
        if self.groq_api_key and not self.groq_api_key.startswith("placeholder_"):
            try:
                result = await self._call_groq(messages, temperature, max_tokens)
                if result:
                    return {"engine": "groq", "content": result}
            except Exception as e:
                logger.warning("Groq AI completion failed: %s; failing over to Gemini", e)

        # 2. Secondary: Google AI Studio Gemini Engine
        if self.gemini_api_key and not self.gemini_api_key.startswith("placeholder_"):
            try:
                result = await self._call_gemini(messages, temperature, max_tokens)
                if result:
                    return {"engine": "gemini", "content": result}
            except Exception as e:
                logger.warning("Gemini AI completion failed: %s; failing over to OpenRouter", e)

        # 3. Tertiary: OpenRouter Free Failover
        if self.openrouter_api_key and not self.openrouter_api_key.startswith("placeholder_"):
            try:
                result = await self._call_openrouter(messages, temperature, max_tokens)
                if result:
                    return {"engine": "openrouter", "content": result}
            except Exception as e:
                logger.warning("OpenRouter free failover failed: %s; using local sanctuary fallback", e)

        # 4. Graceful offline fallback
        return {
            "engine": "offline_sanctuary",
            "content": "Seek clarity within your heart. Sacred reflections require genuine presence.",
        }

    async def _call_groq(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> Optional[str]:
        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(self.groq_api_url, headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        return None

    async def _call_gemini(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int = 512,
    ) -> Optional[str]:
        url = f"{self.gemini_api_url}/gemini-2.5-flash:generateContent"
        headers = {"x-goog-api-key": self.gemini_api_key}
        # Convert OpenAI-style messages to Gemini contents and systemInstruction
        contents = []
        system_instruction = None
        for m in messages:
            role = m.get("role", "")
            text = m.get("content", "")
            if role == "system":
                system_instruction = {"parts": [{"text": text}]}
            else:
                gemini_role = "user" if role == "user" else "model"
                contents.append({"role": gemini_role, "parts": [{"text": text}]})

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
        return None

    async def _call_openrouter(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> Optional[str]:
        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://urheart.app",
            "X-Title": "UR-Heart Sanctuary",
        }
        payload = {
            "model": "meta-llama/llama-3.3-70b-instruct:free",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(self.openrouter_api_url, headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        return None

    async def transcribe_voice_spark(
        self,
        audio_bytes: bytes,
        filename: str = "voice_spark.m4a",
    ) -> Dict[str, Any]:
        """Transcribes Voice Spark audio using Groq Whisper Cloud LPU."""
        if not self.groq_voice_key or self.groq_voice_key.startswith("placeholder_"):
            if settings.ENVIRONMENT in ("development", "test") or getattr(settings, "TESTING", False):
                return {
                    "success": True,
                    "text": "Transcribed voice resonance (sandbox preview).",
                    "engine": "sandbox_whisper",
                }
            raise SanctuaryException(
                error_code="WHISPER_KEY_NOT_CONFIGURED",
                message="Voice transcription service is unconfigured in production.",
                status_code=503,
            )

        headers = {
            "Authorization": f"Bearer {self.groq_voice_key}",
        }
        import mimetypes
        guessed_type, _ = mimetypes.guess_type(filename)
        mime_type = guessed_type or "audio/m4a"
        files = {
            "file": (filename, audio_bytes, mime_type),
        }
        data = {
            "model": "whisper-large-v3-turbo",
            "response_format": "json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    self.groq_whisper_url,
                    headers=headers,
                    files=files,
                    data=data,
                )
                if resp.status_code == 200:
                    result = resp.json()
                    return {
                        "success": True,
                        "text": result.get("text", "").strip(),
                        "engine": "groq_whisper",
                    }
                if settings.ENVIRONMENT in ("development", "test") or getattr(settings, "TESTING", False):
                    logger.warning("Groq Whisper API returned %d in dev/test environment; falling back to sandbox preview", resp.status_code)
                    return {
                        "success": True,
                        "text": "Transcribed voice resonance (sandbox preview).",
                        "engine": "sandbox_whisper",
                    }
                raise SanctuaryException(
                    error_code="WHISPER_TRANSCRIPTION_FAILED",
                    message=f"Voice transcription returned error status {resp.status_code}",
                    status_code=502,
                )
        except httpx.HTTPError as e:
            logger.error("Groq Whisper transport error: %s", e)
            if settings.ENVIRONMENT in ("development", "test") or getattr(settings, "TESTING", False):
                logger.warning("Groq Whisper transport error in dev/test environment; falling back to sandbox preview")
                return {
                    "success": True,
                    "text": "Transcribed voice resonance (sandbox preview).",
                    "engine": "sandbox_whisper",
                }
            raise SanctuaryException(
                error_code="WHISPER_TRANSCRIPTION_FAILED",
                message="Voice transcription gateway communication error.",
                status_code=502,
            )


ai_service = AIService()

def get_ai_service() -> AIService:
    return ai_service
