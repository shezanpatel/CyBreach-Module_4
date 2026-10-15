"""Thin orchestration: preferences → rate limit → Notification Hub → Kafka."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.redis import get_redis
from app.database.connection import SessionLocal
from app.events.base import EventEnvelope
from app.events.published import NotificationSentEvent
from app.models.notification_preference import NotificationPreference
from app.schemas.notification_schema import (
    NotificationChannel,
    NotificationCreate,
    NotificationPriority,
    NotificationStatus,
)
from app.services.integration.kafka.producer import KafkaProducerService
from app.services.integration.rate_limiter import SlidingWindowRateLimiter
from app.services.integration.tenant import tenant_to_user_id
from app.services.integration.websocket.manager import ConnectionManager
from app.services.notification_service import (
    create_notification,
    update_notification_status,
)

logger = get_logger("pod_delta.orchestrator")

CHANNEL_PRIORITY: list[tuple[str, NotificationChannel]] = [
    ("in_app", NotificationChannel.IN_APP),
    ("email", NotificationChannel.EMAIL),
    ("webhook", NotificationChannel.WEBHOOK),
]


class NotificationOrchestrator:
    def __init__(
        self,
        producer: KafkaProducerService,
        ws_manager: ConnectionManager,
    ) -> None:
        self.producer = producer
        self.ws_manager = ws_manager

    def _session(self) -> Session:
        return SessionLocal()

    async def handle_event(
        self,
        event: EventEnvelope,
        *,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        user_id: Optional[int] = None,
        extra_channels: Optional[list[str]] = None,
    ) -> list[NotificationSentEvent]:
        redis = await get_redis()
        limiter = SlidingWindowRateLimiter(redis)
        limit = await limiter.allow(event.tenant_id, event.event_type)
        if not limit.allowed:
            logger.info(
                "notification_rate_limited",
                tenant_id=event.tenant_id,
                event_type=event.event_type,
                correlation_id=event.correlation_id,
            )
            skipped = NotificationSentEvent(
                tenant_id=event.tenant_id,
                correlation_id=event.correlation_id,
                channel="none",
                status="rate_limited",
                triggering_event_type=event.event_type,
                triggering_event_id=event.event_id,
                rate_limited=True,
            )
            await self.producer.publish_owned(skipped)
            return [skipped]

        resolved_user = tenant_to_user_id(event.tenant_id, user_id)
        db = self._session()
        published: list[NotificationSentEvent] = []
        try:
            prefs = (
                db.query(NotificationPreference)
                .filter(NotificationPreference.user_id == resolved_user)
                .first()
            )
            channels = self._select_channels(prefs, extra_channels)
            for channel in channels:
                sent = await self._deliver(
                    db=db,
                    event=event,
                    user_id=resolved_user,
                    channel=channel,
                    title=title,
                    message=message,
                    priority=priority,
                )
                published.append(sent)
        finally:
            db.close()
        return published

    def _select_channels(
        self,
        prefs: Optional[NotificationPreference],
        extra_channels: Optional[list[str]],
    ) -> list[NotificationChannel]:
        wanted = extra_channels or ["in_app", "email", "webhook"]
        selected: list[NotificationChannel] = []
        for name, enum_value in CHANNEL_PRIORITY:
            if name not in wanted:
                continue
            if prefs is None:
                if name in {"in_app", "email"}:
                    selected.append(enum_value)
                continue
            if prefs.is_channel_enabled(name):
                selected.append(enum_value)
        if not selected:
            selected.append(NotificationChannel.IN_APP)
        return selected

    async def _deliver(
        self,
        *,
        db: Session,
        event: EventEnvelope,
        user_id: int,
        channel: NotificationChannel,
        title: str,
        message: str,
        priority: NotificationPriority,
    ) -> NotificationSentEvent:
        created = create_notification(
            db,
            NotificationCreate(
                user_id=user_id,
                title=title,
                message=message,
                channel=channel,
                priority=priority,
            ),
        )
        try:
            update_notification_status(
                db,
                created.id,
                NotificationStatus.SENT,
            )
            status = "sent"
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "notification_status_update_failed",
                error=str(exc),
                tenant_id=event.tenant_id,
                event_type=event.event_type,
                correlation_id=event.correlation_id,
            )
            status = "queued"

        if channel == NotificationChannel.IN_APP:
            await self.ws_manager.broadcast(
                event.tenant_id,
                {
                    "type": "notification",
                    "tenant_id": event.tenant_id,
                    "notification_id": created.id,
                    "title": title,
                    "message": message,
                    "priority": priority.value,
                    "event_type": event.event_type,
                },
            )

        sent_event = NotificationSentEvent(
            tenant_id=event.tenant_id,
            correlation_id=event.correlation_id,
            notification_id=created.id,
            channel=channel.value,
            status=status,
            triggering_event_type=event.event_type,
            triggering_event_id=event.event_id,
        )
        await self.producer.publish_owned(sent_event)
        logger.info(
            "notification_sent",
            tenant_id=event.tenant_id,
            event_type=event.event_type,
            correlation_id=event.correlation_id,
            channel=channel.value,
            notification_id=created.id,
        )
        return sent_event
