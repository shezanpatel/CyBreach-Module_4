"""Sliding-window rate limiter: rate_limit:{tenant_id}:{event_type} TTL 60s."""

from __future__ import annotations

import time
from dataclasses import dataclass
from uuid import uuid4

from redis.asyncio import Redis

from app.core.settings import settings
from app.services.integration.metrics import RATE_LIMITED

RATE_LIMIT_KEY = "rate_limit:{tenant_id}:{event_type}"


@dataclass
class RateLimitResult:
    allowed: bool
    count: int
    remaining: int
    key: str


class SlidingWindowRateLimiter:
    def __init__(
        self,
        redis: Redis,
        *,
        window_seconds: int | None = None,
        max_events: int | None = None,
    ) -> None:
        self.redis = redis
        self.window_seconds = window_seconds or settings.RATE_LIMIT_WINDOW_SECONDS
        self.max_events = max_events or settings.RATE_LIMIT_MAX_EVENTS

    def key(self, tenant_id: str, event_type: str) -> str:
        return RATE_LIMIT_KEY.format(tenant_id=tenant_id, event_type=event_type)

    async def allow(self, tenant_id: str, event_type: str) -> RateLimitResult:
        key = self.key(tenant_id, event_type)
        now = time.time()
        window_start = now - self.window_seconds
        member = f"{now}:{uuid4()}"
        pipe = self.redis.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {member: now})
        pipe.zcard(key)
        pipe.expire(key, self.window_seconds)
        results = await pipe.execute()
        count = int(results[2])
        allowed = count <= self.max_events
        if not allowed:
            await self.redis.zrem(key, member)
            count -= 1
            RATE_LIMITED.labels(event_type=event_type).inc()
        remaining = max(self.max_events - count, 0)
        return RateLimitResult(
            allowed=allowed,
            count=count,
            remaining=remaining,
            key=key,
        )
