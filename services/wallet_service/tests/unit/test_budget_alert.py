from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

from app.services.budget_alert_service import (
    check_budget_alert,
    configure_budget_alert,
    get_configured_budget_alert,
    update_configured_budget_alert,
)


@patch("app.services.budget_alert_service.create_budget_alert")
@patch("app.services.budget_alert_service.get_budget_alert")
def test_configure_budget_alert_creates_alert(
    mock_get_budget_alert,
    mock_create_budget_alert,
):
    db = MagicMock()
    alert = MagicMock()

    mock_get_budget_alert.return_value = None
    mock_create_budget_alert.return_value = alert

    result = configure_budget_alert(
        db=db,
        user_id="budget-user-001",
        currency="usd",
        threshold=Decimal("100.00"),
        is_enabled=True,
    )

    assert result is alert

    mock_create_budget_alert.assert_called_once_with(
        db=db,
        user_id="budget-user-001",
        currency="USD",
        threshold=Decimal("100.00"),
        is_enabled=True,
    )
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(alert)


@patch("app.services.budget_alert_service.update_budget_alert")
@patch("app.services.budget_alert_service.get_budget_alert")
def test_configure_budget_alert_updates_existing_alert(
    mock_get_budget_alert,
    mock_update_budget_alert,
):
    db = MagicMock()
    alert = MagicMock()

    mock_get_budget_alert.return_value = alert
    mock_update_budget_alert.return_value = alert

    result = configure_budget_alert(
        db=db,
        user_id="budget-user-002",
        currency="npr",
        threshold=Decimal("500.00"),
        is_enabled=False,
    )

    assert result is alert

    mock_update_budget_alert.assert_called_once_with(
        db=db,
        alert=alert,
        threshold=Decimal("500.00"),
        is_enabled=False,
    )
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(alert)


@patch("app.services.budget_alert_service.get_budget_alert")
def test_get_configured_budget_alert_normalizes_currency(
    mock_get_budget_alert,
):
    db = MagicMock()
    alert = MagicMock()
    mock_get_budget_alert.return_value = alert

    result = get_configured_budget_alert(
        db=db,
        user_id="budget-user-003",
        currency="usd",
    )

    assert result is alert

    mock_get_budget_alert.assert_called_once_with(
        db=db,
        user_id="budget-user-003",
        currency="USD",
    )


@patch("app.services.budget_alert_service.update_budget_alert")
@patch("app.services.budget_alert_service.get_budget_alert")
def test_update_configured_budget_alert(
    mock_get_budget_alert,
    mock_update_budget_alert,
):
    db = MagicMock()
    alert = MagicMock()

    mock_get_budget_alert.return_value = alert
    mock_update_budget_alert.return_value = alert

    result = update_configured_budget_alert(
        db=db,
        user_id="budget-user-004",
        currency="usd",
        threshold=Decimal("250.00"),
        is_enabled=True,
    )

    assert result is alert

    mock_update_budget_alert.assert_called_once_with(
        db=db,
        alert=alert,
        threshold=Decimal("250.00"),
        is_enabled=True,
    )
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(alert)


@patch("app.services.budget_alert_service.get_wallet_balance")
@patch("app.services.budget_alert_service.get_budget_alert")
def test_check_budget_alert_above_threshold(
    mock_get_budget_alert,
    mock_get_wallet_balance,
):
    db = MagicMock()

    alert = MagicMock()
    alert.is_enabled = True
    alert.threshold = Decimal("100.00")
    alert.last_triggered_at = None

    wallet = MagicMock()
    wallet.available_balance = Decimal("250.00")

    mock_get_budget_alert.return_value = alert
    mock_get_wallet_balance.return_value = wallet

    result = check_budget_alert(
        db=db,
        user_id="budget-user-005",
        currency="usd",
    )

    assert result["balance"] == Decimal("250.00")
    assert result["threshold"] == Decimal("100.00")
    assert result["is_below_threshold"] is False
    assert result["notification_sent"] is False


@patch("app.services.budget_alert_service.mark_budget_alert_triggered")
@patch("app.services.budget_alert_service._publish_budget_alert_event")
@patch("app.services.budget_alert_service.get_wallet_balance")
@patch("app.services.budget_alert_service.get_budget_alert")
def test_check_budget_alert_sends_notification_when_below_threshold(
    mock_get_budget_alert,
    mock_get_wallet_balance,
    mock_publish_event,
    mock_mark_triggered,
):
    db = MagicMock()

    alert = MagicMock()
    alert.is_enabled = True
    alert.threshold = Decimal("100.00")
    alert.last_triggered_at = None

    wallet = MagicMock()
    wallet.available_balance = Decimal("50.00")

    mock_get_budget_alert.return_value = alert
    mock_get_wallet_balance.return_value = wallet
    mock_publish_event.return_value = True

    result = check_budget_alert(
        db=db,
        user_id="budget-user-006",
        currency="usd",
    )

    assert result["balance"] == Decimal("50.00")
    assert result["threshold"] == Decimal("100.00")
    assert result["is_below_threshold"] is True
    assert result["notification_sent"] is True

    mock_publish_event.assert_called_once_with(
        user_id="budget-user-006",
        currency="USD",
        balance=Decimal("50.00"),
        threshold=Decimal("100.00"),
    )

    mock_mark_triggered.assert_called_once_with(
        db=db,
        alert=alert,
    )

    db.commit.assert_called_once()


@patch("app.services.budget_alert_service._publish_budget_alert_event")
@patch("app.services.budget_alert_service.get_wallet_balance")
@patch("app.services.budget_alert_service.get_budget_alert")
def test_check_budget_alert_does_not_repeat_notification(
    mock_get_budget_alert,
    mock_get_wallet_balance,
    mock_publish_event,
):
    db = MagicMock()

    alert = MagicMock()
    alert.is_enabled = True
    alert.threshold = Decimal("100.00")
    alert.last_triggered_at = datetime.now(timezone.utc)

    wallet = MagicMock()
    wallet.available_balance = Decimal("50.00")

    mock_get_budget_alert.return_value = alert
    mock_get_wallet_balance.return_value = wallet

    result = check_budget_alert(
        db=db,
        user_id="budget-user-007",
        currency="USD",
    )

    assert result["is_below_threshold"] is True
    assert result["notification_sent"] is False

    mock_publish_event.assert_not_called()


@patch("app.services.budget_alert_service._publish_budget_alert_event")
@patch("app.services.budget_alert_service.get_wallet_balance")
@patch("app.services.budget_alert_service.get_budget_alert")
def test_check_budget_alert_does_not_notify_disabled_alert(
    mock_get_budget_alert,
    mock_get_wallet_balance,
    mock_publish_event,
):
    db = MagicMock()

    alert = MagicMock()
    alert.is_enabled = False
    alert.threshold = Decimal("100.00")
    alert.last_triggered_at = None

    wallet = MagicMock()
    wallet.available_balance = Decimal("50.00")

    mock_get_budget_alert.return_value = alert
    mock_get_wallet_balance.return_value = wallet

    result = check_budget_alert(
        db=db,
        user_id="budget-user-008",
        currency="USD",
    )

    assert result["is_below_threshold"] is True
    assert result["notification_sent"] is False

    mock_publish_event.assert_not_called()
