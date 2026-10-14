import base64
import json
import logging
import uuid
from decimal import Decimal
from typing import Any, Dict, Optional
import httpx
from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.exceptions import SanctuaryException
from ..models.domain.admin_telemetry import AdminKycEscalation
from ..models.domain.user import User
from .storage_service import CloudflareR2StorageService, get_storage_service

logger = logging.getLogger(__name__)

class KycService:
    """Biometric KYC Verification Service using Groq Vision API with DPDP <60s Ephemeral Purge SLA."""

    def __init__(
        self,
        storage: Optional[CloudflareR2StorageService] = None,
        http_client: Optional[httpx.AsyncClient] = None,
        groq_api_key: Optional[str] = None,
        model: str = "llama-3.2-11b-vision-preview",
    ):
        self.storage_service = storage or get_storage_service()
        self.http_client = http_client or httpx.AsyncClient(timeout=30.0)
        self.groq_api_key = groq_api_key or settings.GROQ_API_KEY
        self.model = model

    async def evaluate_liveness(
        self,
        anchor_image_bytes: bytes,
        live_frame_bytes: bytes,
    ) -> Dict[str, Any]:
        """Evaluates facial match & liveness between anchor photo and live video frame via Groq Vision API."""
        if not self.groq_api_key:
            raise SanctuaryException(
                error_code="GROQ_API_KEY_UNSET",
                message="Groq API key is not configured for facial liveness evaluation.",
                status_code=500,
            )

        anchor_b64 = base64.b64encode(anchor_image_bytes).decode("utf-8")
        live_b64 = base64.b64encode(live_frame_bytes).decode("utf-8")

        prompt = (
            "You are a strict biometric facial verification and liveness engine under India DPDP Act 2023. "
            "Compare Image 1 (registered anchor profile photo) and Image 2 (live selfie capture frame). "
            "Verify: 1. Facial geometry, eye distance, jawline, and ear alignment. "
            "2. Natural skin texture and lighting gradient (ensure Image 2 is a real live person, not a screen replay, photo printout, or 3D mask). "
            "Return valid JSON adhering strictly to: "
            '{"match_score": <integer between 0 and 100>, "is_live_person": <boolean>, "reasoning": "<concise explanation>"}'
        )

        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/webp;base64,{anchor_b64}"},
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/webp;base64,{live_b64}"},
                        },
                    ],
                }
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }

        try:
            resp = await self.http_client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            if resp.status_code != 200:
                logger.error(f"Groq API error ({resp.status_code}): {resp.text}")
                raise SanctuaryException(
                    error_code="GROQ_API_ERROR",
                    message=f"Groq Vision API returned status {resp.status_code}",
                    status_code=502,
                )

            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)

            score = int(parsed.get("match_score", 0))
            is_live = bool(parsed.get("is_live_person", False))
            reasoning = str(parsed.get("reasoning", ""))

            # Penalize if not a live person
            if not is_live and score > 40:
                score = 30

            return {
                "match_score": max(0, min(100, score)),
                "is_live_person": is_live,
                "reasoning": reasoning,
            }
        except SanctuaryException:
            raise
        except Exception as e:
            logger.error(f"Facial liveness evaluation failed: {e}", exc_info=True)
            raise SanctuaryException(
                error_code="LIVENESS_EVALUATION_FAILED",
                message=f"Biometric liveness evaluation error: {str(e)}",
                status_code=500,
            )

    async def _fetch_anchor_bytes(self, user: User) -> bytes:
        """Retrieves anchor photo bytes for comparison strictly under users/{user.id}/ prefix."""
        if not user.photos or not user.photos[0]:
            raise SanctuaryException(
                error_code="MISSING_ANCHOR_PHOTO",
                message="User has no registered anchor photo in slot 1 for liveness comparison.",
                status_code=400,
            )

        photo_url = user.photos[0]
        domain = self.storage_service.public_domain.rstrip("/")
        derived_key: Optional[str] = None
        if photo_url.startswith(domain):
            candidate = photo_url[len(domain) :].lstrip("/")
            if candidate.startswith(f"users/{user.id}/"):
                derived_key = candidate

        # If key is valid and belongs to user, attempt fetch
        if derived_key:
            try:
                return self.storage_service.get_object_bytes(derived_key)
            except Exception:
                pass

        # Fall back strictly to standard user slot 1 key
        fallback_key = f"users/{user.id}/moments/slot_1.webp"
        try:
            return self.storage_service.get_object_bytes(fallback_key)
        except Exception as e:
            raise SanctuaryException(
                error_code="ANCHOR_FETCH_FAILED",
                message=f"Failed to retrieve registered anchor photo from storage: {str(e)}",
                status_code=400,
            )

    async def process_kyc_submission(
        self,
        user: User,
        live_video_key: str,
        background_tasks: BackgroundTasks,
        session: AsyncSession,
    ) -> Dict[str, Any]:
        """Orchestrates biometric liveness evaluation, state transitions, and SLA <60s ephemeral deletion."""
        try:
            # 1. Fetch anchor photo and live video frame
            anchor_bytes = await self._fetch_anchor_bytes(user)
            try:
                live_bytes = self.storage_service.get_object_bytes(live_video_key)
            except Exception as e:
                raise SanctuaryException(
                    error_code="LIVE_FRAME_NOT_FOUND",
                    message=f"Temporary live frame not found in R2 storage: {str(e)}",
                    status_code=404,
                )

            # 2. Evaluate liveness via Groq Vision API
            eval_result = await self.evaluate_liveness(anchor_bytes, live_bytes)
            score = eval_result["match_score"]
            reasoning = eval_result["reasoning"]

            # 3. Tri-State Threshold Evaluation
            if score >= 80:
                user.kyc_status = True
                status_str = "approved"
                msg = "Sacred identity verified."
            elif 50 <= score < 80:
                user.kyc_status = False
                status_str = "escalated"
                msg = "Manual sanctuary review pending."

                # Retain frame at private escalation path for admin review (not public CDN)
                escalation_key = f"kyc_escalations/{user.id}/review_{uuid.uuid4().hex}.webp"
                self.storage_service.put_object_bytes(escalation_key, live_bytes, "image/webp")

                # Check existing escalation or insert new pending ticket
                stmt = select(AdminKycEscalation).where(AdminKycEscalation.user_id == user.id)
                res = await session.execute(stmt)
                existing = res.scalar_one_or_none()
                stale_escalation_key: Optional[str] = None
                if existing:
                    if existing.selfie_storage_url and existing.selfie_storage_url != escalation_key:
                        stale_escalation_key = existing.selfie_storage_url
                    existing.groq_match_score = Decimal(str(round(score / 100.0, 3)))
                    existing.selfie_storage_url = escalation_key
                    existing.status = "pending"
                else:
                    escalation = AdminKycEscalation(
                        user_id=user.id,
                        declared_dob=user.dob,
                        groq_match_score=Decimal(str(round(score / 100.0, 3))),
                        selfie_storage_url=escalation_key,
                        id_card_storage_url=user.photos[0] if user.photos else "",
                        status="pending",
                    )
                    session.add(escalation)
            else:
                user.kyc_status = False
                status_str = "rejected"
                msg = "Facial resonance mismatch."

            await session.commit()
            await session.refresh(user)

            if status_str == "escalated" and stale_escalation_key:
                background_tasks.add_task(self.purge_ephemeral_biometrics, stale_escalation_key)

            return {
                "success": score >= 50,
                "status": status_str,
                "score": score,
                "message": msg,
                "reasoning": reasoning,
            }
        finally:
            # Ephemeral biometric purge must ALWAYS run to fulfill DPDP SLA (<60s)
            background_tasks.add_task(self.purge_ephemeral_biometrics, live_video_key)

    async def purge_ephemeral_biometrics(self, object_key: str) -> bool:
        """Programmatically purges raw biometric media from Cloudflare R2 under DPDP Act Section 8."""
        try:
            self.storage_service.delete_object(object_key)
            logger.info(f"[DPDP-PURGE] Ephemeral biometric key {object_key} purged <60s.")
            return True
        except Exception as e:
            logger.error(f"[DPDP-PURGE] Failed to purge ephemeral key {object_key}: {e}")
            return False

_kyc_service: Optional[KycService] = None

def get_kyc_service() -> KycService:
    """Dependency provider returning singleton KycService."""
    global _kyc_service
    if _kyc_service is None:
        _kyc_service = KycService()
    return _kyc_service
