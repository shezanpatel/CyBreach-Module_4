"""Integration lifespan wiring."""

from __future__ import annotations

from app.core.logging import get_logger
from app.integration.event_router import EventRouter
from app.integration.handlers import IntegrationHandlers
from app.integration.kafka import KafkaConsumer, KafkaProducer
from app.integration.redis_client import close_redis, connect_redis
from app.integration.websocket_manager import WebSocketManager

_producer: KafkaProducer | None = None
_consumer: KafkaConsumer | None = None
_websocket_manager: WebSocketManager | None = None
logger = get_logger("pod_delta.integration.runtime")


def get_producer() -> KafkaProducer:
    if _producer is None:
        raise RuntimeError("Kafka producer is not started")
    return _producer


def get_consumer() -> KafkaConsumer:
    if _consumer is None:
        raise RuntimeError("Kafka consumer is not started")
    return _consumer


def get_websocket_manager() -> WebSocketManager:
    if _websocket_manager is None:
        raise RuntimeError("WebSocket manager is not started")
    return _websocket_manager


async def start_integration() -> None:
    global _producer, _consumer, _websocket_manager
    redis = await connect_redis()
    _websocket_manager = WebSocketManager(redis)
    await _websocket_manager.start()
    _producer = KafkaProducer()
    try:
        await _producer.start()
    except Exception:
        logger.exception("kafka_producer_start_failed")
    handlers = IntegrationHandlers(
        redis=redis,
        producer=_producer,
        websocket_manager=_websocket_manager,
    )
    _consumer = KafkaConsumer(EventRouter(handlers))
    try:
        await _consumer.start()
    except Exception:
        logger.exception("kafka_consumer_start_failed")


async def stop_integration() -> None:
    global _producer, _consumer, _websocket_manager
    if _consumer is not None:
        await _consumer.stop()
        _consumer = None
    if _producer is not None:
        await _producer.stop()
        _producer = None
    if _websocket_manager is not None:
        await _websocket_manager.stop()
        _websocket_manager = None
    await close_redis()
