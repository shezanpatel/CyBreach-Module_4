import threading
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import text

from app.core.database import SessionLocal
from app.models.wallet_balance import WalletBalance
from app.models.wallet_ledger import WalletLedger
from app.models.wallet_ledger_entry import WalletLedgerEntry
from app.services.wallet_service import withdraw_money


def test_concurrent_withdrawals_cannot_overspend():
    """
    Verify that concurrent withdrawals against the same wallet
    cannot spend the same balance twice.

    Starting balance:
        $100

    Concurrent requests:
        Withdrawal A -> $80
        Withdrawal B -> $80

    Expected:
        Exactly one withdrawal succeeds.
        Exactly one withdrawal fails.
        Final balance is $20.
        Exactly one withdrawal ledger transaction exists.
        That transaction contains exactly one DEBIT and one CREDIT.
    """

    user_id = f"concurrency-test-{uuid4()}"
    currency = "USD"

    # ============================================================
    # CREATE TEST WALLET
    # ============================================================

    setup_db = SessionLocal()

    try:
        wallet = WalletBalance(
            user_id=user_id,
            currency=currency,
            available_balance=Decimal("100.00"),
        )

        setup_db.add(wallet)
        setup_db.commit()

    finally:
        setup_db.close()

    # ============================================================
    # SYNCHRONIZE TWO CONCURRENT REQUESTS
    # ============================================================

    barrier = threading.Barrier(2)

    def perform_withdrawal():
        db = SessionLocal()

        try:
            # Force both workers to begin the withdrawal at
            # approximately the same time.
            barrier.wait()

            result = withdraw_money(
                db=db,
                user_id=user_id,
                amount=Decimal("80.00"),
                currency=currency,
            )

            return {
                "success": True,
                "balance": result.available_balance,
                "error": None,
            }

        except Exception as exc:
            return {
                "success": False,
                "balance": None,
                "error": exc,
            }

        finally:
            db.close()

    try:
        # ========================================================
        # RUN TWO CONCURRENT WITHDRAWALS
        # ========================================================

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(perform_withdrawal),
                executor.submit(perform_withdrawal),
            ]

            results = [
                future.result()
                for future in futures
            ]

        # ========================================================
        # VERIFY SUCCESS / FAILURE
        # ========================================================

        successful = [
            result
            for result in results
            if result["success"]
        ]

        failed = [
            result
            for result in results
            if not result["success"]
        ]

        # Exactly one $80 withdrawal must succeed.
        assert len(successful) == 1, (
            f"Expected exactly 1 successful withdrawal, "
            f"got {len(successful)}. Results: {results}"
        )

        # Exactly one withdrawal must fail.
        assert len(failed) == 1, (
            f"Expected exactly 1 failed withdrawal, "
            f"got {len(failed)}. Results: {results}"
        )

        # ========================================================
        # VERIFY FINAL WALLET BALANCE
        # ========================================================

        verify_db = SessionLocal()

        try:
            final_wallet = (
                verify_db.query(WalletBalance)
                .filter(
                    WalletBalance.user_id == user_id,
                    WalletBalance.currency == currency,
                )
                .one()
            )

            assert final_wallet.available_balance == Decimal(
                "20.00"
            ), (
                "Concurrent withdrawals overspent or corrupted "
                f"the wallet. Final balance: "
                f"{final_wallet.available_balance}"
            )

            # ====================================================
            # VERIFY LEDGER TRANSACTION COUNT
            # ====================================================

            ledger_transactions = (
                verify_db.query(WalletLedger)
                .filter(
                    WalletLedger.user_id == user_id,
                    WalletLedger.transaction_type == "WITHDRAW",
                )
                .all()
            )

            assert len(ledger_transactions) == 1, (
                "Expected exactly one successful withdrawal "
                f"ledger transaction, got "
                f"{len(ledger_transactions)}"
            )

            successful_transaction = ledger_transactions[0]

            assert successful_transaction.amount == Decimal(
                "80.00"
            )

            # ====================================================
            # VERIFY DOUBLE-ENTRY ACCOUNTING
            # ====================================================

            ledger_entries = (
                verify_db.query(WalletLedgerEntry)
                .filter(
                    WalletLedgerEntry.transaction_id
                    == successful_transaction.id
                )
                .all()
            )

            # One DEBIT + one CREDIT.
            assert len(ledger_entries) == 2, (
                "Successful withdrawal must contain exactly "
                f"2 ledger entries, got {len(ledger_entries)}"
            )

            entry_types = {
                entry.entry_type
                for entry in ledger_entries
            }

            assert entry_types == {
                "DEBIT",
                "CREDIT",
            }

            # Both entries must have the same amount.
            amounts = {
                entry.amount
                for entry in ledger_entries
            }

            assert amounts == {
                Decimal("80.00")
            }

            # Both entries must use USD.
            currencies = {
                entry.currency
                for entry in ledger_entries
            }

            assert currencies == {
                "USD"
            }

            # ====================================================
            # VERIFY ACCOUNT MAPPING
            # ====================================================

            debit_entry = next(
                entry
                for entry in ledger_entries
                if entry.entry_type == "DEBIT"
            )

            credit_entry = next(
                entry
                for entry in ledger_entries
                if entry.entry_type == "CREDIT"
            )

            assert debit_entry.account_code == "WALLET"
            assert credit_entry.account_code == "CASH"

        finally:
            verify_db.close()

    finally:
        # ========================================================
        # TEST CLEANUP
        # ========================================================
        #
        # wallet_ledger is protected by a deferred database
        # trigger that requires every transaction to remain
        # balanced.
        #
        # Therefore, ordinary deletion of ledger entries would
        # temporarily create:
        #
        #     entries = 0
        #     debits  = 0
        #     credits = 0
        #
        # and the trigger would correctly reject the transaction.
        #
        # This cleanup is ONLY for this isolated test data.
        # It does not modify the production trigger or schema.
        # ========================================================

        cleanup_db = SessionLocal()

        try:
            transaction_ids = [
                row.id
                for row in cleanup_db.query(WalletLedger.id)
                .filter(
                    WalletLedger.user_id == user_id
                )
                .all()
            ]

            if transaction_ids:
                # Disable triggers only inside this cleanup
                # transaction so test records can be removed.
                #
                # This requires the PostgreSQL role to have the
                # necessary privilege. If it does not, the test
                # will report that clearly.
                cleanup_db.execute(
                    text(
                        "SET LOCAL session_replication_role = replica"
                    )
                )

                cleanup_db.query(WalletLedgerEntry).filter(
                    WalletLedgerEntry.transaction_id.in_(
                        transaction_ids
                    )
                ).delete(
                    synchronize_session=False
                )

                cleanup_db.query(WalletLedger).filter(
                    WalletLedger.id.in_(transaction_ids)
                ).delete(
                    synchronize_session=False
                )

            cleanup_db.query(WalletBalance).filter(
                WalletBalance.user_id == user_id,
                WalletBalance.currency == currency,
            ).delete(
                synchronize_session=False
            )

            cleanup_db.commit()

        except Exception:
            cleanup_db.rollback()
            raise

        finally:
            cleanup_db.close()