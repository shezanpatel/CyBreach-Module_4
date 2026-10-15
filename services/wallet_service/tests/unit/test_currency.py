 
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.services.currency_service import (
    CurrencyRateNotFoundError,
    convert_currency,
    get_conversion_rate,
)


@patch("app.services.currency_service.get_latest_currency_rate")
def test_convert_currency(mock_get_latest_currency_rate):
    rate_record = MagicMock()
    rate_record.rate = Decimal("140.50000000")

    mock_get_latest_currency_rate.return_value = rate_record

    db = MagicMock()

    result = convert_currency(
        db=db,
        amount=Decimal("10.00"),
        base_currency="USD",
        target_currency="NPR",
    )

    assert result == Decimal("1405.00")

    mock_get_latest_currency_rate.assert_called_once_with(
        db=db,
        base_currency="USD",
        target_currency="NPR",
        effective_at=None,
    )


@patch("app.services.currency_service.get_latest_currency_rate")
def test_convert_currency_uses_effective_time(
    mock_get_latest_currency_rate,
):
    rate_record = MagicMock()
    rate_record.rate = Decimal("141.25000000")

    mock_get_latest_currency_rate.return_value = rate_record

    db = MagicMock()

    effective_at = datetime(
        2026,
        9,
        14,
        0,
        0,
        tzinfo=UTC,
    )

    result = convert_currency(
        db=db,
        amount=Decimal("2.00"),
        base_currency="USD",
        target_currency="NPR",
        effective_at=effective_at,
    )

    assert result == Decimal("282.50")

    mock_get_latest_currency_rate.assert_called_once_with(
        db=db,
        base_currency="USD",
        target_currency="NPR",
        effective_at=effective_at,
    )


def test_same_currency_conversion_does_not_require_rate():
    db = MagicMock()

    result = convert_currency(
        db=db,
        amount=Decimal("100.00"),
        base_currency="USD",
        target_currency="USD",
    )

    assert result == Decimal("100.00")


def test_same_currency_conversion_rounds_to_two_decimal_places():
    db = MagicMock()

    result = convert_currency(
        db=db,
        amount=Decimal("100.126"),
        base_currency="USD",
        target_currency="USD",
    )

    assert result == Decimal("100.13")


@patch("app.services.currency_service.get_latest_currency_rate")
def test_convert_currency_raises_when_rate_missing(
    mock_get_latest_currency_rate,
):
    mock_get_latest_currency_rate.return_value = None

    db = MagicMock()

    with pytest.raises(
        CurrencyRateNotFoundError,
        match="No currency rate configured for USD->NPR",
    ):
        convert_currency(
            db=db,
            amount=Decimal("100.00"),
            base_currency="USD",
            target_currency="NPR",
        )


@patch("app.services.currency_service.get_latest_currency_rate")
def test_get_conversion_rate(mock_get_latest_currency_rate):
    rate_record = MagicMock()
    rate_record.rate = Decimal("140.50000000")

    mock_get_latest_currency_rate.return_value = rate_record

    db = MagicMock()

    result = get_conversion_rate(
        db=db,
        base_currency="usd",
        target_currency="npr",
    )

    assert result == Decimal("140.50000000")

    mock_get_latest_currency_rate.assert_called_once_with(
        db=db,
        base_currency="USD",
        target_currency="NPR",
        effective_at=None,
    )


def test_same_currency_rate_is_one():
    db = MagicMock()

    result = get_conversion_rate(
        db=db,
        base_currency="USD",
        target_currency="USD",
    )

    assert result == Decimal("1")


@patch("app.services.currency_service.get_latest_currency_rate")
def test_negative_amount_is_rejected(
    mock_get_latest_currency_rate,
):
    db = MagicMock()

    with pytest.raises(
        ValueError,
        match="Amount cannot be negative",
    ):
        convert_currency(
            db=db,
            amount=Decimal("-10.00"),
            base_currency="USD",
            target_currency="NPR",
        )

    mock_get_latest_currency_rate.assert_not_called()
