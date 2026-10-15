import pytest
from fakeredis import FakeAsyncRedis

from app.services.integration.rate_limiter import SlidingWindowRateLimiter


@pytest.fixture
async def redis():
    client = FakeAsyncRedis(decode_responses=True)
    yield client
    await client.aclose()


async def test_rate_limit_key_pattern(redis):
    limiter = SlidingWindowRateLimiter(redis, window_seconds=60, max_events=3)
    assert limiter.key("acme", "wallet.transaction") == "rate_limit:acme:wallet.transaction"


async def test_sliding_window_allows_then_blocks(redis):
    limiter = SlidingWindowRateLimiter(redis, window_seconds=60, max_events=2)
    first = await limiter.allow("acme", "wallet.transaction")
    second = await limiter.allow("acme", "wallet.transaction")
    third = await limiter.allow("acme", "wallet.transaction")
    assert first.allowed is True
    assert second.allowed is True
    assert third.allowed is False
    assert third.key == "rate_limit:acme:wallet.transaction"


async def test_rate_limit_is_scoped_per_event_type(redis):
    limiter = SlidingWindowRateLimiter(redis, window_seconds=60, max_events=1)
    a = await limiter.allow("acme", "wallet.transaction")
    b = await limiter.allow("acme", "achievement.awarded")
    assert a.allowed is True
    assert b.allowed is True
