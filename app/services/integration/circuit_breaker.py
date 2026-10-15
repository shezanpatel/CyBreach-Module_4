"""Simple async circuit breaker for Kafka / Redis side effects."""

from __future__ import annotations

import time
from enum import Enum
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(RuntimeError):
    pass


class CircuitBreaker:
    def __init__(
        self,
        *,
        failure_threshold: int = 5,
        recovery_seconds: float = 15.0,
        name: str = "default",
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self.name = name
        self.failures = 0
        self.state = CircuitState.CLOSED
        self.opened_at = 0.0

    def _maybe_half_open(self) -> None:
        if self.state == CircuitState.OPEN:
            if time.monotonic() - self.opened_at >= self.recovery_seconds:
                self.state = CircuitState.HALF_OPEN

    async def call(self, fn: Callable[[], Awaitable[T]]) -> T:
        self._maybe_half_open()
        if self.state == CircuitState.OPEN:
            raise CircuitOpenError(f"circuit {self.name} is open")
        try:
            result = await fn()
        except Exception:
            self.failures += 1
            if self.failures >= self.failure_threshold:
                self.state = CircuitState.OPEN
                self.opened_at = time.monotonic()
            raise
        self.failures = 0
        self.state = CircuitState.CLOSED
        return result
