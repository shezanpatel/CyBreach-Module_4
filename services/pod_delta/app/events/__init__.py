"""Kafka event contracts for Pod Delta integration."""

from app.events.consumed import (
    AchievementAwardedEvent,
    BenchmarkComputedEvent,
    EngagementCompletedEvent,
    EngagementLifecycleEvent,
    LeaderboardUpdatedEvent,
    Mod3ScoreEvent,
    WalletTransactionEvent,
)
from app.events.published import (
    AnalyticsReportEvent,
    NotificationSentEvent,
    ScoreDisplayedEvent,
)
from app.events.registry import EVENT_MODEL_BY_TOPIC, parse_event
from app.events.topics import ConsumeTopic, PublishTopic

__all__ = [
    "AchievementAwardedEvent",
    "AnalyticsReportEvent",
    "BenchmarkComputedEvent",
    "ConsumeTopic",
    "EngagementCompletedEvent",
    "EngagementLifecycleEvent",
    "EVENT_MODEL_BY_TOPIC",
    "LeaderboardUpdatedEvent",
    "Mod3ScoreEvent",
    "NotificationSentEvent",
    "parse_event",
    "PublishTopic",
    "ScoreDisplayedEvent",
    "WalletTransactionEvent",
]
