"""Pydantic contracts for topics Pod Delta consumes."""

from typing import Any, Literal, Optional

from pydantic import Field

from app.events.base import EventEnvelope
from app.events.topics import ConsumeTopic


class WalletTransactionEvent(EventEnvelope):
    event_type: Literal["wallet.transaction"] = "wallet.transaction"
    transaction_id: str = Field(..., min_length=1)
    amount: float
    currency: str = Field(default="USD", min_length=1, max_length=8)
    direction: Literal["credit", "debit"]
    status: str = Field(default="completed")
    wallet_id: Optional[str] = None
    user_id: Optional[int] = None
    description: Optional[str] = None


class EngagementLifecycleEvent(EventEnvelope):
    event_type: Literal["engagement.lifecycle"] = "engagement.lifecycle"
    engagement_id: str = Field(..., min_length=1)
    stage: str = Field(..., min_length=1)
    user_id: Optional[int] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EngagementCompletedEvent(EventEnvelope):
    event_type: Literal["engagement.completed"] = "engagement.completed"
    engagement_id: str = Field(..., min_length=1)
    outcome: str = Field(default="completed")
    user_id: Optional[int] = None
    score_delta: Optional[float] = None
    duration_seconds: Optional[float] = None


class Mod3ScoreEvent(EventEnvelope):
    event_type: Literal["mod3.score"] = "mod3.score"
    score: float = Field(..., ge=0, le=100)
    previous_score: Optional[float] = Field(default=None, ge=0, le=100)
    trend: Optional[str] = None
    components: dict[str, Any] = Field(default_factory=dict)
    computed_at: Optional[str] = None


class AchievementAwardedEvent(EventEnvelope):
    event_type: Literal["achievement.awarded"] = "achievement.awarded"
    achievement_id: str = Field(..., min_length=1)
    achievement_name: str = Field(..., min_length=1)
    user_id: Optional[int] = None
    points: int = Field(default=0, ge=0)


class LeaderboardUpdatedEvent(EventEnvelope):
    event_type: Literal["leaderboard.updated"] = "leaderboard.updated"
    board_id: str = Field(default="global")
    rankings: list[dict[str, Any]] = Field(default_factory=list)
    generated_at: Optional[str] = None


class BenchmarkComputedEvent(EventEnvelope):
    event_type: Literal["benchmark.computed"] = "benchmark.computed"
    benchmark_id: str = Field(..., min_length=1)
    percentile: Optional[float] = Field(default=None, ge=0, le=100)
    peer_group: Optional[str] = None
    metrics: dict[str, Any] = Field(default_factory=dict)


TOPIC_EVENT_TYPE: dict[str, str] = {
    ConsumeTopic.WALLET_TRANSACTION.value: "wallet.transaction",
    ConsumeTopic.ENGAGEMENT_LIFECYCLE.value: "engagement.lifecycle",
    ConsumeTopic.ENGAGEMENT_COMPLETED.value: "engagement.completed",
    ConsumeTopic.MOD3_SCORE.value: "mod3.score",
    ConsumeTopic.ACHIEVEMENT_AWARDED.value: "achievement.awarded",
    ConsumeTopic.LEADERBOARD_UPDATED.value: "leaderboard.updated",
    ConsumeTopic.BENCHMARK_COMPUTED.value: "benchmark.computed",
}
