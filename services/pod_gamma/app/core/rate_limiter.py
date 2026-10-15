import os
import time

from fastapi import HTTPException, Request, status
from redis.asyncio import Redis


RATE_LIMIT_PER_MINUTE = 20

redis_client = Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    decode_responses=True,
)


async def check_rate_limit(request: Request):
    client_ip = request.client.host if request.client else "unknown"

    current_minute = int(time.time() // 60)

    key = f"rate_limit:{client_ip}:{current_minute}"

    request_count = await redis_client.incr(key)

    if request_count == 1:
        await redis_client.expire(key, 60)

    if request_count > RATE_LIMIT_PER_MINUTE:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Maximum 20 requests per minute.",
        )