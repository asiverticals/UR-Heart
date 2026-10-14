from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_current_user
from backend.app.core.database import get_db
from backend.app.models.domain.admin_telemetry import DeviceFcmToken
from backend.app.models.domain.user import User
from backend.app.schemas.base_response import SanctuaryResponse
from backend.app.schemas.notification import (
    DeviceTokenRegisterRequest,
    DeviceTokenUnregisterRequest,
    NotificationPreferencesRequest,
    NotificationPreferencesResponse,
)

router = APIRouter()

@router.post("/device-token", response_model=SanctuaryResponse[dict])
async def register_device_token(
    payload: DeviceTokenRegisterRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Registers or updates a device FCM push notification token."""
    res = await db.execute(
        select(DeviceFcmToken).where(DeviceFcmToken.token == payload.token)
    )
    existing_token = res.scalar_one_or_none()

    if existing_token:
        existing_token.user_id = current_user.id
        existing_token.platform = payload.platform
        existing_token.is_active = True
    else:
        new_token = DeviceFcmToken(
            user_id=current_user.id,
            token=payload.token,
            platform=payload.platform,
            is_active=True,
        )
        db.add(new_token)

    current_user.fcm_token = payload.token
    if payload.installation_id:
        current_user.last_installation_uuid = payload.installation_id

    await db.commit()
    return SanctuaryResponse(
        data={"registered": True},
        message="Device FCM token registered successfully.",
    )

@router.delete("/device-token", response_model=SanctuaryResponse[dict])
async def unregister_device_token(
    payload: DeviceTokenUnregisterRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deactivates an active device FCM token."""
    res = await db.execute(
        select(DeviceFcmToken).where(
            DeviceFcmToken.token == payload.token,
            DeviceFcmToken.user_id == current_user.id,
        )
    )
    token_row = res.scalar_one_or_none()
    if token_row:
        token_row.is_active = False

    if current_user.fcm_token == payload.token:
        current_user.fcm_token = None

    await db.commit()
    return SanctuaryResponse(
        data={"unregistered": True},
        message="Device FCM token unregistered successfully.",
    )

@router.put("/preferences", response_model=SanctuaryResponse[NotificationPreferencesResponse])
async def update_notification_preferences(
    payload: NotificationPreferencesRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Updates master notification push preferences for the current seeker."""
    current_user.push_notifications_enabled = payload.push_enabled
    await db.commit()

    return SanctuaryResponse(
        data=NotificationPreferencesResponse(
            push_notifications_enabled=current_user.push_notifications_enabled
        ),
        message="Notification preferences updated successfully.",
    )
