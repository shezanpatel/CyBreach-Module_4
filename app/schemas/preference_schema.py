from typing import  Literal, Optional

from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict
Frequency = Literal["realtime", "hourly", "daily", "weekly"]
TIME_PATTERN = r"^([01]\d|2[0-3]):[0-5]\d$"   # HH:MM, 00:00 to 23:59

class PreferenceCreate(BaseModel):
    """Schema for creating user notification preferences."""

    user_id: int = Field(
        ...,
        gt=0,
        description="ID of the user"
    )

    # Channel preferences
    email_enabled: bool = True
    sms_enabled: bool = False
    in_app_enabled: bool = True
    push_enabled: bool = True
    webhook_enabled: bool = False
    whatsapp_enabled: bool = False
    telegram_enabled: bool = False

    # Priority preferences
    receive_low_priority: bool = True
    receive_medium_priority: bool = True
    receive_high_priority: bool = True
    receive_urgent_priority: bool = True
    receive_critical_priority: bool = True

    # Quiet hours
    quiet_hours_start: Optional[str] = Field(default=None, pattern=TIME_PATTERN)
    quiet_hours_end: Optional[str] = Field(default=None, pattern=TIME_PATTERN)
    ...
    frequency: Frequency = "realtime"

    # Digest / frequency
    digest_enabled: bool = False
    frequency: str = "realtime"

    # Unsubscribe
    is_unsubscribed_all: bool = False

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": 123,
                "email_enabled": True,
                "sms_enabled": False,
                "in_app_enabled": True,
                "push_enabled": True,
                "receive_high_priority": True,
                "quiet_hours_enabled": True,
                "quiet_hours_start": "22:00",
                "quiet_hours_end": "07:00",
                "frequency": "realtime",
                "digest_enabled": False,
                "is_unsubscribed_all": False
            }
        }
    )


class PreferenceUpdate(BaseModel):
    """Schema for updating user notification preferences."""

    # Channel preferences
    email_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None
    in_app_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
    webhook_enabled: Optional[bool] = None
    whatsapp_enabled: Optional[bool] = None
    telegram_enabled: Optional[bool] = None

    # Priority preferences
    receive_low_priority: Optional[bool] = None
    receive_medium_priority: Optional[bool] = None
    receive_high_priority: Optional[bool] = None
    receive_urgent_priority: Optional[bool] = None
    receive_critical_priority: Optional[bool] = None

    # Quiet hours
    quiet_hours_start: Optional[str] = Field(default=None, pattern=TIME_PATTERN)
    quiet_hours_end: Optional[str] = Field(default=None, pattern=TIME_PATTERN)
    ...
    frequency: Optional[Frequency] = None

    # Digest / frequency
    digest_enabled: Optional[bool] = None
    frequency: Optional[str] = None

    # Unsubscribe
    is_unsubscribed_all: Optional[bool] = None


class PreferenceResponse(BaseModel):
    """Schema for preference response."""

    id: int
    user_id: int

    # Channel preferences
    email_enabled: bool
    sms_enabled: bool
    in_app_enabled: bool
    push_enabled: bool
    webhook_enabled: bool
    whatsapp_enabled: bool
    telegram_enabled: bool

    # Priority preferences
    receive_low_priority: bool
    receive_medium_priority: bool
    receive_high_priority: bool
    receive_urgent_priority: bool
    receive_critical_priority: bool

    # Quiet hours
    quiet_hours_enabled: bool
    quiet_hours_start: Optional[str]
    quiet_hours_end: Optional[str]

    # Digest / frequency
    digest_enabled: bool
    weekly_summary: bool
    frequency: str

    # Unsubscribe
    is_unsubscribed_all: bool

    # Timestamps
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )