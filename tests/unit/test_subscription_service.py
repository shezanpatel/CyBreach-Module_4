from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.services.subscription_service import SubscriptionService


def _active_subscription(
    *,
    user_id="test_user",
    tier="STARTER",
):
    subscription = MagicMock()

    subscription.id = uuid4()
    subscription.user_id = user_id
    subscription.tier = tier
    subscription.status = "ACTIVE"

    tier_values = {
        "FREE": Decimal("5"),
        "STARTER": Decimal("50"),
        "PROFESSIONAL": Decimal("200"),
        "ENTERPRISE": Decimal("0"),
    }

    subscription.credits_per_period = tier_values[tier]

    subscription.current_period_start = datetime.now(timezone.utc)
    subscription.current_period_end = (
        subscription.current_period_start + timedelta(days=30)
    )

    subscription.cancelled_at = None

    return subscription


def test_tier_credit_configuration():
    assert SubscriptionService.TIER_CREDITS["FREE"] == Decimal("5")
    assert SubscriptionService.TIER_CREDITS["STARTER"] == Decimal("50")
    assert (
        SubscriptionService.TIER_CREDITS["PROFESSIONAL"]
        == Decimal("200")
    )
    assert SubscriptionService.TIER_CREDITS["ENTERPRISE"] is None


@patch("app.services.subscription_service.create_credit")
def test_signup_paid_tier_allocates_wallet_credit(mock_create_credit):
    db = MagicMock()
    service = SubscriptionService(db)
    service.repository = MagicMock()

    service.repository.get_active_by_user_id.return_value = None

    subscription = _active_subscription(
        user_id="test_user",
        tier="STARTER",
    )

    service.repository.create.return_value = subscription

    result = service.signup(
        user_id="test_user",
        tier="starter",
    )

    assert result == subscription

    call_kwargs = service.repository.create.call_args.kwargs

    assert call_kwargs["tier"] == "STARTER"
    assert call_kwargs["credits_per_period"] == Decimal("50")

    mock_create_credit.assert_called_once()

    credit_kwargs = mock_create_credit.call_args.kwargs

    assert credit_kwargs["db"] is db
    assert credit_kwargs["user_id"] == "test_user"
    assert credit_kwargs["amount"] == Decimal("50")
    assert credit_kwargs["currency"] == "USD"

    assert str(subscription.id) in credit_kwargs["reference_id"]
    assert str(subscription.id) in credit_kwargs["idempotency_key"]

    db.refresh.assert_called_once_with(subscription)


@patch("app.services.subscription_service.create_credit")
def test_signup_free_does_not_use_paid_allocation(mock_create_credit):
    db = MagicMock()
    service = SubscriptionService(db)
    service.repository = MagicMock()

    service.repository.get_active_by_user_id.return_value = None

    subscription = _active_subscription(
        user_id="free_user",
        tier="FREE",
    )

    service.repository.create.return_value = subscription

    service.signup(
        user_id="free_user",
        tier="FREE",
    )

    call_kwargs = service.repository.create.call_args.kwargs

    assert call_kwargs["credits_per_period"] == Decimal("5")

    mock_create_credit.assert_not_called()
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(subscription)


@patch("app.services.subscription_service.create_credit")
def test_signup_enterprise_does_not_create_finite_credit(
    mock_create_credit,
):
    db = MagicMock()
    service = SubscriptionService(db)
    service.repository = MagicMock()

    service.repository.get_active_by_user_id.return_value = None

    subscription = _active_subscription(
        user_id="enterprise_user",
        tier="ENTERPRISE",
    )

    service.repository.create.return_value = subscription

    service.signup(
        user_id="enterprise_user",
        tier="ENTERPRISE",
    )

    call_kwargs = service.repository.create.call_args.kwargs

    assert call_kwargs["credits_per_period"] == Decimal("0")

    mock_create_credit.assert_not_called()
    db.commit.assert_called_once()


def test_signup_rejects_duplicate_active_subscription():
    db = MagicMock()
    service = SubscriptionService(db)
    service.repository = MagicMock()

    service.repository.get_active_by_user_id.return_value = (
        _active_subscription()
    )

    with pytest.raises(
        ValueError,
        match="already has an active subscription",
    ):
        service.signup(
            user_id="test_user",
            tier="STARTER",
        )

    service.repository.create.assert_not_called()


def test_signup_rejects_invalid_tier():
    db = MagicMock()
    service = SubscriptionService(db)
    service.repository = MagicMock()

    with pytest.raises(
        ValueError,
        match="Invalid subscription tier",
    ):
        service.signup(
            user_id="test_user",
            tier="INVALID",
        )


@patch("app.services.subscription_service.create_credit")
def test_renew_adds_new_monthly_allocation(mock_create_credit):
    db = MagicMock()
    service = SubscriptionService(db)
    service.repository = MagicMock()

    subscription = _active_subscription(
        tier="STARTER",
    )

    old_period_end = subscription.current_period_end

    service.repository.get_active_by_user_id.return_value = subscription
    service.repository.update.return_value = subscription

    result = service.renew(
        user_id="test_user",
    )

    assert result == subscription

    assert subscription.current_period_start >= old_period_end

    assert subscription.current_period_end == (
        subscription.current_period_start
        + timedelta(days=service.PERIOD_DAYS)
    )

    assert subscription.credits_per_period == Decimal("50")

    mock_create_credit.assert_called_once()

    credit_kwargs = mock_create_credit.call_args.kwargs

    assert credit_kwargs["amount"] == Decimal("50")
    assert credit_kwargs["user_id"] == "test_user"
    assert str(subscription.id) in credit_kwargs["idempotency_key"]


def test_renew_rejects_missing_active_subscription():
    db = MagicMock()
    service = SubscriptionService(db)
    service.repository = MagicMock()

    service.repository.get_active_by_user_id.return_value = None

    with pytest.raises(
        ValueError,
        match="No active subscription found",
    ):
        service.renew(
            user_id="test_user",
        )


def test_cancel_marks_subscription_cancelled():
    db = MagicMock()
    service = SubscriptionService(db)
    service.repository = MagicMock()

    subscription = _active_subscription()

    service.repository.get_active_by_user_id.return_value = subscription
    service.repository.update.return_value = subscription

    result = service.cancel(
        user_id="test_user",
    )

    assert result == subscription
    assert subscription.status == "CANCELLED"
    assert subscription.cancelled_at is not None

    service.repository.update.assert_called_once_with(subscription)
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(subscription)


@patch("app.services.subscription_service.create_credit")
def test_cancel_does_not_modify_wallet_credit(mock_create_credit):
    db = MagicMock()
    service = SubscriptionService(db)
    service.repository = MagicMock()

    subscription = _active_subscription()

    service.repository.get_active_by_user_id.return_value = subscription
    service.repository.update.return_value = subscription

    service.cancel(
        user_id="test_user",
    )

    mock_create_credit.assert_not_called()


def test_change_tier_updates_future_allocation():
    db = MagicMock()
    service = SubscriptionService(db)
    service.repository = MagicMock()

    subscription = _active_subscription(
        tier="STARTER",
    )

    service.repository.get_active_by_user_id.return_value = subscription
    service.repository.update.return_value = subscription

    result = service.change_tier(
        user_id="test_user",
        tier="professional",
    )

    assert result == subscription
    assert subscription.tier == "PROFESSIONAL"
    assert subscription.credits_per_period == Decimal("200")

    service.repository.update.assert_called_once_with(subscription)
    db.commit.assert_called_once()


@patch("app.services.subscription_service.create_credit")
def test_change_tier_does_not_allocate_immediate_proration(
    mock_create_credit,
):
    db = MagicMock()
    service = SubscriptionService(db)
    service.repository = MagicMock()

    subscription = _active_subscription(
        tier="STARTER",
    )

    service.repository.get_active_by_user_id.return_value = subscription
    service.repository.update.return_value = subscription

    service.change_tier(
        user_id="test_user",
        tier="PROFESSIONAL",
    )

    mock_create_credit.assert_not_called()


def test_change_tier_to_enterprise_uses_unlimited_sentinel():
    db = MagicMock()
    service = SubscriptionService(db)
    service.repository = MagicMock()

    subscription = _active_subscription(
        tier="PROFESSIONAL",
    )

    service.repository.get_active_by_user_id.return_value = subscription
    service.repository.update.return_value = subscription

    service.change_tier(
        user_id="test_user",
        tier="ENTERPRISE",
    )

    assert subscription.tier == "ENTERPRISE"
    assert subscription.credits_per_period == Decimal("0")


def test_change_tier_rejects_invalid_tier():
    db = MagicMock()
    service = SubscriptionService(db)
    service.repository = MagicMock()

    with pytest.raises(
        ValueError,
        match="Invalid subscription tier",
    ):
        service.change_tier(
            user_id="test_user",
            tier="INVALID",
        )


def test_get_subscription_returns_latest_subscription():
    db = MagicMock()
    service = SubscriptionService(db)
    service.repository = MagicMock()

    subscription = _active_subscription()

    service.repository.get_by_user_id.return_value = subscription

    result = service.get_subscription(
        user_id="test_user",
    )

    assert result == subscription

    service.repository.get_by_user_id.assert_called_once_with(
        "test_user"
    )
