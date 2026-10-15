"""Resilience score cache: score:{tenant_id} with 1h TTL."""

from __future__ import annotations

import json
from typing import Any, Optional

from redis.asyncio import Redis

from app.core.settings import settings
from app.events.consumed import Mod3ScoreEvent

SCORE_KEY = "score:{tenant_id}"


class ScoreCache:
    def __init__(self, redis: Redis, ttl_seconds: int | None = None) -> None:
        self.redis = redis
        self.ttl_seconds = ttl_seconds or settings.SCORE_CACHE_TTL_SECONDS

    def key(self, tenant_id: str) -> str:
        return SCORE_KEY.format(tenant_id=tenant_id)

    async def store(self, event: Mod3ScoreEvent) -> str:
        cache_key = self.key(event.tenant_id)
        payload = event.model_dump(mode="json")
        await self.redis.set(
            cache_key,
            json.dumps(payload),
            ex=self.ttl_seconds,
        )
        return cache_key

    async def get(self, tenant_id: str) -> Optional[dict[str, Any]]:
        raw = await self.redis.get(self.key(tenant_id))
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return json.loads(raw)

    async def delete(self, tenant_id: str) -> None:
        await self.redis.delete(self.key(tenant_id))
