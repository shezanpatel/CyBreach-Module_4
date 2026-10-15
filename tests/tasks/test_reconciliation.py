from decimal import Decimal
from uuid import uuid4

from app.core.database import SessionLocal
from app.models.wallet_balance import WalletBalance
from app.models.wallet_ledger import WalletLedger
from app.tasks.reconciliation import reconcile_wallet


def test_reconciliation_matches_ledger():
    db = SessionLocal()

    user_id = f"reconcile_test_{uuid4().hex[:8]}"
    currency = "USD"

    try:
        # -----------------------------------------
        # Wallet balance = $80
        # -----------------------------------------
        balance = WalletBalance(
            user_id=user_id,
            currency=currency,
            available_balance=Decimal("80.00"),
        )

        db.add(balance)

        # -----------------------------------------
        # Ledger:
        # Deposit $100
        # Withdraw $20
        #
        # Expected balance = $80
        # -----------------------------------------
        db.add(
            WalletLedger(
                user_id=user_id,
                transaction_type="DEPOSIT",
                currency=currency,
                amount=Decimal("100.00"),
                reference_id=f"deposit-{uuid4().hex}",
            )
        )

        db.add(
            WalletLedger(
                user_id=user_id,
                transaction_type="WITHDRAW",
                currency=currency,
                amount=Decimal("20.00"),
                reference_id=f"withdraw-{uuid4().hex}",
            )
        )

        db.commit()

        result = reconcile_wallet(
            db,
            user_id,
            currency,
        )

        assert result["status"] == "MATCH"
        assert result["expected_balance"] == Decimal("80.00")
        assert result["actual_balance"] == Decimal("80.00")
        assert result["difference"] == Decimal("0.00")

    finally:
        db.rollback()
        db.close()


def test_reconciliation_detects_mismatch():
    db = SessionLocal()

    user_id = f"reconcile_mismatch_{uuid4().hex[:8]}"
    currency = "USD"

    try:
        # -----------------------------------------
        # Wallet incorrectly says $80
        # -----------------------------------------
        balance = WalletBalance(
            user_id=user_id,
            currency=currency,
            available_balance=Decimal("80.00"),
        )

        db.add(balance)

        # -----------------------------------------
        # Ledger:
        # Deposit $100
        # Withdraw $10
        #
        # Expected balance = $90
        # Actual wallet balance = $80
        #
        # Difference = $10
        # -----------------------------------------
        db.add(
            WalletLedger(
                user_id=user_id,
                transaction_type="DEPOSIT",
                currency=currency,
                amount=Decimal("100.00"),
                reference_id=f"deposit-{uuid4().hex}",
            )
        )

        db.add(
            WalletLedger(
                user_id=user_id,
                transaction_type="WITHDRAW",
                currency=currency,
                amount=Decimal("10.00"),
                reference_id=f"withdraw-{uuid4().hex}",
            )
        )

        db.commit()

        result = reconcile_wallet(
            db,
            user_id,
            currency,
        )

        assert result["status"] == "MISMATCH"
        assert result["expected_balance"] == Decimal("90.00")
        assert result["actual_balance"] == Decimal("80.00")
        assert result["difference"] == Decimal("10.00")

    finally:
        db.rollback()
        db.close()