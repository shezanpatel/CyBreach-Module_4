import logging
from datetime import UTC, datetime
from app.core.database import SessionLocal
from app.repositories.currency_repository import get_latest_currency_rate


logger = logging.getLogger(__name__)



def refresh_configured_currency_rates():
    """
    Perform the scheduled daily currency-rate refresh.

    Currency conversion is display-only. This task never modifies
    wallet balances or wallet ledger entries.

    The current service does not have an external FX provider
    configured. Until one is configured, the task safely verifies
    the configured rate table and leaves existing rates unchanged.

    This gives the scheduler a stable daily refresh boundary without
    inventing an external provider or silently fabricating FX rates.
    """

    db = SessionLocal()

    try:
        now = datetime.now(UTC)

        # Query through the ORM model so the task remains consistent
        # with the existing repository architecture.
        from app.models.currency_rate import CurrencyRate

        currency_pairs = (
            db.query(
                CurrencyRate.base_currency,
                CurrencyRate.target_currency,
            )
            .distinct()
            .all()
        )

        if not currency_pairs:
            logger.info(
                "Daily currency-rate refresh completed: "
                "no configured currency pairs"
            )
            return {
                "status": "NO_CONFIGURED_RATES",
                "checked_pairs": 0,
                "refreshed_rates": 0,
                "effective_at": now,
            }

        checked_pairs = 0

        for base_currency, target_currency in currency_pairs:
            checked_pairs += 1

            latest_rate = get_latest_currency_rate(
                db=db,
                base_currency=base_currency,
                target_currency=target_currency,
                effective_at=now,
            )

            if latest_rate is None:
                logger.warning(
                    "No effective currency rate found for %s->%s",
                    base_currency,
                    target_currency,
                )
                continue

            logger.info(
                "Configured currency rate available: "
                "%s->%s rate=%s effective_at=%s",
                base_currency,
                target_currency,
                latest_rate.rate,
                latest_rate.effective_at,
            )

        return {
            "status": "CHECKED_CONFIGURED_RATES",
            "checked_pairs": checked_pairs,
            "refreshed_rates": 0,
            "effective_at": now,
        }

    except Exception:
        db.rollback()

        logger.exception(
            "Daily currency-rate refresh failed"
        )

        return {
            "status": "FAILED",
            "checked_pairs": 0,
            "refreshed_rates": 0,
        }

    finally:
        db.close()
