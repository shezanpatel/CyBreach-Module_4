from datetime import datetime, timezone

import pytest

from app.events.registry import EventValidationError, parse_event
from app.events.topics import CONSUME_TOPICS, PUBLISH_TOPICS, ConsumeTopic, PublishTopic
from app.events.consumed import Mod3ScoreEvent, WalletTransactionEvent
from app.events.published import NotificationSentEvent, ScoreDisplayedEvent


def _base(**overrides):
    payload = {
        "event_id": "evt-1",
        "event_version": "1.0",
        "tenant_id": "tenant-a",
        "correlation_id": "corr-1",
        "occurred_at": datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat(),
        "source": "pod-alpha",
        "transaction_id": "txn-1",
        "amount": 25.5,
        "direction": "credit",
        "currency": "USD",
    }
    payload.update(overrides)
    return payload


def test_consume_and_publish_topic_lists_are_exact():
    assert CONSUME_TOPICS == (
        "wallet.transaction",
        "engagement.lifecycle",
        "engagement.completed",
        "mod3.score",
        "achievement.awarded",
        "leaderboard.updated",
        "benchmark.computed",
    )
    assert PUBLISH_TOPICS == (
        "notification.sent",
        "analytics.report",
        "score.displayed",
    )
    assert ConsumeTopic.MOD3_SCORE.value == "mod3.score"
    assert PublishTopic.NOTIFICATION_SENT.value == "notification.sent"


def test_wallet_event_validates():
    event = parse_event("wallet.transaction", _base())
    assert isinstance(event, WalletTransactionEvent)
    assert event.tenant_id == "tenant-a"
    assert event.amount == 25.5


def test_wallet_event_rejects_bad_direction():
    with pytest.raises(EventValidationError):
        parse_event("wallet.transaction", _base(direction="sideways"))


def test_mod3_score_bounds():
    payload = {
        "event_id": "s1",
        "tenant_id": "t1",
        "correlation_id": "c1",
        "occurred_at": "2026-01-01T00:00:00Z",
        "score": 101,
    }
    with pytest.raises(EventValidationError):
        parse_event("mod3.score", payload)

    payload["score"] = 88.2
    event = parse_event("mod3.score", payload)
    assert isinstance(event, Mod3ScoreEvent)
    assert event.score == 88.2


def test_unknown_topic_rejected():
    with pytest.raises(EventValidationError):
        parse_event("not.a.topic", {"event_id": "x"})


def test_published_events_forbid_unknown_fields():
    with pytest.raises(Exception):
        NotificationSentEvent(
            tenant_id="t1",
            channel="email",
            status="sent",
            triggering_event_type="wallet.transaction",
            triggering_event_id="e1",
            unexpected="nope",
        )


def test_score_displayed_event():
    event = ScoreDisplayedEvent(
        tenant_id="t1",
        score=42.0,
        cache_key="score:t1",
        push_delivered=True,
    )
    dumped = event.model_dump()
    assert dumped["event_type"] == "score.displayed"
    assert dumped["event_version"] == "1.0"
