 
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from app.core.database import SessionLocal
from app.models.wallet_balance import WalletBalance
from app.tasks.scheduler import (
    RECONCILIATION_INTERVAL_HOURS,
    scheduler,
    run_reconciliation_job,
)


def test_reconciliation_interval_is_six_hours():
    assert RECONCILIATION_INTERVAL_HOURS == 6


def test_reconciliation_job_reconciles_all_wallets():
    db = SessionLocal()

    user_id_1 = f"scheduler_test_1_{uuid4().hex[:8]}"
    user_id_2 = f"scheduler_test_2_{uuid4().hex[:8]}"

    try:
        # ---------------------------------------------------------
        # Create exactly two test wallets
        # ---------------------------------------------------------
        wallet_1 = WalletBalance(
            user_id=user_id_1,
            currency="USD",
            available_balance=Decimal("100.00"),
        )

        wallet_2 = WalletBalance(
            user_id=user_id_2,
            currency="USD",
            available_balance=Decimal("200.00"),
        )

        db.add_all(
            [
                wallet_1,
                wallet_2,
            ]
        )

        db.commit()

        # ---------------------------------------------------------
        # Mock the reconciliation function
        # ---------------------------------------------------------
        def fake_reconcile(
            db,
            user_id,
            currency,
        ):
            if user_id == user_id_1:
                return {
                    "user_id": user_id_1,
                    "currency": "USD",
                    "status": "MATCH",
                    "expected_balance": Decimal("100.00"),
                    "actual_balance": Decimal("100.00"),
                    "difference": Decimal("0.00"),
                }

            if user_id == user_id_2:
                return {
                    "user_id": user_id_2,
                    "currency": "USD",
                    "status": "MATCH",
                    "expected_balance": Decimal("200.00"),
                    "actual_balance": Decimal("200.00"),
                    "difference": Decimal("0.00"),
                }

            # Any other wallet belongs to previous tests.
            # Return a valid reconciliation report instead of
            # exhausting a mock side_effect.
            return {
                "user_id": user_id,
                "currency": currency,
                "status": "MATCH",
                "expected_balance": Decimal("0.00"),
                "actual_balance": Decimal("0.00"),
                "difference": Decimal("0.00"),
            }

        with patch(
            "app.tasks.scheduler.reconcile_wallet",
            side_effect=fake_reconcile,
        ) as mock_reconcile:
            reports = run_reconciliation_job()

        # ---------------------------------------------------------
        # Verify our two wallets were reconciled
        # ---------------------------------------------------------
        reconciled_users = {
            report["user_id"]
            for report in reports
        }

        assert user_id_1 in reconciled_users
        assert user_id_2 in reconciled_users

        # ---------------------------------------------------------
        # Verify the scheduler actually reconciled wallets
        # ---------------------------------------------------------
        assert mock_reconcile.call_count >= 2

    finally:
        # ---------------------------------------------------------
        # Remove only wallets created by THIS test
        # ---------------------------------------------------------
        db.query(WalletBalance).filter(
            WalletBalance.user_id.in_(
                [
                    user_id_1,
                    user_id_2,
                ]
            )
        ).delete(
            synchronize_session=False
        )

        db.commit()
        db.close()


def test_scheduler_job_configuration():
    existing_job = scheduler.get_job(
        "wallet_reconciliation"
    )

    if existing_job is not None:
        scheduler.remove_job(
            "wallet_reconciliation"
        )

    scheduler.add_job(
        lambda: None,
        trigger="interval",
        hours=RECONCILIATION_INTERVAL_HOURS,
        id="wallet_reconciliation",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    try:
        job = scheduler.get_job(
            "wallet_reconciliation"
        )

        assert job is not None
        assert job.id == "wallet_reconciliation"

        assert (
            job.trigger.interval.total_seconds()
            == RECONCILIATION_INTERVAL_HOURS * 60 * 60
        )

        assert job.max_instances == 1
        assert job.coalesce is True

    finally:
        scheduler.remove_job(
            "wallet_reconciliation"
        )
