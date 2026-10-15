from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.currency_rate import CurrencyRate


def create_currency_rate(
    db: Session,
    base_currency: str,
    target_currency: str,
    rate: Decimal,
    effective_at: datetime,
) -> CurrencyRate:
    """
    Store a configured currency conversion rate.
    """

    currency_rate = CurrencyRate(
        base_currency=base_currency.upper(),
        target_currency=target_currency.upper(),
        rate=rate,
        effective_at=effective_at,
    )

    db.add(currency_rate)
    db.flush()

    return currency_rate


def get_latest_currency_rate(
    db: Session,
    base_currency: str,
    target_currency: str,
    effective_at: datetime | None = None,
) -> CurrencyRate | None:
    """
    Return the latest rate that is effective at the requested time.

    If effective_at is omitted, the current time is used.
    """

    if effective_at is None:
        effective_at = datetime.now().astimezone()

    statement = (
        select(CurrencyRate)
        .where(
            CurrencyRate.base_currency == base_currency.upper(),
            CurrencyRate.target_currency == target_currency.upper(),
            CurrencyRate.effective_at <= effective_at,
        )
        .order_by(CurrencyRate.effective_at.desc())
        .limit(1)
    )

    return db.execute(statement).scalar_one_or_none()


def list_currency_rates(
    db: Session,
    base_currency: str | None = None,
    target_currency: str | None = None,
) -> list[CurrencyRate]:
    """
    Return configured currency rates ordered from newest to oldest.
    """

    statement = select(CurrencyRate)

    if base_currency is not None:
        statement = statement.where(
            CurrencyRate.base_currency == base_currency.upper()
        )

    if target_currency is not None:
        statement = statement.where(
            CurrencyRate.target_currency == target_currency.upper()
        )

    statement = statement.order_by(
        CurrencyRate.effective_at.desc()
    )

    return list(db.execute(statement).scalars().all())