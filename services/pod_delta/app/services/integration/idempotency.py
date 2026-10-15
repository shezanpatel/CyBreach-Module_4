"""Redis-backed Kafka event idempotency."""

from redis.asyncio import Redis

from app.core.settings import settings

DEDUP_KEY = "event_dedup:{topic}:{event_id}"


class IdempotencyStore:
    def __init__(self, redis: Redis, ttl_seconds: int | None = None) -> None:
        self.redis = redis
        self.ttl_seconds = ttl_seconds or settings.IDEMPOTENCY_TTL_SECONDS

    def key(self, topic: str, event_id: str) -> str:
        return DEDUP_KEY.format(topic=topic, event_id=event_id)

    async def already_processed(self, topic: str, event_id: str) -> bool:
        created = await self.redis.set(
            self.key(topic, event_id),
            "1",
            ex=self.ttl_seconds,
            nx=True,
        )
        return created is None or created is False
