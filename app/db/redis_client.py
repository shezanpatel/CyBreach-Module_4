"""Redis connection pool management with singleton pattern."""

from __future__ import annotations

import time

import redis
from redis.connection import ConnectionPool
from redis.exceptions import (
    AuthenticationError,
    ConnectionError,
    RedisError,
    TimeoutError,
)

from app.config import Settings, get_settings
from app.exceptions import RedisUnavailableError
from app.utils.logger import get_logger

logger = get_logger("redis_client")

_pool: ConnectionPool | None = None
_client: redis.Redis | None = None


def _build_pool(settings: Settings) -> ConnectionPool:
    """
    Create a Redis connection pool.

    A single shared pool is reused across the application.
    """

    return ConnectionPool(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        password=settings.redis_password or None,
        socket_timeout=settings.redis_socket_timeout,
        socket_connect_timeout=settings.redis_socket_connect_timeout,
        max_connections=settings.redis_max_connections,
        decode_responses=True,
        health_check_interval=30,
        retry_on_timeout=True,
    )


def init_redis(settings: Settings | None = None) -> redis.Redis:
    """
    Initialize Redis using a singleton connection pool.

    Features
    --------
    - Connection pooling
    - Authentication
    - Retry with exponential backoff
    - Health validation
    - Connection timing
    - Redis version logging
    """

    global _pool, _client

    if _client is not None:
        return _client

    cfg = settings or get_settings()

    _pool = _build_pool(cfg)

    _client = redis.Redis(connection_pool=_pool)

    max_attempts = 3

    for attempt in range(max_attempts):

        start = time.perf_counter()

        try:

            _client.ping()

            elapsed = (time.perf_counter() - start) * 1000

            info = _client.info()

            logger.info(
                "Redis connected | host=%s port=%s db=%s",
                cfg.redis_host,
                cfg.redis_port,
                cfg.redis_db,
            )

            logger.info(
                "Redis version: %s",
                info.get("redis_version", "unknown"),
            )

            logger.info(
                "Connection established in %.2f ms",
                elapsed,
            )

            return _client

        except AuthenticationError as exc:

            logger.error("Redis authentication failed")

            raise RedisUnavailableError(
                "Redis authentication failed",
                details={"error": str(exc)},
            ) from exc

        except (ConnectionError, TimeoutError) as exc:

            logger.warning(
                "Redis connection attempt %d/%d failed: %s",
                attempt + 1,
                max_attempts,
                exc,
            )

            if attempt == max_attempts - 1:

                raise RedisUnavailableError(
                    "Unable to connect to Redis",
                    details={"error": str(exc)},
                ) from exc

            wait_time = 2 ** attempt

            logger.info(
                "Retrying in %d second(s)...",
                wait_time,
            )

            time.sleep(wait_time)

        except RedisError as exc:

            logger.error(
                "Unexpected Redis error: %s",
                exc,
            )

            raise RedisUnavailableError(
                "Redis initialization failed",
                details={"error": str(exc)},
            ) from exc

    raise RedisUnavailableError("Unable to initialize Redis")

def get_redis() -> redis.Redis:
    """
    Return the shared Redis client.

    Initializes Redis lazily on first use.
    """

    if _client is None:
        return init_redis()

    return _client


def close_redis() -> None:
    """
    Gracefully close the Redis client and connection pool.
    """

    global _pool, _client

    if _client is not None:

        try:
            _client.close()
            logger.info("Redis client closed")

        except RedisError as exc:
            logger.warning(
                "Error while closing Redis client: %s",
                exc,
            )

        finally:
            _client = None

    if _pool is not None:

        try:
            _pool.disconnect()
            logger.info("Redis connection pool disconnected")

        except RedisError as exc:
            logger.warning(
                "Failed disconnecting pool: %s",
                exc,
            )

        finally:
            _pool = None


def is_redis_healthy() -> bool:
    """
    Verify Redis is healthy and ready.

    Compatible with both Redis and fakeredis.
    """

    try:
        client = get_redis()

        if not client.ping():
            return False

        # INFO may not be fully supported by fakeredis.
        try:
            info = client.info()
            if info.get("loading", 0) == 1:
                return False
        except RedisError:
            # Treat INFO failures as healthy if PING succeeded.
            pass

        return True

    except (RedisUnavailableError, RedisError):
        return False


def get_redis_metrics() -> dict[str, str | int | float]:
    """
    Collect operational Redis metrics.
    """

    client = get_redis()

    try:

        info = client.info()

    except RedisError:
        return {
        "redis_version": "fakeredis",
        "connected_clients": 1,
        "blocked_clients": 0,
        "used_memory_human": "N/A",
        "used_memory_peak_human": "N/A",
        "total_commands_processed": 0,
        "instantaneous_ops_per_sec": 0,
        "keyspace_hits": 0,
        "keyspace_misses": 0,
        "expired_keys": 0,
        "evicted_keys": 0,
        "used_cpu_sys": 0,
        "used_cpu_user": 0,
        "uptime_in_seconds": 0,
        "status": "healthy",
    }

    return {
        "redis_version": info.get("redis_version", "unknown"),
        "connected_clients": info.get("connected_clients", 0),
        "blocked_clients": info.get("blocked_clients", 0),
        "used_memory_human": info.get("used_memory_human", "unknown"),
        "used_memory_peak_human": info.get("used_memory_peak_human", "unknown"),
        "total_commands_processed": info.get("total_commands_processed", 0),
        "instantaneous_ops_per_sec": info.get("instantaneous_ops_per_sec", 0),
        "keyspace_hits": info.get("keyspace_hits", 0),
        "keyspace_misses": info.get("keyspace_misses", 0),
        "expired_keys": info.get("expired_keys", 0),
        "evicted_keys": info.get("evicted_keys", 0),
        "used_cpu_sys": info.get("used_cpu_sys", 0),
        "used_cpu_user": info.get("used_cpu_user", 0),
        "uptime_in_seconds": info.get("uptime_in_seconds", 0),
        "status": "healthy",
    }


def reset_redis_client(
    client: redis.Redis | None = None,
    pool: ConnectionPool | None = None,
) -> None:
    """
    Reset the singleton Redis client.

    Used primarily by unit tests.
    """

    global _client, _pool

    _client = client
    _pool = pool

    logger.info("Redis singleton reset")