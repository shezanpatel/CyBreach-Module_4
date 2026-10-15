"""Pydantic contracts for topics Pod Delta publishes."""

from typing import Any, Literal, Optional

from pydantic import Field

from app.events.base import StrictPublishedEvent


class NotificationSentEvent(StrictPublishedEvent):
    event_type: Literal["notification.sent"] = "notification.sent"
    notification_id: Optional[int] = None
    channel: str
    status: str
    triggering_event_type: str
    triggering_event_id: str
    rate_limited: bool = False


class AnalyticsReportEvent(StrictPublishedEvent):
    event_type: Literal["analytics.report"] = "analytics.report"
    report_month: str
    report_kind: Literal["scheduled", "on_demand"] = "scheduled"
    record_id: Optional[int] = None
    summary: dict[str, Any] = Field(default_factory=dict)


class ScoreDisplayedEvent(StrictPublishedEvent):
    event_type: Literal["score.displayed"] = "score.displayed"
    score: float = Field(..., ge=0, le=100)
    cache_key: str
    push_delivered: bool = False
