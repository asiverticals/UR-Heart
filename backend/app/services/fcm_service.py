import json
import logging
import time
from typing import Any, Dict, Optional
from uuid import UUID

import google.auth.transport.requests
from google.oauth2 import service_account
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.database import AsyncSessionLocal
from backend.app.models.domain.admin_telemetry import DeviceFcmToken
from backend.app.models.domain.user import User

logger = logging.getLogger("SanctuaryFCM")

class FcmService:
    """Dispatches FCM HTTP v1 background push notifications with OAuth2 caching and stale token pruning."""

    def __init__(self) -> None:
        self.scopes = ["https://www.googleapis.com/auth/firebase.messaging"]
        self.credentials: Optional[service_account.Credentials] = None
        self._cached_token: Optional[str] = None
        self._token_expiry: float = 0.0

        if settings.FIREBASE_SERVICE_ACCOUNT_JSON and settings.FIREBASE_SERVICE_ACCOUNT_JSON.strip() not in ("", "{}"):
            try:
                info = json.loads(settings.FIREBASE_SERVICE_ACCOUNT_JSON)
                if "client_email" in info and "private_key" in info:
                    self.credentials = service_account.Credentials.from_service_account_info(
                        info, scopes=self.scopes
                    )
            except Exception as e:
                logger.warning(f"FCM service account initialization skipped: {e}")

    def _get_access_token(self) -> Optional[str]:
        """Returns valid OAuth2 Bearer token, refreshing before expiry."""
        if not self.credentials:
            return None

        now = time.time()
        if self._cached_token and now < (self._token_expiry - 60):
            return self._cached_token

        req = google.auth.transport.requests.Request()
        self.credentials.refresh(req)
        self._cached_token = self.credentials.token
        # Google tokens typically expire in 3600 seconds
        self._token_expiry = now + 3500
        return self._cached_token

    async def send_multicast_push(
        self,
        user_id: UUID,
        title: str,
        body: str,
        data_payload: Dict[str, Any],
        channel_id: str = "channel_kinship_dialogue",
        session: Optional[AsyncSession] = None,
    ) -> int:
        """Dispatches privacy-preserving push notifications to all active device tokens of a user.
        
        DPDP Section 8 Invariant: Never leaks decrypted message content or raw PII.
        """
        if session is None:
            async with AsyncSessionLocal() as db_session:
                return await self._dispatch_to_user(
                    user_id=user_id,
                    title=title,
                    body=body,
                    data_payload=data_payload,
                    channel_id=channel_id,
                    session=db_session,
                )
        return await self._dispatch_to_user(
            user_id=user_id,
            title=title,
            body=body,
            data_payload=data_payload,
            channel_id=channel_id,
            session=session,
        )

    async def _dispatch_to_user(
        self,
        user_id: UUID,
        title: str,
        body: str,
        data_payload: Dict[str, Any],
        channel_id: str,
        session: AsyncSession,
    ) -> int:
        # 1. Check user push preference
        user_res = await session.execute(
            select(User.push_notifications_enabled).where(User.id == user_id)
        )
        push_enabled = user_res.scalar_one_or_none()
        if push_enabled is False:
            logger.info(f"FCM push aborted: user {user_id} disabled notifications.")
            return 0

        # 2. Fetch active device tokens
        tokens_res = await session.execute(
            select(DeviceFcmToken).where(
                DeviceFcmToken.user_id == user_id,
                DeviceFcmToken.is_active == True,
            )
        )
        token_records = tokens_res.scalars().all()
        if not token_records:
            return 0

        project_id = settings.FIREBASE_PROJECT_ID or "ur-heart-sanctuary"
        fcm_url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
        access_token = self._get_access_token()

        success_count = 0
        tokens_to_deactivate = []

        async with httpx.AsyncClient() as client:
            for record in token_records:
                payload = {
                    "message": {
                        "token": record.token,
                        "notification": {
                            "title": title,
                            "body": body,
                        },
                        "data": {
                            "click_action": "FLUTTER_NOTIFICATION_CLICK",
                            "match_id": str(data_payload.get("match_id", "")),
                            "type": str(data_payload.get("type", "chat_message")),
                        },
                        "android": {
                            "priority": "high" if channel_id == "channel_kinship_dialogue" else "normal",
                            "notification": {
                                "channel_id": channel_id,
                                "color": "#D4AF37",
                                "icon": "ic_sanctuary_notification",
                            },
                        },
                    }
                }

                headers = {
                    "Authorization": f"Bearer {access_token or 'mock-bearer-token'}",
                    "Content-Type": "application/json",
                }

                try:
                    res = await client.post(fcm_url, json=payload, headers=headers, timeout=5.0)
                    if res.status_code == 200:
                        success_count += 1
                    elif res.status_code in (404, 410) or "UNREGISTERED" in res.text or "INVALID_ARGUMENT" in res.text:
                        logger.warning(f"FCM token {record.token[:12]}... stale or unregistered. Deactivating.")
                        tokens_to_deactivate.append(record)
                    else:
                        logger.warning(f"FCM delivery status {res.status_code}: {res.text}")
                except Exception as ex:
                    logger.error(f"FCM dispatch network error for token {record.token[:12]}...: {ex}")

        # 3. Self-healing stale token pruning
        if tokens_to_deactivate:
            for dead_record in tokens_to_deactivate:
                dead_record.is_active = False
            await session.commit()

        return success_count

fcm_service = FcmService()

def get_fcm_service() -> FcmService:
    return fcm_service
