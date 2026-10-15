from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fakeredis import FakeAsyncRedis

from app.core.redis import set_redis_for_tests
from app.events.consumed import WalletTransactionEvent
from app.schemas.notification_schema import NotificationChannel, NotificationPriority
from app.services.integration.orchestrator import NotificationOrchestrator


class DummyNotification:
    def __init__(self, notification_id: int = 7) -> None:
        self.id = notification_id


@pytest.fixture
async def redis():
    client = FakeAsyncRedis(decode_responses=True)
    set_redis_for_tests(client)
    yield client
    set_redis_for_tests(None)
    await client.aclose()


async def test_orchestrator_rate_limit_short_circuits(redis):
    producer = MagicMock()
    producer.publish_owned = AsyncMock()
    ws = MagicMock()
    ws.broadcast = AsyncMock(return_value=0)
    orchestrator = NotificationOrchestrator(producer, ws)

    limiter_result = MagicMock(allowed=False)
    with patch(
        "app.services.integration.orchestrator.SlidingWindowRateLimiter.allow",
        AsyncMock(return_value=limiter_result),
    ):
        event = WalletTransactionEvent(
            event_id="w1",
            tenant_id="t-rate",
            correlation_id="c1",
            occurred_at=datetime.now(timezone.utc),
            transaction_id="txn",
            amount=10,
            direction="credit",
        )
        results = await orchestrator.handle_event(
            event,
            title="Wallet",
            message="credit",
            priority=NotificationPriority.HIGH,
        )
    assert results[0].rate_limited is True
    ws.broadcast.assert_not_called()


async def test_orchestrator_calls_notification_hub(redis):
    producer = MagicMock()
    producer.publish_owned = AsyncMock()
    ws = MagicMock()
    ws.broadcast = AsyncMock(return_value=1)
    orchestrator = NotificationOrchestrator(producer, ws)

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    orchestrator._session = lambda: db  # type: ignore[method-assign]

    with patch(
        "app.services.integration.orchestrator.create_notification",
        return_value=DummyNotification(11),
    ), patch(
        "app.services.integration.orchestrator.update_notification_status",
        return_value=DummyNotification(11),
    ):
        event = WalletTransactionEvent(
            event_id="w2",
            tenant_id="42",
            correlation_id="c2",
            occurred_at=datetime.now(timezone.utc),
            transaction_id="txn",
            amount=10,
            direction="credit",
            user_id=42,
        )
        results = await orchestrator.handle_event(
            event,
            title="Wallet",
            message="credit",
        )
    assert results
    assert results[0].notification_id == 11
    assert results[0].channel in {
        NotificationChannel.IN_APP.value,
        NotificationChannel.EMAIL.value,
    }
    producer.publish_owned.assert_awaited()
