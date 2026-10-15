"""Robust Kafka consumer for Pod Delta consume topics."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Optional

from aiokafka import AIOKafkaConsumer, TopicPartition
from aiokafka.errors import KafkaError

from app.core.logging import get_logger
from app.core.redis import get_redis
from app.core.settings import settings
from app.events.registry import EventValidationError, parse_event
from app.events.topics import CONSUME_TOPICS, ConsumeTopic
from app.services.integration.idempotency import IdempotencyStore
from app.services.integration.kafka.handlers import EventHandlers
from app.services.integration.kafka.producer import KafkaProducerService
from app.services.integration.metrics import (
    CONSUMER_LAG,
    EVENTS_CONSUMED,
    EVENTS_ERRORS,
    PROCESS_SECONDS,
)
from app.services.integration.websocket.manager import ConnectionManager

logger = get_logger("pod_delta.kafka.consumer")


class KafkaConsumerService:
    def __init__(
        self,
        producer: KafkaProducerService,
        ws_manager: ConnectionManager,
    ) -> None:
        self.producer = producer
        self.handlers = EventHandlers(producer, ws_manager)
        self._consumer: Optional[AIOKafkaConsumer] = None
        self._task: Optional[asyncio.Task[None]] = None
        self._lag_task: Optional[asyncio.Task[None]] = None
        self._running = False

    async def start(self) -> None:
        if not settings.KAFKA_ENABLE:
            logger.warning("kafka_consumer_disabled")
            return
        self._consumer = AIOKafkaConsumer(
            *CONSUME_TOPICS,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=settings.KAFKA_CONSUMER_GROUP,
            client_id=f"{settings.KAFKA_CLIENT_ID}-consumer",
            enable_auto_commit=False,
            auto_offset_reset=settings.KAFKA_AUTO_OFFSET_RESET,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")) if v else {},
        )
        await self._consumer.start()
        self._running = True
        self._task = asyncio.create_task(self._run())
        self._lag_task = asyncio.create_task(self._report_lag())
        logger.info("kafka_consumer_started", topics=list(CONSUME_TOPICS))

    async def stop(self) -> None:
        self._running = False
        for task in (self._task, self._lag_task):
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        if self._consumer is not None:
            await self._consumer.stop()
            self._consumer = None
        logger.info("kafka_consumer_stopped")

    @property
    def ready(self) -> bool:
        return self._consumer is not None and self._running

    async def _run(self) -> None:
        assert self._consumer is not None
        try:
            async for message in self._consumer:
                await self._process_message(message)
        except asyncio.CancelledError:
            raise
        except KafkaError:
            logger.exception("kafka_consumer_loop_failed")

    async def _process_message(self, message: Any) -> None:
        topic = message.topic
        payload = message.value if isinstance(message.value, dict) else {}
        with PROCESS_SECONDS.labels(topic=topic).time():
            try:
                event = parse_event(topic, payload)
            except EventValidationError as exc:
                EVENTS_ERRORS.labels(topic=topic, reason="validation").inc()
                logger.error(
                    "event_validation_failed",
                    topic=topic,
                    errors=exc.errors,
                )
                await self.producer.publish_dlt(
                    topic, payload, error=str(exc)
                )
                await self._commit()
                return

            redis = await get_redis()
            store = IdempotencyStore(redis)
            if await store.already_processed(topic, event.event_id):
                logger.info(
                    "duplicate_event_skipped",
                    tenant_id=event.tenant_id,
                    event_type=event.event_type,
                    correlation_id=event.correlation_id,
                    event_id=event.event_id,
                )
                await self._commit()
                return

            try:
                await self._dispatch(topic, event)
                EVENTS_CONSUMED.labels(topic=topic).inc()
                await self._commit()
            except Exception as exc:  # noqa: BLE001
                EVENTS_ERRORS.labels(topic=topic, reason="handler").inc()
                logger.exception(
                    "event_handler_failed",
                    tenant_id=event.tenant_id,
                    event_type=event.event_type,
                    correlation_id=event.correlation_id,
                )
                await self.producer.publish_dlt(
                    topic,
                    payload,
                    error=str(exc),
                )
                await self._commit()

    async def _dispatch(self, topic: str, event: Any) -> None:
        mapping = {
            ConsumeTopic.WALLET_TRANSACTION.value: self.handlers.wallet_transaction,
            ConsumeTopic.ENGAGEMENT_LIFECYCLE.value: self.handlers.engagement_lifecycle,
            ConsumeTopic.ENGAGEMENT_COMPLETED.value: self.handlers.engagement_completed,
            ConsumeTopic.MOD3_SCORE.value: self.handlers.mod3_score,
            ConsumeTopic.ACHIEVEMENT_AWARDED.value: self.handlers.achievement_awarded,
            ConsumeTopic.LEADERBOARD_UPDATED.value: self.handlers.leaderboard_updated,
            ConsumeTopic.BENCHMARK_COMPUTED.value: self.handlers.benchmark_computed,
        }
        handler = mapping[topic]
        await handler(event)

    async def _commit(self) -> None:
        if self._consumer is not None:
            await self._consumer.commit()

    async def _report_lag(self) -> None:
        while self._running and self._consumer is not None:
            try:
                partitions = self._consumer.assignment()
                if partitions:
                    end_offsets = await self._consumer.end_offsets(list(partitions))
                    for tp in partitions:
                        tp_obj = tp if isinstance(tp, TopicPartition) else tp
                        committed = await self._consumer.committed(tp_obj)
                        end = end_offsets.get(tp_obj, 0)
                        lag = max(end - (committed or 0), 0)
                        CONSUMER_LAG.labels(
                            topic=tp_obj.topic,
                            partition=str(tp_obj.partition),
                        ).set(lag)
            except Exception:  # noqa: BLE001
                logger.warning("lag_report_failed")
            await asyncio.sleep(15)
