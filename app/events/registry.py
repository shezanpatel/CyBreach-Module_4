"""Topic → model registry and JSON parsing."""

from typing import Any, Type

from pydantic import ValidationError

from app.events.consumed import (
    AchievementAwardedEvent,
    BenchmarkComputedEvent,
    EngagementCompletedEvent,
    EngagementLifecycleEvent,
    LeaderboardUpdatedEvent,
    Mod3ScoreEvent,
    WalletTransactionEvent,
)
from app.events.topics import ConsumeTopic, PublishTopic

EVENT_MODEL_BY_TOPIC: dict[str, Type[Any]] = {
    ConsumeTopic.WALLET_TRANSACTION.value: WalletTransactionEvent,
    ConsumeTopic.ENGAGEMENT_LIFECYCLE.value: EngagementLifecycleEvent,
    ConsumeTopic.ENGAGEMENT_COMPLETED.value: EngagementCompletedEvent,
    ConsumeTopic.MOD3_SCORE.value: Mod3ScoreEvent,
    ConsumeTopic.ACHIEVEMENT_AWARDED.value: AchievementAwardedEvent,
    ConsumeTopic.LEADERBOARD_UPDATED.value: LeaderboardUpdatedEvent,
    ConsumeTopic.BENCHMARK_COMPUTED.value: BenchmarkComputedEvent,
}

PUBLISH_EVENT_TYPES = {
    PublishTopic.NOTIFICATION_SENT.value,
    PublishTopic.ANALYTICS_REPORT.value,
    PublishTopic.SCORE_DISPLAYED.value,
}


class EventValidationError(ValueError):
    def __init__(self, topic: str, errors: list[Any]) -> None:
        self.topic = topic
        self.errors = errors
        super().__init__(f"Invalid payload for topic {topic}: {errors}")


def parse_event(topic: str, payload: dict[str, Any]) -> Any:
    model = EVENT_MODEL_BY_TOPIC.get(topic)
    if model is None:
        raise EventValidationError(topic, [{"msg": "unknown consume topic"}])
    data = dict(payload)
    data.setdefault("event_type", topic)
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        raise EventValidationError(topic, exc.errors()) from exc
