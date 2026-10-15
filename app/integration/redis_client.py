"""Async Redis client for rate limits, score cache, and WebSocket fan-out."""

from __future__ import annotations

from redis.asyncio import Redis

from app.core.settings import settings

_redis: Redis | None = None


async def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis


async def connect_redis() -> Redis:
    client = await get_redis()
    await client.ping()
    return client


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


def set_redis_for_tests(client: Redis | None) -> None:
    global _redis
    _redis = client

