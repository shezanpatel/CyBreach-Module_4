"""Process-wide integration runtime (producer, consumer, ws manager)."""

from __future__ import annotations

import asyncio
from typing import Optional

from app.core.logging import get_logger
from app.core.redis import get_redis
from app.core.settings import settings
from app.services.integration.analytics_pipeline import AnalyticsPipeline
from app.services.integration.kafka.consumer import KafkaConsumerService
from app.services.integration.kafka.producer import KafkaProducerService
from app.services.integration.websocket.manager import ConnectionManager

logger = get_logger("pod_delta.runtime")

_producer: Optional[KafkaProducerService] = None
_consumer: Optional[KafkaConsumerService] = None
_ws_manager: Optional[ConnectionManager] = None
_flush_task: Optional[asyncio.Task[None]] = None


def get_producer() -> KafkaProducerService:
    if _producer is None:
        raise RuntimeError("Kafka producer is not started")
    return _producer


def get_consumer() -> KafkaConsumerService:
    if _consumer is None:
        raise RuntimeError("Kafka consumer is not started")
    return _consumer


def get_ws_manager() -> ConnectionManager:
    if _ws_manager is None:
        raise RuntimeError("WebSocket manager is not started")
    return _ws_manager


def set_runtime_for_tests(
    *,
    producer: Optional[KafkaProducerService] = None,
    consumer: Optional[KafkaConsumerService] = None,
    ws_manager: Optional[ConnectionManager] = None,
) -> None:
    global _producer, _consumer, _ws_manager
    if producer is not None:
        _producer = producer
    if consumer is not None:
        _consumer = consumer
    if ws_manager is not None:
        _ws_manager = ws_manager


async def start_integration() -> None:
    global _producer, _consumer, _ws_manager, _flush_task
    try:
        redis = await get_redis()
        await redis.ping()
    except Exception:  # noqa: BLE001
        logger.exception("redis_unavailable")
        return

    _ws_manager = ConnectionManager(redis)
    await _ws_manager.start()
    _producer = KafkaProducerService()
    try:
        await _producer.start()
    except Exception:  # noqa: BLE001
        logger.exception("kafka_producer_start_failed")
    _consumer = KafkaConsumerService(producer=_producer, ws_manager=_ws_manager)
    try:
        await _consumer.start()
    except Exception:  # noqa: BLE001
        logger.exception("kafka_consumer_start_failed")
    _flush_task = asyncio.create_task(_analytics_flush_loop())


async def _analytics_flush_loop() -> None:
    while True:
        await asyncio.sleep(settings.ANALYTICS_FLUSH_INTERVAL_SECONDS)
        if _producer is None:
            continue
        try:
            flushed = await AnalyticsPipeline(_producer).flush_all()
            logger.info("scheduled_analytics_flush", flushed=flushed)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            logger.exception("scheduled_analytics_flush_failed")


async def stop_integration() -> None:
    global _producer, _consumer, _ws_manager, _flush_task
    if _flush_task:
        _flush_task.cancel()
        try:
            await _flush_task
        except asyncio.CancelledError:
            pass
        _flush_task = None
    if _consumer:
        await _consumer.stop()
        _consumer = None
    if _producer:
        await _producer.stop()
        _producer = None
    if _ws_manager:
        await _ws_manager.stop()
        _ws_manager = None
