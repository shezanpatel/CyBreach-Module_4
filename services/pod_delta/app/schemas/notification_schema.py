from enum import Enum
from datetime import datetime
from typing import Optional, List

from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
    field_validator,
)


# ============================================================
# ENUMS
# ============================================================

class NotificationStatus(str, Enum):
    """Notification delivery status."""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NotificationChannel(str, Enum):
    """Notification delivery channels."""

    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"
    WEBHOOK = "webhook"
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"


class NotificationPriority(str, Enum):
    """Notification priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


# ============================================================
# REQUEST SCHEMAS
# ============================================================

class NotificationCreate(BaseModel):
    """Schema for creating a new notification."""

    user_id: int = Field(
        ...,
        gt=0,
        description="ID of the user receiving the notification"
    )

    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Notification title"
    )

    message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Notification message content"
    )

    channel: NotificationChannel = Field(
        ...,
        description="Delivery channel for the notification"
    )

    priority: NotificationPriority = Field(
        default=NotificationPriority.MEDIUM,
        description="Priority level of the notification"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": 123,
                "title": "Security Alert",
                "message": "Suspicious login detected from new device",
                "channel": "email",
                "priority": "high"
            }
        }
    )


class NotificationUpdate(BaseModel):
    """Schema for updating an existing notification."""

    title: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="Notification title"
    )

    message: Optional[str] = Field(
        None,
        min_length=1,
        max_length=1000,
        description="Notification message content"
    )

    channel: Optional[NotificationChannel] = Field(
        None,
        description="Delivery channel for the notification"
    )

    priority: Optional[NotificationPriority] = Field(
        None,
        description="Priority level of the notification"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Updated Security Alert",
                "priority": "critical"
            }
        }
    )


class NotificationStatusUpdate(BaseModel):
    """Schema for updating notification status."""

    status: NotificationStatus = Field(
        ...,
        description="New status for the notification"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "read"
            }
        }
    )


class BulkNotificationUpdate(BaseModel):
    """Schema for bulk updating multiple notifications."""

    notification_ids: List[int] = Field(
        ...,
        min_length=1,
        description="List of notification IDs to update"
    )

    status: Optional[NotificationStatus] = Field(
        None,
        description="Status to set for all notifications"
    )

    is_read: Optional[bool] = Field(
        None,
        description="Read status to set for all notifications"
    )

    @field_validator("notification_ids")
    @classmethod
    def validate_notification_ids(cls, value):
        if len(value) > 100:
            raise ValueError(
                "Maximum 100 notifications can be updated at once"
            )
        return value

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "notification_ids": [1, 2, 3, 4, 5],
                "status": "read",
                "is_read": True
            }
        }
    )


class NotificationFilter(BaseModel):
    """Schema for filtering notifications."""

    user_id: Optional[int] = Field(
        None,
        gt=0,
        description="Filter by user ID"
    )

    status: Optional[NotificationStatus] = Field(
        None,
        description="Filter by status"
    )

    channel: Optional[NotificationChannel] = Field(
        None,
        description="Filter by channel"
    )

    priority: Optional[NotificationPriority] = Field(
        None,
        description="Filter by priority"
    )

    is_read: Optional[bool] = Field(
        None,
        description="Filter by read status"
    )

    search: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="Search in title and message"
    )

    start_date: Optional[datetime] = Field(
        None,
        description="Filter by start date"
    )

    end_date: Optional[datetime] = Field(
        None,
        description="Filter by end date"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": 123,
                "status": "read",
                "priority": "high",
                "start_date": "2026-01-01T00:00:00Z",
                "end_date": "2026-12-31T23:59:59Z"
            }
        }
    )


# ============================================================
# RESPONSE SCHEMAS
# ============================================================

class NotificationResponse(BaseModel):
    """Schema for notification response."""

    id: int

    user_id: int = Field(
        ...,
        gt=0,
        description="ID of the user"
    )

    title: str = Field(
        ...,
        description="Notification title"
    )

    message: str = Field(
        ...,
        description="Notification message"
    )

    channel: NotificationChannel = Field(
        ...,
        description="Delivery channel"
    )

    priority: NotificationPriority = Field(
        ...,
        description="Notification priority"
    )

    status: NotificationStatus = Field(
        ...,
        description="Current status"
    )

    is_read: bool = Field(
        ...,
        description="Read status"
    )

    created_at: datetime = Field(
        ...,
        description="Creation timestamp"
    )

    updated_at: Optional[datetime] = Field(
        None,
        description="Last update timestamp"
    )

    read_at: Optional[datetime] = Field(
        None,
        description="When the notification was read"
    )

    delivered_at: Optional[datetime] = Field(
        None,
        description="When the notification was delivered"
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "user_id": 123,
                "title": "Security Alert",
                "message": "Suspicious login detected from new device",
                "channel": "email",
                "priority": "high",
                "status": "delivered",
                "is_read": False,
                "created_at": "2026-07-19T10:30:00Z",
                "updated_at": "2026-07-19T10:30:05Z",
                "read_at": None,
                "delivered_at": "2026-07-19T10:30:03Z"
            }
        }
    )


class NotificationListResponse(BaseModel):
    """Schema for paginated notification list response."""

    total: int = Field(
        ...,
        description="Total number of notifications matching filters"
    )

    skip: int = Field(
        ...,
        description="Number of records skipped"
    )

    limit: int = Field(
        ...,
        description="Number of records returned"
    )

    notifications: List[NotificationResponse] = Field(
        ...,
        description="List of notifications"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total": 50,
                "skip": 0,
                "limit": 10,
                "notifications": []
            }
        }
    )


class UnreadCountResponse(BaseModel):
    """Schema for unread notification count."""

    count: int = Field(
        ...,
        description="Number of unread notifications"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "count": 15
            }
        }
    )


class BulkOperationResponse(BaseModel):
    """Schema for bulk operation response."""

    success: bool = Field(
        ...,
        description="Whether the operation succeeded"
    )

    processed_count: int = Field(
        ...,
        description="Number of notifications processed"
    )

    failed_count: int = Field(
        ...,
        description="Number of notifications that failed"
    )

    failed_ids: Optional[List[int]] = Field(
        None,
        description="IDs of notifications that failed"
    )

    message: str = Field(
        ...,
        description="Status message"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "processed_count": 5,
                "failed_count": 0,
                "failed_ids": [],
                "message": "Successfully marked 5 notifications as read"
            }
        }
    )


class NotificationStatsResponse(BaseModel):
    """Schema for notification statistics."""

    total: int = Field(
        ...,
        description="Total notifications"
    )

    unread: int = Field(
        ...,
        description="Unread notifications"
    )

    read: int = Field(
        ...,
        description="Read notifications"
    )

    by_channel: dict = Field(
        ...,
        description="Counts by channel"
    )

    by_priority: dict = Field(
        ...,
        description="Counts by priority"
    )

    by_status: dict = Field(
        ...,
        description="Counts by status"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total": 100,
                "unread": 30,
                "read": 70,
                "by_channel": {
                    "email": 45,
                    "sms": 20,
                    "push": 35
                },
                "by_priority": {
                    "low": 10,
                    "medium": 50,
                    "high": 30,
                    "critical": 10
                },
                "by_status": {
                    "pending": 5,
                    "sent": 20,
                    "delivered": 60,
                    "read": 10,
                    "failed": 5
                }
            }
        }
    )