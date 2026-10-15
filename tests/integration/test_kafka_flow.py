from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fakeredis import FakeAsyncRedis

from app.core.redis import set_redis_for_tests
from app.events.topics import ConsumeTopic
from app.services.integration.kafka.consumer import KafkaConsumerService
from app.services.integration.kafka.producer import KafkaProducerService
from app.services.integration.websocket.manager import ConnectionManager


def _message(topic: str, value: dict):
    return SimpleNamespace(topic=topic, value=value, partition=0, offset=1)


@pytest.fixture
async def redis():
    client = FakeAsyncRedis(decode_responses=True)
    set_redis_for_tests(client)
    yield client
    set_redis_for_tests(None)
    await client.aclose()


@pytest.fixture
def consumer(redis):
    producer = KafkaProducerService()
    producer.publish = AsyncMock()
    producer.publish_owned = AsyncMock()
    producer.publish_dlt = AsyncMock()
    ws = MagicMock(spec=ConnectionManager)
    ws.broadcast = AsyncMock(return_value=1)
    service = KafkaConsumerService(producer, ws)
    service._consumer = MagicMock()
    service._consumer.commit = AsyncMock()
    service.handlers.orchestrator.handle_event = AsyncMock(return_value=[])
    service.handlers.analytics.ingest = AsyncMock()
    service.handlers.score_flow.handle = AsyncMock()
    return service


async def test_invalid_payload_goes_to_dlt(consumer):
    msg = _message(
        ConsumeTopic.WALLET_TRANSACTION.value,
        {"event_id": "x"},
    )
    await consumer._process_message(msg)
    consumer.producer.publish_dlt.assert_awaited()
    consumer._consumer.commit.assert_awaited()


async def test_valid_mod3_score_dispatches(consumer):
    msg = _message(
        ConsumeTopic.MOD3_SCORE.value,
        {
            "event_id": "score-99",
            "tenant_id": "t9",
            "correlation_id": "c9",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "score": 64.0,
        },
    )
    await consumer._process_message(msg)
    consumer.handlers.score_flow.handle.assert_awaited()
    consumer._consumer.commit.assert_awaited()


async def test_duplicate_event_is_skipped(consumer, redis):
    payload = {
        "event_id": "dup-1",
        "tenant_id": "t9",
        "correlation_id": "c9",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "score": 50.0,
    }
    msg = _message(ConsumeTopic.MOD3_SCORE.value, payload)
    await consumer._process_message(msg)
    await consumer._process_message(msg)
    assert consumer.handlers.score_flow.handle.await_count == 1
