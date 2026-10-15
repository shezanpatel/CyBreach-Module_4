"""Pydantic event contracts for Pod Delta integration topics."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, TypeAlias
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


CONSUME_TOPICS: tuple[str, ...] = (
    "wallet.transaction",
    "engagement.lifecycle",
    "engagement.completed",
    "mod3.score",
    "achievement.awarded",
    "leaderboard.updated",
    "benchmark.computed",
)

PUBLISH_TOPICS: tuple[str, ...] = (
    "notification.sent",
    "analytics.report",
    "score.displayed",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EventEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    event_type: str = Field(..., min_length=1, max_length=128)
    event_id: str = Field(..., min_length=1, max_length=128)
    tenant_id: str = Field(..., min_length=1, max_length=128)
    timestamp: datetime
    data: dict[str, Any] = Field(default_factory=dict)

    @field_validator("timestamp")
    @classmethod
    def ensure_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class WalletTransactionData(BaseModel):
    transaction_id: str = Field(..., min_length=1)
    amount: float
    currency: str = Field(default="USD", min_length=1, max_length=8)
    direction: Literal["credit", "debit"]
    status: str = "completed"
    wallet_id: str | None = None
    user_id: int | None = None


class EngagementLifecycleData(BaseModel):
    engagement_id: str = Field(..., min_length=1)
    stage: str = Field(..., min_length=1)
    user_id: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EngagementCompletedData(BaseModel):
    engagement_id: str = Field(..., min_length=1)
    outcome: str = "completed"
    user_id: int | None = None
    score_delta: float | None = None
    duration_seconds: float | None = None


class Mod3ScoreData(BaseModel):
    score: float = Field(..., ge=0, le=100)
    previous_score: float | None = Field(default=None, ge=0, le=100)
    trend: str | None = None
    components: dict[str, Any] = Field(default_factory=dict)
    computed_at: str | None = None


class AchievementAwardedData(BaseModel):
    achievement_id: str = Field(..., min_length=1)
    achievement_name: str = Field(..., min_length=1)
    user_id: int | None = None
    points: int = Field(default=0, ge=0)


class LeaderboardUpdatedData(BaseModel):
    board_id: str = "global"
    rankings: list[dict[str, Any]] = Field(default_factory=list)
    generated_at: str | None = None


class BenchmarkComputedData(BaseModel):
    benchmark_id: str = Field(..., min_length=1)
    percentile: float | None = Field(default=None, ge=0, le=100)
    peer_group: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)


ConsumedData: TypeAlias = (
    WalletTransactionData
    | EngagementLifecycleData
    | EngagementCompletedData
    | Mod3ScoreData
    | AchievementAwardedData
    | LeaderboardUpdatedData
    | BenchmarkComputedData
)


class ValidatedEvent(BaseModel):
    envelope: EventEnvelope
    data: ConsumedData

    @property
    def event_type(self) -> str:
        return self.envelope.event_type

    @property
    def event_id(self) -> str:
        return self.envelope.event_id

    @property
    def tenant_id(self) -> str:
        return self.envelope.tenant_id

    @property
    def timestamp(self) -> datetime:
        return self.envelope.timestamp


DATA_MODELS: dict[str, type[BaseModel]] = {
    "wallet.transaction": WalletTransactionData,
    "engagement.lifecycle": EngagementLifecycleData,
    "engagement.completed": EngagementCompletedData,
    "mod3.score": Mod3ScoreData,
    "achievement.awarded": AchievementAwardedData,
    "leaderboard.updated": LeaderboardUpdatedData,
    "benchmark.computed": BenchmarkComputedData,
}


def validate_event(topic: str, payload: dict[str, Any]) -> ValidatedEvent:
    envelope = EventEnvelope.model_validate(payload)
    if topic not in CONSUME_TOPICS:
        raise ValueError(f"Unsupported topic {topic}")
    if envelope.event_type != topic:
        raise ValueError("event_type must match Kafka topic")
    data_model = DATA_MODELS[topic]
    data = data_model.model_validate(envelope.data)
    return ValidatedEvent(envelope=envelope, data=data)  # type: ignore[arg-type]


def published_envelope(
    *,
    event_type: Literal["notification.sent", "analytics.report", "score.displayed"],
    tenant_id: str,
    data: dict[str, Any],
    event_id: str | None = None,
    timestamp: datetime | None = None,
) -> dict[str, Any]:
    return EventEnvelope(
        event_type=event_type,
        event_id=event_id or str(uuid4()),
        tenant_id=tenant_id,
        timestamp=timestamp or utc_now(),
        data=data,
    ).model_dump(mode="json")

