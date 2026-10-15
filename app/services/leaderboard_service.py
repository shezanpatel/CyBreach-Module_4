"""Leaderboard business logic backed by Redis Sorted Sets (ZSET)."""

from __future__ import annotations

import math
import re
import time
import redis

from app.config import Settings, get_settings
from app.db.redis_client import get_redis
from app.tenant_contract import (
    validate_tenant_id,
    validate_industry,
    validate_region,
    validate_size,
    industry_key,
    region_key,
    size_key,
    tenant_members_key,
)
from app.exceptions import (
    InvalidScoreError,
    InvalidTenantMetadataError,
    NegativeScoreError,
    RedisTimeoutError,
    RedisUnavailableError,
    UserNotFoundError,
)
from app.models.schemas import PlayerEntry
from app.utils.logger import get_logger

logger = get_logger("leaderboard_service")
USERNAME_REGEX = re.compile(r"^[A-Za-z0-9_.-]{3,30}$")


class LeaderboardService:
    """
    Service layer for leaderboard operations.

    All score mutations use atomic Redis commands (ZADD, ZINCRBY, ZREM, DEL).
    Rank lookups use O(log N) ZREVRANK and ZREVRANGE operations.
    """

    def __init__(
        self,
        redis_client: redis.Redis | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._redis = redis_client
        self._settings = settings or get_settings()

    @property
    def redis(self) -> redis.Redis:
        """Lazy-resolve the Redis client."""
        if self._redis is None:
            self._redis = get_redis()
        return self._redis

    @staticmethod
    def _validate_username(username: str) -> str:
        """
        Validate username before storing it in Redis.
        """

        username = username.strip()

        if not username:
            raise InvalidScoreError(
                "Username cannot be empty",
                details={"username": username},
            )

        if not USERNAME_REGEX.fullmatch(username):
            raise InvalidScoreError(
                "Username contains invalid characters",
                details={"username": username},
            )

        return username

    @property
    def key(self) -> str:
        """Redis ZSET key for the global leaderboard."""
        return self._settings.redis_leaderboard_key

    def _handle_redis_error(self, operation: str, exc: redis.RedisError) -> None:
        """Translate Redis errors into domain exceptions."""
        if isinstance(exc, redis.TimeoutError):
            logger.error("Redis timeout during %s: %s", operation, exc)
            raise RedisTimeoutError(
                f"Redis operation timed out: {operation}",
                details={"operation": operation},
            ) from exc

        logger.error("Redis error during %s: %s", operation, exc)
        raise RedisUnavailableError(
            f"Redis unavailable during {operation}",
            details={"operation": operation, "error": str(exc)},
        ) from exc

    @staticmethod
    def _validate_score(score: float) -> float:
        """Validate and normalize a score value."""
        if math.isnan(score) or math.isinf(score):
            raise InvalidScoreError(
                "Score must be a finite number",
                details={"score": score},
            )
        if score < 0:
            raise NegativeScoreError(
                "Score cannot be negative",
                details={"score": score},
            )
        return float(score)

    def set_score(self, username: str, score: float) -> float:
        """
        Create or update a player's score using ZADD.

        Args:
            username: Unique player identifier.
            score: Non-negative score value.

        Returns:
            The stored score.
        """
        username = self._validate_username(username)
        validated = self._validate_score(score)
        start = time.perf_counter()
        try:
            self.redis.zadd(self.key, {username: validated})
            logger.info("Score set | user=%s score=%s", username, validated)
            elapsed = (time.perf_counter() - start) * 1000
            logger.info(
                "ZADD completed in %.2f ms",
                elapsed,
            )
            return validated
        except redis.RedisError as exc:
            self._handle_redis_error("ZADD", exc)
            raise  # unreachable; satisfies type checker
    def set_tenant_score(
        self,
        username: str,
        score: float,
        tenant_id: str,
        industry: str,
        region: str,
        size: str,
    ) -> float:
        """Set a tenant score across all absolute leaderboards."""
        username = self._validate_username(username)
        validated_score = self._validate_score(score)

        try:
            tenant_id = validate_tenant_id(tenant_id)
            industry = validate_industry(industry)
            region = validate_region(region)
            size = validate_size(size)
        except ValueError as exc:
            raise InvalidTenantMetadataError(
            str(exc),
            details={"tenant_id": tenant_id},
            ) from exc

        try:
            pipe = self.redis.pipeline(transaction=True)

            # Preserve the existing configured global leaderboard.
            pipe.zadd(self.key, {username: validated_score})

            # Update the tenant's industry, region, and size leaderboards.
            pipe.zadd(industry_key(industry), {username: validated_score})
            pipe.zadd(region_key(region), {username: validated_score})
            pipe.zadd(size_key(size), {username: validated_score})

            # Record the tenant's membership.
            pipe.sadd(tenant_members_key(tenant_id), username)

            pipe.execute()

            logger.info(
                "Tenant score set | tenant=%s user=%s score=%s",
                tenant_id,
                username,
                validated_score,
            )
            return validated_score

        except redis.RedisError as exc:
            self._handle_redis_error("TENANT_SCORE_UPDATE", exc)
            raise

    # ------------------------------------------------------------------
    # Bulk Operations
    # Optimized for tournaments and leaderboard imports.
    # Uses a single Redis ZADD command.
    # ------------------------------------------------------------------
    def set_scores_bulk(
        self,
        scores: dict[str, float],
    ) -> int:
        """
        Bulk insert/update multiple users using one ZADD command.
        """
        if not scores:
            return 0

        start = time.perf_counter()

        validated: dict[str, float] = {}

        for username, score in scores.items():
            username = self._validate_username(username)
            validated[username] = self._validate_score(score)

        try:
            self.redis.zadd(self.key, validated)

            elapsed = (time.perf_counter() - start) * 1000

            logger.info(
                "Bulk inserted %d users in %.2f ms",
                len(validated),
                elapsed,
            )

            return len(validated)
        except redis.RedisError as exc:
            self._handle_redis_error("ZADD_BULK", exc)
            raise

    def increment_score(self, username: str, increment: float) -> float:
        """
        Atomically increment a player's score using ZINCRBY.

        Creates the player with the increment value if they do not exist.

        Args:
            username: Unique player identifier.
            increment: Positive value to add.

        Returns:
            The new score after increment.
        """
        username = self._validate_username(username)
        if increment <= 0:
            raise InvalidScoreError(
                "Increment must be a positive number",
                details={"increment": increment},
            )

        start = time.perf_counter()

        try:
            current = self.redis.zscore(self.key, username)
            if current is None:
                new_score = self._validate_score(increment)
                self.redis.zadd(self.key, {username: new_score})
            else:
                new_score = self.redis.zincrby(self.key, increment, username)
                if new_score < 0:
                    self.redis.zadd(self.key, {username: 0})
                    raise NegativeScoreError(
                        "Increment would result in a negative score",
                        details={"username": username, "result": new_score},
                    )

            elapsed = (time.perf_counter() - start) * 1000

            logger.info(
                "Score incremented | user=%s increment=%s new_score=%s time=%.2f ms",
                username,
                increment,
                new_score,
                elapsed,
            )
            return float(new_score)
        except (InvalidScoreError, NegativeScoreError):
            raise
        except redis.RedisError as exc:
            self._handle_redis_error("ZINCRBY", exc)
            raise

    def get_top_players(self, limit: int = 10) -> tuple[list[PlayerEntry], int]:
        """
        Return the top N players by score using ZREVRANGE.

        Args:
            limit: Maximum number of entries to return (1-1000).

        Returns:
            Tuple of (ranked entries, total player count).
        """
        limit = max(1, min(limit, 1000))
        start = time.perf_counter()
        try:
            total = self.redis.zcard(self.key)
            raw = self.redis.zrevrange(
                self.key,
                0,
                limit - 1,
                withscores=True,
            )
            entries = [
                PlayerEntry(
                    rank=index + 1,
                    username=member,
                    score=float(score),
                )
                for index, (member, score) in enumerate(raw)
            ]

            elapsed = (time.perf_counter() - start) * 1000
            logger.info(
                "ZREVRANGE completed in %.2f ms",
                elapsed,
            )

            return entries, total
        except redis.RedisError as exc:
            self._handle_redis_error("ZREVRANGE", exc)
            raise

    def get_rank(self, username: str) -> tuple[float, int]:
        """
        Return a player's score and rank using a Redis pipeline.

        Uses a Redis pipeline to fetch the score and rank in a single
        network round trip, improving performance.

        Args:
            username: Player to look up.

        Returns:
            Tuple of (score, 1-based rank).

        Raises:
            UserNotFoundError: If the player is not on the leaderboard.
        """
        username = self._validate_username(username)

        start = time.perf_counter()

        try:
            pipe = self.redis.pipeline()

            pipe.zscore(self.key, username)
            pipe.zrevrank(self.key, username)

            score, rank = pipe.execute()

            if score is None or rank is None:
                raise UserNotFoundError(
                    f"User '{username}' not found on leaderboard",
                    details={"username": username},
                )

            elapsed = (time.perf_counter() - start) * 1000

            logger.info(
                "ZREVRANK/ZSCORE completed | user=%s rank=%s time=%.2f ms",
                username,
                int(rank) + 1,
                elapsed,
            )

            return float(score), int(rank) + 1

        except UserNotFoundError:
            raise

        except redis.RedisError as exc:
            self._handle_redis_error("ZREVRANK/ZSCORE", exc)
            raise

    def delete_user(self, username: str) -> bool:
        """
        Remove a player from the leaderboard using ZREM.

        Args:
            username: Player to remove.

        Returns:
            True if the user was removed, False if they did not exist.

        Raises:
            UserNotFoundError: If the player does not exist.
        """
        username = self._validate_username(username)

        start = time.perf_counter()

        try:
            removed = self.redis.zrem(self.key, username)

            if removed == 0:
                raise UserNotFoundError(
                    f"User '{username}' not found on leaderboard",
                    details={"username": username},
                )

            elapsed = (time.perf_counter() - start) * 1000

            logger.info(
                "User deleted | user=%s time=%.2f ms",
                username,
                elapsed,
            )

            return True

        except UserNotFoundError:
            raise

        except redis.RedisError as exc:
            self._handle_redis_error("ZREM", exc)
            raise

    # ------------------------------------------------------------------
    # Batch Operations
    # Uses Redis pipeline to minimize network round trips.
    # ------------------------------------------------------------------
    def delete_users(
        self,
        usernames: list[str],
    ) -> int:
        """
        Delete multiple users using a Redis pipeline.
        """
        if not usernames:
            return 0

        start = time.perf_counter()

        try:
            pipe = self.redis.pipeline()

            for username in usernames:
                username = self._validate_username(username)
                pipe.zrem(self.key, username)

            results = pipe.execute()

            removed = sum(int(result) for result in results)

            elapsed = (time.perf_counter() - start) * 1000

            logger.info(
                "Deleted %d users in %.2f ms",
                removed,
                elapsed,
            )

            return removed
        except redis.RedisError as exc:
            self._handle_redis_error("ZREM_BULK", exc)
            raise

    def reset_leaderboard(self) -> None:
        """Clear the entire leaderboard using DEL."""
        start = time.perf_counter()
        try:
            self.redis.delete(self.key)
            elapsed = (time.perf_counter() - start) * 1000
            logger.info(
                "Leaderboard reset | key=%s time=%.2f ms",
                self.key,
                elapsed,
            )
        except redis.RedisError as exc:
            self._handle_redis_error("DEL", exc)
            raise


def get_leaderboard_service() -> LeaderboardService:
    """FastAPI dependency provider for LeaderboardService."""
    return LeaderboardService()