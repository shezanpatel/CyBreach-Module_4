"""Score cache + live WebSocket push + score.displayed publish."""

from __future__ import annotations

from app.core.logging import get_logger
from app.core.redis import get_redis
from app.events.consumed import Mod3ScoreEvent
from app.events.published import ScoreDisplayedEvent
from app.services.integration.kafka.producer import KafkaProducerService
from app.services.integration.score_cache import ScoreCache
from app.services.integration.websocket.manager import ConnectionManager

logger = get_logger("pod_delta.score_flow")


class ScoreDisplayFlow:
    def __init__(
        self,
        producer: KafkaProducerService,
        ws_manager: ConnectionManager,
    ) -> None:
        self.producer = producer
        self.ws_manager = ws_manager

    async def handle(self, event: Mod3ScoreEvent) -> ScoreDisplayedEvent:
        redis = await get_redis()
        cache = ScoreCache(redis)
        cache_key = await cache.store(event)
        push_count = await self.ws_manager.broadcast(
            event.tenant_id,
            {
                "type": "score_update",
                "tenant_id": event.tenant_id,
                "score": event.score,
                "previous_score": event.previous_score,
                "trend": event.trend,
                "components": event.components,
                "cache_key": cache_key,
            },
        )
        displayed = ScoreDisplayedEvent(
            tenant_id=event.tenant_id,
            correlation_id=event.correlation_id,
            score=event.score,
            cache_key=cache_key,
            push_delivered=push_count > 0,
        )
        await self.producer.publish_owned(displayed)
        logger.info(
            "score_displayed",
            tenant_id=event.tenant_id,
            event_type=event.event_type,
            correlation_id=event.correlation_id,
            cache_key=cache_key,
            push_delivered=displayed.push_delivered,
        )
        return displayed
