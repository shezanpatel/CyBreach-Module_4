"""Thin async handlers that call existing Notification and Analytics services."""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from redis.asyncio import Redis

from app.core.settings import settings
from app.database.connection import SessionLocal as NotificationSessionLocal
from app.database.db_connection import SessionLocal as AnalyticsSessionLocal
from app.integration.event_schemas import (
    AchievementAwardedData,
    EngagementCompletedData,
    EngagementLifecycleData,
    Mod3ScoreData,
    ValidatedEvent,
    WalletTransactionData,
    published_envelope,
)
from app.integration.websocket_manager import WebSocketManager
from app.schemas.analytics_schema import AnalyticsCreate
from app.schemas.notification_schema import (
    NotificationChannel,
    NotificationCreate,
    NotificationPriority,
    NotificationStatus,
)
from app.services.analytics_engine_service import create_analytics
from app.services.notification_service import create_notification, update_notification_status

if TYPE_CHECKING:
    from app.integration.kafka import KafkaProducer

SCORE_KEY = "score:{tenant_id}"
RATE_LIMIT_KEY = "rate_limit:{tenant_id}:{event_type}"


class SlidingWindowRateLimiter:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    def key(self, tenant_id: str, event_type: str) -> str:
        return RATE_LIMIT_KEY.format(tenant_id=tenant_id, event_type=event_type)

    async def allow(self, tenant_id: str, event_type: str) -> bool:
        key = self.key(tenant_id, event_type)
        now = time.time()
        member = f"{now}:{uuid4()}"
        pipe = self.redis.pipeline()
        pipe.zremrangebyscore(key, 0, now - settings.RATE_LIMIT_WINDOW_SECONDS)
        pipe.zadd(key, {member: now})
        pipe.zcard(key)
        pipe.expire(key, 60)
        results = await pipe.execute()
        allowed = int(results[2]) <= settings.RATE_LIMIT_MAX_EVENTS
        if not allowed:
            await self.redis.zrem(key, member)
        return allowed


class IntegrationHandlers:
    def __init__(
        self,
        *,
        redis: Redis,
        producer: "KafkaProducer",
        websocket_manager: WebSocketManager,
    ) -> None:
        self.redis = redis
        self.producer = producer
        self.websocket_manager = websocket_manager
        self.rate_limiter = SlidingWindowRateLimiter(redis)

    async def handle_score(self, event: ValidatedEvent) -> None:
        data = event.data
        assert isinstance(data, Mod3ScoreData)
        key = SCORE_KEY.format(tenant_id=event.tenant_id)
        payload = {
            "event_type": event.event_type,
            "event_id": event.event_id,
            "tenant_id": event.tenant_id,
            "timestamp": event.timestamp.isoformat(),
            "data": data.model_dump(mode="json"),
        }
        await self.redis.set(key, json.dumps(payload), ex=3600)
        await self.websocket_manager.broadcast(
            event.tenant_id,
            {"type": "score_update", "tenant_id": event.tenant_id, **data.model_dump(mode="json")},
        )
        await self.producer.publish(
            "score.displayed",
            published_envelope(
                event_type="score.displayed",
                tenant_id=event.tenant_id,
                data={"score": data.score, "cache_key": key, "source_event_id": event.event_id},
            ),
            key=event.tenant_id,
        )

    async def handle_notification(self, event: ValidatedEvent) -> None:
        if not await self.rate_limiter.allow(event.tenant_id, event.event_type):
            return
        data = event.data
        title = "CyBreach update"
        message = f"{event.event_type} received"
        user_id = 1
        priority = NotificationPriority.MEDIUM
        if isinstance(data, AchievementAwardedData):
            title = "Achievement unlocked"
            message = f"{data.achievement_name} awarded (+{data.points})"
            user_id = data.user_id or 1
            priority = NotificationPriority.HIGH
        elif isinstance(data, EngagementCompletedData):
            title = "Engagement completed"
            message = f"Engagement {data.engagement_id} finished with {data.outcome}"
            user_id = data.user_id or 1
        elif isinstance(data, EngagementLifecycleData):
            title = "Engagement update"
            message = f"Engagement {data.engagement_id} moved to {data.stage}"
            user_id = data.user_id or 1
        elif isinstance(data, WalletTransactionData):
            title = "Wallet activity"
            message = f"{data.amount} {data.currency} {data.direction}"
            user_id = data.user_id or 1

        notification_id = await asyncio.to_thread(
            self._create_notification,
            user_id,
            title,
            message,
            priority,
        )
        await self.producer.publish(
            "notification.sent",
            published_envelope(
                event_type="notification.sent",
                tenant_id=event.tenant_id,
                data={
                    "notification_id": notification_id,
                    "status": "sent",
                    "triggering_event_type": event.event_type,
                    "triggering_event_id": event.event_id,
                },
            ),
            key=event.tenant_id,
        )

    def _create_notification(
        self,
        user_id: int,
        title: str,
        message: str,
        priority: NotificationPriority,
    ) -> int:
        db = NotificationSessionLocal()
        try:
            notification = create_notification(
                db,
                NotificationCreate(
                    user_id=user_id,
                    title=title,
                    message=message,
                    channel=NotificationChannel.IN_APP,
                    priority=priority,
                ),
            )
            update_notification_status(db, notification.id, NotificationStatus.SENT)
            return int(notification.id)
        finally:
            db.close()

    async def handle_analytics(self, event: ValidatedEvent) -> None:
        if event.event_type not in {
            "wallet.transaction",
            "engagement.lifecycle",
            "engagement.completed",
        }:
            return
        record_id = await asyncio.to_thread(self._create_analytics_record, event)
        await self.producer.publish(
            "analytics.report",
            published_envelope(
                event_type="analytics.report",
                tenant_id=event.tenant_id,
                data={
                    "record_id": record_id,
                    "source_event_type": event.event_type,
                    "source_event_id": event.event_id,
                },
            ),
            key=event.tenant_id,
        )

    def _create_analytics_record(self, event: ValidatedEvent) -> int:
        db = AnalyticsSessionLocal()
        try:
            record = create_analytics(
                db,
                AnalyticsCreate(
                    tenant_id=event.tenant_id,
                    tenant_name=event.tenant_id,
                    resilience_score=0.0,
                    report_month=datetime.now(timezone.utc).strftime("%Y-%m"),
                    metrics_json={
                        "source": "pod-delta-integration",
                        "event_type": event.event_type,
                        "event_id": event.event_id,
                        "data": event.data.model_dump(mode="json"),
                    },
                ),
            )
            return int(record.id)
        finally:
            db.close()
