import json
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Index,
)
from sqlalchemy.sql import func

from app.database.connection import Base


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    # User
    user_id = Column(
        Integer,
        unique=True,
        nullable=False,
        index=True
    )

    # Channel preferences
    email_enabled = Column(
        Boolean,
        default=True,
        nullable=False
    )

    sms_enabled = Column(
        Boolean,
        default=False,
        nullable=False
    )

    in_app_enabled = Column(
        Boolean,
        default=True,
        nullable=False
    )

    push_enabled = Column(
        Boolean,
        default=True,
        nullable=False
    )

    webhook_enabled = Column(
        Boolean,
        default=False,
        nullable=False
    )

    whatsapp_enabled = Column(
        Boolean,
        default=False,
        nullable=False
    )

    telegram_enabled = Column(
        Boolean,
        default=False,
        nullable=False
    )

    # Category preferences
    # Stored as JSON text for flexibility
    categories = Column(
        String(1000),
        nullable=True
    )

    # Priority preferences
    receive_low_priority = Column(
        Boolean,
        default=True,
        nullable=False
    )

    receive_medium_priority = Column(
        Boolean,
        default=True,
        nullable=False
    )

    receive_high_priority = Column(
        Boolean,
        default=True,
        nullable=False
    )

    receive_urgent_priority = Column(
        Boolean,
        default=True,
        nullable=False
    )

    receive_critical_priority = Column(
        Boolean,
        default=True,
        nullable=False
    )

    # Quiet hours
    quiet_hours_enabled = Column(
        Boolean,
        default=False,
        nullable=False
    )

    quiet_hours_start = Column(
        String(5),
        nullable=True
    )

    quiet_hours_end = Column(
        String(5),
        nullable=True
    )

    # Digest / frequency
    digest_enabled = Column(
        Boolean,
        default=False,
        nullable=False
    )

    weekly_summary = Column(
        Boolean,
        default=True,
        nullable=False
    )

    frequency = Column(
        String(20),
        default="realtime",
        nullable=False
    )

    # Unsubscribe
    is_unsubscribed_all = Column(
        Boolean,
        default=False,
        nullable=False
    )

    unsubscribe_token = Column(
        String(100),
        unique=True,
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

    # Extra metadata
    # Use extra_metadata as the Python attribute because
    # "metadata" is reserved by SQLAlchemy.
    extra_metadata = Column(
        "metadata",
        String(1000),
        nullable=True
    )

    # Index
    __table_args__ = (
        Index(
            "ix_preferences_user_unsubscribed",
            "user_id",
            "is_unsubscribed_all"
        ),
    )

    def __repr__(self):
        return (
            f"<NotificationPreference("
            f"user_id={self.user_id}, "
            f"email={self.email_enabled}, "
            f"sms={self.sms_enabled})>"
        )

    def is_channel_enabled(self, channel: str) -> bool:
        """Check if a specific channel is enabled."""

        if self.is_unsubscribed_all:
            return False

        mapping = {
            "email": self.email_enabled,
            "sms": self.sms_enabled,
            "in_app": self.in_app_enabled,
            "push": self.push_enabled,
            "webhook": self.webhook_enabled,
            "whatsapp": self.whatsapp_enabled,
            "telegram": self.telegram_enabled,
        }

        return mapping.get(channel, False)

    def is_priority_allowed(self, priority: str) -> bool:
        """Check if a priority level is allowed."""

        if self.is_unsubscribed_all:
            return False

        mapping = {
            "low": self.receive_low_priority,
            "medium": self.receive_medium_priority,
            "high": self.receive_high_priority,
            "urgent": self.receive_urgent_priority,
            "critical": self.receive_critical_priority,
        }

        return mapping.get(priority, True)

    def is_category_enabled(self, category: str) -> bool:
        """Check if a notification category is enabled."""

        if self.is_unsubscribed_all or not self.categories:
            return True

        try:
            categories = json.loads(self.categories)
            return categories.get(category, True)
        except (json.JSONDecodeError, TypeError):
            return True

    def set_categories(self, categories: dict):
        """Set category preferences."""

        self.categories = json.dumps(categories)

    def get_enabled_channels(self) -> list:
        """Get list of enabled channels."""

        channels = []

        if self.email_enabled:
            channels.append("email")

        if self.sms_enabled:
            channels.append("sms")

        if self.in_app_enabled:
            channels.append("in_app")

        if self.push_enabled:
            channels.append("push")

        if self.webhook_enabled:
            channels.append("webhook")

        if self.whatsapp_enabled:
            channels.append("whatsapp")

        if self.telegram_enabled:
            channels.append("telegram")

        return channels

    def is_in_quiet_hours(
        self,
        current_time: datetime = None
    ) -> bool:
        """Check if current time is within quiet hours."""

        if not self.quiet_hours_enabled:
            return False

        if not self.quiet_hours_start or not self.quiet_hours_end:
            return False

        if current_time is None:
            current_time = datetime.now()

        current = current_time.strftime("%H:%M")
        start = self.quiet_hours_start
        end = self.quiet_hours_end

        # Normal range, e.g. 09:00 -> 17:00
        if start <= end:
            return start <= current <= end

        # Overnight range, e.g. 22:00 -> 07:00
        return current >= start or current <= end

    def get_default_preferences(self):
        """Return default preference settings as a template."""

        return {
            "email": True,
            "sms": False,
            "in_app": True,
            "push": True,
            "webhook": False,
            "whatsapp": False,
            "telegram": False,
            "priority": {
                "low": True,
                "medium": True,
                "high": True,
                "urgent": True,
                "critical": True,
            },
            "quiet_hours": {
                "enabled": False,
                "start": "22:00",
                "end": "07:00",
            },
            "frequency": "realtime",
            "digest": False,
            "weekly_summary": True,
        }