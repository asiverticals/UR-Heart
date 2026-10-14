from typing import Literal, Optional
from pydantic import BaseModel, Field

class DeviceTokenRegisterRequest(BaseModel):
    token: str = Field(..., min_length=1, max_length=512, description="FCM device push registration token")
    platform: Literal["android", "ios", "web"] = Field(..., description="Target device platform")
    installation_id: Optional[str] = Field(None, max_length=64, description="Unique client hardware installation UUID")

class DeviceTokenUnregisterRequest(BaseModel):
    token: str = Field(..., min_length=1, max_length=512, description="FCM device registration token to deactivate")

class NotificationPreferencesRequest(BaseModel):
    push_enabled: bool = Field(..., description="Master toggle for background push notifications")

class NotificationPreferencesResponse(BaseModel):
    push_notifications_enabled: bool
