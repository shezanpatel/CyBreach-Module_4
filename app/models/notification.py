from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Enum, Index
from sqlalchemy.sql import func

from app.database.connection import Base
from app.schemas.notification_schema import (
    NotificationStatus,
    NotificationChannel,
    NotificationPriority,
)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)

    # User ID
    user_id = Column(
        Integer,
        nullable=False,
        index=True
    )

    # Content
    title = Column(String(255), nullable=False)
    message = Column(String(1000), nullable=False)

    # Channel, priority and status
    channel = Column(
        Enum(NotificationChannel),
        nullable=False
    )

    priority = Column(
        Enum(NotificationPriority),
        nullable=False,
        default=NotificationPriority.MEDIUM
    )

    status = Column(
        Enum(NotificationStatus),
        nullable=False,
        default=NotificationStatus.PENDING
    )

    # Read status
    is_read = Column(
        Boolean,
        default=False,
        nullable=False
    )

    # Optional metadata
    extra_metadata = Column(
        "metadata",
        String(500),
        nullable=True
    )

    # Timestamps
    created_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False
    )

    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    read_at = Column(
        DateTime,
        nullable=True
    )

    delivered_at = Column(
        DateTime,
        nullable=True
    )

    # Indexes
    __table_args__ = (
        Index(
            "ix_notifications_user_status",
            "user_id",
            "status"
        ),
        Index(
            "ix_notifications_user_read",
            "user_id",
            "is_read"
        ),
        Index(
            "ix_notifications_created_at",
            "created_at"
        ),
        Index(
            "ix_notifications_channel_status",
            "channel",
            "status"
        ),
    )

    def __repr__(self):
        return (
            f"<Notification("
            f"id={self.id}, "
            f"user_id={self.user_id}, "
            f"title='{self.title[:20]}...', "
            f"status='{self.status.value}')>"
        )

    def mark_as_read(self):
        """Mark notification as read."""
        self.is_read = True
        self.status = NotificationStatus.READ
        self.read_at = datetime.utcnow()

    def mark_as_delivered(self):
        """Mark notification as delivered."""
        self.status = NotificationStatus.DELIVERED
        self.delivered_at = datetime.utcnow()