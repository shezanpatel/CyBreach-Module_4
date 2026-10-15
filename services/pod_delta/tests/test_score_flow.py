from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fakeredis import FakeAsyncRedis

from app.events.consumed import Mod3ScoreEvent
from app.services.integration.score_flow import ScoreDisplayFlow


@pytest.fixture
async def redis():
    client = FakeAsyncRedis(decode_responses=True)
    yield client
    await client.aclose()


async def test_score_flow_caches_broadcasts_and_publishes(redis, monkeypatch):
    monkeypatch.setattr(
        "app.services.integration.score_flow.get_redis",
        AsyncMock(return_value=redis),
    )
    producer = MagicMock()
    producer.publish_owned = AsyncMock()
    ws_manager = MagicMock()
    ws_manager.broadcast = AsyncMock(return_value=2)

    flow = ScoreDisplayFlow(producer, ws_manager)
    event = Mod3ScoreEvent(
        event_id="s1",
        tenant_id="t-live",
        correlation_id="c1",
        occurred_at=datetime.now(timezone.utc),
        score=91.0,
        trend="up",
    )
    displayed = await flow.handle(event)
    assert displayed.cache_key == "score:t-live"
    assert displayed.push_delivered is True
    assert displayed.score == 91.0
    ws_manager.broadcast.assert_awaited()
    producer.publish_owned.assert_awaited()
    cached = await redis.get("score:t-live")
    assert cached is not None
    assert "91.0" in cached or "91" in cached
