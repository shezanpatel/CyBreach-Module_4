from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fakeredis import FakeAsyncRedis

from app.integration.event_router import EventRouter
from app.integration.event_schemas import validate_event
from app.integration.handlers import IntegrationHandlers


class FakeProducer:
    def __init__(self):
        self.publish = AsyncMock()


class FakeWebSocketManager:
    def __init__(self):
        self.broadcast = AsyncMock(return_value=1)


@pytest.fixture
async def integration_parts():
    redis = FakeAsyncRedis(decode_responses=True)
    producer = FakeProducer()
    ws = FakeWebSocketManager()
    handlers = IntegrationHandlers(
        redis=redis,
        producer=producer,
        websocket_manager=ws,
    )
    yield redis, producer, ws, handlers
    await redis.aclose()


def envelope(event_type: str, data: dict):
    return {
        "event_type": event_type,
        "event_id": f"{event_type}-1",
        "tenant_id": "tenant-a",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }


async def test_mod3_score_to_redis_websocket_and_score_displayed(integration_parts):
    redis, producer, ws, handlers = integration_parts
    event = validate_event(
        "mod3.score",
        envelope("mod3.score", {"score": 82.5, "previous_score": 80.0}),
    )

    await EventRouter(handlers).route(event)

    assert await redis.get("score:tenant-a") is not None
    ws.broadcast.assert_awaited_once()
    producer.publish.assert_awaited_once()
    assert producer.publish.await_args.args[0] == "score.displayed"


async def test_achievement_awarded_to_notification_sent(monkeypatch, integration_parts):
    _, producer, _, handlers = integration_parts
    monkeypatch.setattr(handlers, "_create_notification", lambda *args: 123)
    event = validate_event(
        "achievement.awarded",
        envelope(
            "achievement.awarded",
            {
                "achievement_id": "ach-1",
                "achievement_name": "First Defense",
                "user_id": 7,
                "points": 50,
            },
        ),
    )

    await EventRouter(handlers).route(event)

    producer.publish.assert_awaited_once()
    assert producer.publish.await_args.args[0] == "notification.sent"


async def test_wallet_transaction_to_analytics_report(monkeypatch, integration_parts):
    _, producer, _, handlers = integration_parts
    monkeypatch.setattr(handlers, "_create_analytics_record", lambda *args: 456)
    monkeypatch.setattr(handlers, "_create_notification", lambda *args: 123)
    event = validate_event(
        "wallet.transaction",
        envelope(
            "wallet.transaction",
            {
                "transaction_id": "txn-1",
                "amount": 10.0,
                "direction": "credit",
                "user_id": 7,
            },
        ),
    )

    await EventRouter(handlers).route(event)

    published_topics = [call.args[0] for call in producer.publish.await_args_list]
    assert "analytics.report" in published_topics
