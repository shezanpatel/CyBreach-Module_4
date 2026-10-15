import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.database import SessionLocal
from app.repositories.wallet_repository import (
    get_wallet_balance,
    pause_wallet,
)
from app.models.wallet_balance import WalletBalance
from app.tasks.reconciliation import reconcile_wallet
from app.tasks.currency_rate_refresh import (
    refresh_configured_currency_rates,
)


logger = logging.getLogger(__name__)

RECONCILIATION_INTERVAL_HOURS = 6
CURRENCY_RATE_REFRESH_INTERVAL_HOURS = 24

# One scheduler instance for the entire application process.
scheduler = AsyncIOScheduler()


def _build_mismatch_alert(report: dict) -> dict:
    """
    Build the structured operational alert for a financial-integrity
    reconciliation mismatch.
    """

    return {
        "alert_type": "FINANCIAL_INTEGRITY_MISMATCH",
        "severity": "CRITICAL",
        "user_id": report["user_id"],
        "currency": report["currency"],
        "status": report["status"],
        "expected_balance": str(
            report["expected_balance"]
        ),
        "actual_balance": str(
            report["actual_balance"]
        ),
        "difference": str(
            report["difference"]
        ),
    }


def reconcile_and_handle_wallet(
    db,
    user_id: str,
    currency: str,
):
    """
    Reconcile one wallet and apply Task 4 safety behavior.

    The caller owns the transaction boundary.

    On mismatch:

        reconcile -> alert -> pause

    The wallet is never automatically resumed.
    """

    wallet = get_wallet_balance(
        db=db,
        user_id=user_id,
        currency=currency,
    )

    if wallet is None:
        return {
            "user_id": user_id,
            "currency": currency,
            "status": "NOT_FOUND",
            "expected_balance": 0,
            "actual_balance": 0,
            "difference": 0,
            "wallet_paused": False,
        }

    report = reconcile_wallet(
        db=db,
        user_id=user_id,
        currency=currency,
    )

    report["wallet_paused"] = False

    if report["status"] == "MISMATCH":

        alert = _build_mismatch_alert(report)

        logger.critical(
            "FINANCIAL INTEGRITY ALERT: %s",
            alert,
        )

        reason = (
            "Financial-integrity reconciliation mismatch: "
            f"expected={report['expected_balance']} "
            f"actual={report['actual_balance']} "
            f"difference={report['difference']}"
        )

        paused_wallet = pause_wallet(
            db=db,
            user_id=user_id,
            currency=currency,
            reason=reason,
        )

        if paused_wallet is None:
            raise RuntimeError(
                "Wallet disappeared while attempting to pause it"
            )

        report["wallet_paused"] = True
        report["pause_reason"] = (
            paused_wallet.pause_reason
        )

        report["paused_at"] = (
            paused_wallet.paused_at.isoformat()
            if paused_wallet.paused_at is not None
            else None
        )

    else:
        logger.info(
            "Wallet reconciliation: "
            "user_id=%s currency=%s status=%s "
            "expected=%s actual=%s difference=%s",
            report["user_id"],
            report["currency"],
            report["status"],
            report["expected_balance"],
            report["actual_balance"],
            report["difference"],
        )

    return report


def run_reconciliation_job():
    """
    Run reconciliation for every existing wallet.

    Each wallet gets its own transaction boundary.

    A failure for one wallet is rolled back and does not prevent
    the remaining wallets from being reconciled.
    """

    db = SessionLocal()

    try:
        wallet_keys = [
            (
                wallet.user_id,
                wallet.currency,
            )
            for wallet in db.query(WalletBalance).all()
        ]

        if not wallet_keys:
            logger.info(
                "Reconciliation job completed: no wallets found"
            )
            return []

        reports = []

        for user_id, currency in wallet_keys:

            try:
                db.rollback()

                report = reconcile_and_handle_wallet(
                    db=db,
                    user_id=user_id,
                    currency=currency,
                )

                db.commit()

                reports.append(report)

            except Exception:

                db.rollback()

                logger.exception(
                    "Failed to reconcile wallet "
                    "user_id=%s currency=%s; "
                    "transaction rolled back",
                    user_id,
                    currency,
                )

        matches = sum(
            1
            for report in reports
            if report["status"] == "MATCH"
        )

        mismatches = sum(
            1
            for report in reports
            if report["status"] == "MISMATCH"
        )

        logger.info(
            "Reconciliation job completed: "
            "wallets=%s matches=%s mismatches=%s",
            len(reports),
            matches,
            mismatches,
        )

        return reports

    except Exception:

        db.rollback()

        logger.exception(
            "Reconciliation job failed"
        )

        return []

    finally:
        db.close()


def start_scheduler():
    """
    Start the application-wide reconciliation scheduler.

    Reconciliation runs every 6 hours.
    """

    if scheduler.running:
        logger.info(
            "Reconciliation scheduler is already running"
        )
        return

    scheduler.add_job(
        run_reconciliation_job,
        trigger=IntervalTrigger(
            hours=RECONCILIATION_INTERVAL_HOURS
        ),
        id="wallet_reconciliation",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    scheduler.add_job(
        refresh_configured_currency_rates,
        trigger=IntervalTrigger(
            hours=CURRENCY_RATE_REFRESH_INTERVAL_HOURS
        ),
        id="currency_rate_refresh",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    scheduler.start()

    logger.info(
        "Wallet reconciliation scheduler started "
        "(interval=%s hours)",
        RECONCILIATION_INTERVAL_HOURS,
    )


def stop_scheduler():
    """
    Stop the reconciliation scheduler cleanly.
    """

    if not scheduler.running:
        logger.info(
            "Reconciliation scheduler is not running"
        )
        return

    scheduler.shutdown(
        wait=False
    )

    logger.info(
        "Wallet reconciliation scheduler stopped"
    )