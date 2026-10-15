"""Async Kafka/Redpanda consumer and producer."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from app.core.logging import get_logger
from app.core.settings import settings
from app.integration.event_router import EventRouter
from app.integration.event_schemas import CONSUME_TOPICS, PUBLISH_TOPICS, validate_event

logger = get_logger("pod_delta.integration.kafka")


class KafkaProducer:
    def __init__(self) -> None:
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        if not settings.KAFKA_ENABLE:
            return
        self._producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            client_id=settings.KAFKA_CLIENT_ID,
            acks="all",
            enable_idempotence=True,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda v: v.encode("utf-8") if v else None,
        )
        await self._producer.start()

    async def stop(self) -> None:
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None

    @property
    def ready(self) -> bool:
        return self._producer is not None

    async def publish(
        self,
        topic: str,
        payload: dict[str, Any],
        *,
        key: str | None = None,
    ) -> None:
        if topic not in PUBLISH_TOPICS:
            raise ValueError(f"Unsupported publish topic {topic}")
        if self._producer is None:
            logger.warning("kafka_publish_skipped", topic=topic)
            return
        await self._producer.send_and_wait(topic, payload, key=key)


class KafkaConsumer:
    def __init__(self, router: EventRouter) -> None:
        self.router = router
        self._consumer: AIOKafkaConsumer | None = None
        self._task: asyncio.Task[None] | None = None
        self._running = False

    async def start(self) -> None:
        if not settings.KAFKA_ENABLE:
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

    async def stop(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if self._consumer is not None:
            await self._consumer.stop()
            self._consumer = None

    @property
    def ready(self) -> bool:
        return self._consumer is not None and self._running

    async def _run(self) -> None:
        assert self._consumer is not None
        async for message in self._consumer:
            try:
                await self.process_message(message.topic, message.value)
            except Exception:
                logger.exception("kafka_message_processing_failed", topic=message.topic)
            finally:
                await self._consumer.commit()

    async def process_message(self, topic: str, payload: dict[str, Any]) -> None:
        event = validate_event(topic, payload)
        await self.router.route(event)
