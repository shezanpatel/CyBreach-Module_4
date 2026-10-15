from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

from app.tasks.currency_rate_refresh import (
    refresh_configured_currency_rates,
)


@patch("app.tasks.currency_rate_refresh.SessionLocal")
def test_refresh_returns_no_configured_rates(mock_session_local):
    db = MagicMock()
    mock_session_local.return_value = db

    db.query.return_value.distinct.return_value.all.return_value = []

    result = refresh_configured_currency_rates()

    assert result["status"] == "NO_CONFIGURED_RATES"
    assert result["checked_pairs"] == 0
    assert result["refreshed_rates"] == 0

    db.close.assert_called_once()


@patch(
    "app.tasks.currency_rate_refresh.get_latest_currency_rate"
)
@patch("app.tasks.currency_rate_refresh.SessionLocal")
def test_refresh_checks_configured_currency_pair(
    mock_session_local,
    mock_get_latest_currency_rate,
):
    db = MagicMock()
    mock_session_local.return_value = db

    db.query.return_value.distinct.return_value.all.return_value = [
        ("USD", "NPR")
    ]

    rate = MagicMock()
    rate.rate = Decimal("140.50000000")
    rate.effective_at = datetime(
        2026,
        9,
        26,
        tzinfo=UTC,
    )

    mock_get_latest_currency_rate.return_value = rate

    result = refresh_configured_currency_rates()

    assert result["status"] == "CHECKED_CONFIGURED_RATES"
    assert result["checked_pairs"] == 1
    assert result["refreshed_rates"] == 0

    mock_get_latest_currency_rate.assert_called_once()

    call_kwargs = (
        mock_get_latest_currency_rate.call_args.kwargs
    )

    assert call_kwargs["db"] is db
    assert call_kwargs["base_currency"] == "USD"
    assert call_kwargs["target_currency"] == "NPR"
    assert call_kwargs["effective_at"] is not None

    db.close.assert_called_once()


@patch(
    "app.tasks.currency_rate_refresh.get_latest_currency_rate"
)
@patch("app.tasks.currency_rate_refresh.SessionLocal")
def test_refresh_handles_missing_effective_rate(
    mock_session_local,
    mock_get_latest_currency_rate,
):
    db = MagicMock()
    mock_session_local.return_value = db

    db.query.return_value.distinct.return_value.all.return_value = [
        ("USD", "NPR")
    ]

    mock_get_latest_currency_rate.return_value = None

    result = refresh_configured_currency_rates()

    assert result["status"] == "CHECKED_CONFIGURED_RATES"
    assert result["checked_pairs"] == 1
    assert result["refreshed_rates"] == 0

    db.close.assert_called_once()


@patch("app.tasks.currency_rate_refresh.SessionLocal")
def test_refresh_failure_is_isolated(mock_session_local):
    db = MagicMock()
    mock_session_local.return_value = db

    db.query.side_effect = RuntimeError(
        "database unavailable"
    )

    result = refresh_configured_currency_rates()

    assert result["status"] == "FAILED"
    assert result["checked_pairs"] == 0
    assert result["refreshed_rates"] == 0

    db.rollback.assert_called_once()
    db.close.assert_called_once()
