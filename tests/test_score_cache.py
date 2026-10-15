from datetime import datetime, timezone

import pytest
from fakeredis import FakeAsyncRedis

from app.events.consumed import Mod3ScoreEvent
from app.services.integration.score_cache import ScoreCache


@pytest.fixture
async def redis():
    client = FakeAsyncRedis(decode_responses=True)
    yield client
    await client.aclose()


def _event(tenant_id: str = "tenant-9") -> Mod3ScoreEvent:
    return Mod3ScoreEvent(
        event_id="score-1",
        tenant_id=tenant_id,
        correlation_id="corr-score",
        occurred_at=datetime.now(timezone.utc),
        score=76.5,
        previous_score=70.0,
        trend="up",
        components={"identity": 80},
    )


async def test_score_cache_key_and_roundtrip(redis):
    cache = ScoreCache(redis, ttl_seconds=3600)
    event = _event()
    key = await cache.store(event)
    assert key == "score:tenant-9"
    stored = await cache.get("tenant-9")
    assert stored is not None
    assert stored["score"] == 76.5
    assert stored["tenant_id"] == "tenant-9"
    assert stored["components"]["identity"] == 80


async def test_missing_score_returns_none(redis):
    cache = ScoreCache(redis)
    assert await cache.get("missing") is None
