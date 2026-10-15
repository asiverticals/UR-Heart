import logging
from typing import Any, Dict
from fastapi import APIRouter, Depends, File, Request, UploadFile, status

from ....core.exceptions import SanctuaryException
from ....models.domain.user import User
from ....schemas.ai import AICoachRequest, AICoachResponse, AITranscribeResponse
from ....schemas.base_response import SanctuaryResponse
from ....services.ai_service import AIService, get_ai_service
from ...deps import get_current_user

logger = logging.getLogger("urheart.api.ai")

router = APIRouter()


@router.post(
    "/coach",
    response_model=SanctuaryResponse[AICoachResponse],
    status_code=status.HTTP_200_OK,
    summary="Mindful Wingman AI Coaching & Conversational Reflection",
)
async def get_ai_coaching(
    payload: AICoachRequest,
    current_user: User = Depends(get_current_user),
    ai: AIService = Depends(get_ai_service),
) -> SanctuaryResponse[AICoachResponse]:
    """Generates mindful kinship coaching advice through Groq LPU with Gemini & OpenRouter failover."""
    messages = list(payload.messages)
    if payload.prompt:
        messages.append({"role": "user", "content": payload.prompt})
    if not messages:
        messages.append({"role": "user", "content": "Provide a gentle icebreaker for an intentional romantic connection."})

    res = await ai.generate_completion(messages=messages)
    return SanctuaryResponse(
        data=AICoachResponse(engine=res["engine"], content=res["content"]),
        message="Mindful coaching generated.",
    )


@router.post(
    "/transcribe-voice-spark",
    response_model=SanctuaryResponse[AITranscribeResponse],
    status_code=status.HTTP_200_OK,
    summary="Transcribe Seeker 7-Second Voice Spark using Groq Whisper",
)
async def transcribe_voice_spark(
    request: Request,
    audio_file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    ai: AIService = Depends(get_ai_service),
) -> SanctuaryResponse[AITranscribeResponse]:
    MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB limit protecting Render 512MB RAM constraint
    MAX_REQUEST_BYTES = MAX_AUDIO_BYTES + 64 * 1024  # Allow 64KB headroom for multipart MIME framing
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_REQUEST_BYTES:
                raise SanctuaryException(
                    error_code="PAYLOAD_TOO_LARGE",
                    message="Audio file exceeds 10MB limit.",
                    status_code=413,
                )
        except (ValueError, TypeError):
            pass

    audio_bytes = await audio_file.read(MAX_AUDIO_BYTES + 1)
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise SanctuaryException(
            error_code="PAYLOAD_TOO_LARGE",
            message="Audio file exceeds 10MB limit.",
            status_code=413,
        )
    if not audio_bytes:
        raise SanctuaryException(
            error_code="EMPTY_AUDIO_FILE",
            message="Uploaded voice spark payload is empty.",
            status_code=400,
        )

    res = await ai.transcribe_voice_spark(audio_bytes=audio_bytes, filename=audio_file.filename or "voice_spark.m4a")
    return SanctuaryResponse(
        data=AITranscribeResponse(success=res["success"], text=res["text"], engine=res["engine"]),
        message="Voice spark transcribed successfully.",
    )
