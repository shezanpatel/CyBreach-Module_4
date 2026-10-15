"""Kafka producer with at-least-once acknowledgements."""

from __future__ import annotations

import json
from typing import Any, Optional

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError

from app.core.logging import get_logger
from app.core.settings import settings
from app.events.base import dump_event
from app.events.topics import PublishTopic, dead_letter_topic
from app.services.integration.circuit_breaker import CircuitBreaker, CircuitOpenError
from app.services.integration.metrics import EVENTS_DLT, EVENTS_PUBLISHED

logger = get_logger("pod_delta.kafka.producer")


class KafkaProducerService:
    def __init__(self) -> None:
        self._producer: Optional[AIOKafkaProducer] = None
        self._breaker = CircuitBreaker(name="kafka-producer")

    async def start(self) -> None:
        if not settings.KAFKA_ENABLE:
            logger.warning("kafka_producer_disabled")
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
        logger.info("kafka_producer_started")

    async def stop(self) -> None:
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None
            logger.info("kafka_producer_stopped")

    @property
    def ready(self) -> bool:
        return self._producer is not None

    async def publish(
        self,
        topic: str,
        payload: dict[str, Any] | Any,
        *,
        key: Optional[str] = None,
    ) -> None:
        body = dump_event(payload) if hasattr(payload, "model_dump") else payload
        if self._producer is None:
            logger.warning("kafka_publish_skipped", topic=topic)
            return

        async def _send() -> None:
            assert self._producer is not None
            await self._producer.send_and_wait(topic, body, key=key)

        try:
            await self._breaker.call(_send)
            EVENTS_PUBLISHED.labels(topic=topic).inc()
            logger.info("kafka_published", topic=topic, key=key)
        except CircuitOpenError:
            logger.error("kafka_producer_circuit_open", topic=topic)
            raise
        except KafkaError:
            logger.exception("kafka_publish_failed", topic=topic)
            raise

    async def publish_owned(self, event: Any) -> None:
        topic = str(event.event_type)
        if topic not in {item.value for item in PublishTopic}:
            raise ValueError(f"Pod Delta does not publish topic {topic}")
        await self.publish(topic, event, key=event.tenant_id)

    async def publish_dlt(
        self,
        original_topic: str,
        payload: dict[str, Any],
        *,
        error: str,
    ) -> None:
        dlt = dead_letter_topic(original_topic)
        envelope = {
            "original_topic": original_topic,
            "error": error,
            "payload": payload,
        }
        try:
            await self.publish(dlt, envelope, key=payload.get("tenant_id"))
            EVENTS_DLT.labels(topic=original_topic).inc()
        except Exception as exc:  # noqa: BLE001
            logger.error("dlt_publish_failed", topic=dlt, error=str(exc))
