"""Custom domain exceptions for the leaderboard service."""

from typing import Any


class LeaderboardError(Exception):
    """Base exception for all leaderboard-related errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class RedisUnavailableError(LeaderboardError):
    """Raised when Redis is unreachable or not connected."""


class RedisTimeoutError(LeaderboardError):
    """Raised when a Redis operation exceeds the configured timeout."""


class UserNotFoundError(LeaderboardError):
    """Raised when a requested user does not exist on the leaderboard."""


class InvalidScoreError(LeaderboardError):
    """Raised when a score value is invalid (non-numeric, NaN, etc.)."""


class NegativeScoreError(LeaderboardError):
    """Raised when a score or increment would result in a negative value."""

class InvalidTenantMetadataError(LeaderboardError):
    """Raised when tenant ID or metadata is invalid."""
