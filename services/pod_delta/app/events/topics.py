"""Canonical Kafka topic names owned or consumed by Pod Delta."""

from enum import Enum


class ConsumeTopic(str, Enum):
    WALLET_TRANSACTION = "wallet.transaction"
    ENGAGEMENT_LIFECYCLE = "engagement.lifecycle"
    ENGAGEMENT_COMPLETED = "engagement.completed"
    MOD3_SCORE = "mod3.score"
    ACHIEVEMENT_AWARDED = "achievement.awarded"
    LEADERBOARD_UPDATED = "leaderboard.updated"
    BENCHMARK_COMPUTED = "benchmark.computed"


class PublishTopic(str, Enum):
    NOTIFICATION_SENT = "notification.sent"
    ANALYTICS_REPORT = "analytics.report"
    SCORE_DISPLAYED = "score.displayed"


CONSUME_TOPICS: tuple[str, ...] = tuple(topic.value for topic in ConsumeTopic)
PUBLISH_TOPICS: tuple[str, ...] = tuple(topic.value for topic in PublishTopic)

CONSUMER_GROUP_ID = "pod-delta-integration"


def dead_letter_topic(topic: str) -> str:
    return f"{topic}.dlt"
