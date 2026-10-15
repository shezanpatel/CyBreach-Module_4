 
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.repositories.currency_repository import get_latest_currency_rate


DISPLAY_QUANTIZE = Decimal("0.01")


class CurrencyRateNotFoundError(Exception):
    """Raised when no configured currency conversion rate is available."""


def convert_currency(
    db: Session,
    amount: Decimal,
    base_currency: str,
    target_currency: str,
    effective_at: datetime | None = None,
) -> Decimal:
    """
    Convert an amount using the configured currency rate.

    This is a display-layer conversion only.

    Wallet balances and ledger amounts remain unchanged.
    """

    if amount < Decimal("0"):
        raise ValueError("Amount cannot be negative")

    base_currency = base_currency.upper()
    target_currency = target_currency.upper()

    if base_currency == target_currency:
        return amount.quantize(DISPLAY_QUANTIZE, rounding=ROUND_HALF_UP)

    currency_rate = get_latest_currency_rate(
        db=db,
        base_currency=base_currency,
        target_currency=target_currency,
        effective_at=effective_at,
    )

    if currency_rate is None:
        raise CurrencyRateNotFoundError(
            f"No currency rate configured for "
            f"{base_currency}->{target_currency}"
        )

    converted_amount = amount * currency_rate.rate

    return converted_amount.quantize(
        DISPLAY_QUANTIZE,
        rounding=ROUND_HALF_UP,
    )


def get_conversion_rate(
    db: Session,
    base_currency: str,
    target_currency: str,
    effective_at: datetime | None = None,
) -> Decimal:
    """
    Return the latest configured conversion rate effective at the
    requested time.
    """

    base_currency = base_currency.upper()
    target_currency = target_currency.upper()

    if base_currency == target_currency:
        return Decimal("1")

    currency_rate = get_latest_currency_rate(
        db=db,
        base_currency=base_currency,
        target_currency=target_currency,
        effective_at=effective_at,
    )

    if currency_rate is None:
        raise CurrencyRateNotFoundError(
            f"No currency rate configured for "
            f"{base_currency}->{target_currency}"
        )

    return currency_rate.rate
