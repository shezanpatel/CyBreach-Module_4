"""Async Redis client used for rate limits, cache, and WebSocket fan-out."""

from typing import Optional

from redis.asyncio import Redis

from app.core.logging import get_logger
from app.core.settings import settings

logger = get_logger("pod_delta.redis")

_redis: Optional[Redis] = None


async def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis


async def ping_redis() -> bool:
    try:
        client = await get_redis()
        return bool(await client.ping())
    except Exception as exc:  # noqa: BLE001
        logger.warning("redis_ping_failed", error=str(exc))
        return False


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


def set_redis_for_tests(client: Optional[Redis]) -> None:
    global _redis
    _redis = client
