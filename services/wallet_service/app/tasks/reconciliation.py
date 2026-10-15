 
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.wallet_balance import WalletBalance
from app.models.wallet_ledger import WalletLedger
from app.models.wallet_ledger_entry import WalletLedgerEntry


ZERO = Decimal("0.00")


def _wallet_account_total(
    db: Session,
    user_id: str,
    currency: str,
    entry_type: str,
) -> Decimal:
    """
    Calculate the total amount posted to the WALLET
    accounting account.

    For a customer wallet liability account:

        CREDIT to WALLET -> increases wallet
        DEBIT from WALLET -> decreases wallet
    """

    total = (
        db.query(
            func.coalesce(
                func.sum(WalletLedgerEntry.amount),
                0,
            )
        )
        .filter(
            WalletLedgerEntry.user_id == user_id,
            WalletLedgerEntry.currency == currency,
            WalletLedgerEntry.account_code == "WALLET",
            WalletLedgerEntry.entry_type == entry_type,
        )
        .scalar()
    )

    if total is None:
        return ZERO

    return Decimal(str(total))


def _count_transactions(
    db: Session,
    user_id: str,
    currency: str,
) -> int:
    """
    Count wallet transaction headers.
    """

    return (
        db.query(
            func.count(WalletLedger.id)
        )
        .filter(
            WalletLedger.user_id == user_id,
            WalletLedger.currency == currency,
        )
        .scalar()
        or 0
    )


def _count_accounting_transactions(
    db: Session,
    user_id: str,
    currency: str,
) -> int:
    """
    Count unique wallet transactions represented by
    accounting entries.
    """

    return (
        db.query(
            func.count(
                func.distinct(
                    WalletLedgerEntry.transaction_id
                )
            )
        )
        .filter(
            WalletLedgerEntry.user_id == user_id,
            WalletLedgerEntry.currency == currency,
        )
        .scalar()
        or 0
    )


def _legacy_ledger_total(
    db: Session,
    user_id: str,
    currency: str,
    transaction_type: str,
) -> Decimal:
    """
    Compatibility helper for legacy tests/data created
    before the double-entry migration.

    New wallet transactions must use wallet_ledger_entries.
    """

    total = (
        db.query(
            func.coalesce(
                func.sum(WalletLedger.amount),
                0,
            )
        )
        .filter(
            WalletLedger.user_id == user_id,
            WalletLedger.currency == currency,
            WalletLedger.transaction_type == transaction_type,
        )
        .scalar()
    )

    if total is None:
        return ZERO

    return Decimal(str(total))


def _legacy_expected_balance(
    db: Session,
    user_id: str,
    currency: str,
) -> Decimal:
    """
    Calculate expected balance using the original
    single-entry ledger format.

    This exists only as a migration compatibility path.
    """

    deposits = _legacy_ledger_total(
        db,
        user_id,
        currency,
        "DEPOSIT",
    )

    credits = _legacy_ledger_total(
        db,
        user_id,
        currency,
        "CREDIT",
    )

    refunds = _legacy_ledger_total(
        db,
        user_id,
        currency,
        "REFUND",
    )

    withdrawals = _legacy_ledger_total(
        db,
        user_id,
        currency,
        "WITHDRAW",
    )

    expired_credits = _legacy_ledger_total(
        db,
        user_id,
        currency,
        "CREDIT_EXPIRY",
    )

    return (
        deposits
        + credits
        + refunds
        - withdrawals
        - expired_credits
    )


def reconcile_wallet(
    db: Session,
    user_id: str,
    currency: str = "USD",
):
    """
    Reconcile a wallet against the true double-entry
    accounting ledger.

    The WALLET account is treated as the customer wallet
    liability account.

    Therefore:

        Expected wallet balance
            =
        WALLET credits - WALLET debits

    A wallet transaction should always have exactly two
    accounting entries. The database migration enforces
    the double-entry balance at transaction commit.

    A legacy fallback exists only when the wallet has
    transaction headers but no accounting entries at all.
    This allows old pre-migration test/data records to
    remain readable during the migration period.
    """

    # =========================================================
    # STEP 1: Get current wallet balance
    # =========================================================

    balance = (
        db.query(WalletBalance)
        .filter(
            WalletBalance.user_id == user_id,
            WalletBalance.currency == currency,
        )
        .first()
    )

    # =========================================================
    # STEP 2: Wallet does not exist
    # =========================================================

    if balance is None:
        return {
            "user_id": user_id,
            "currency": currency,
            "status": "NOT_FOUND",
            "expected_balance": ZERO,
            "actual_balance": ZERO,
            "difference": ZERO,
        }

    # =========================================================
    # STEP 3: Determine ledger mode
    # =========================================================

    transaction_count = _count_transactions(
        db,
        user_id,
        currency,
    )

    accounting_transaction_count = (
        _count_accounting_transactions(
            db,
            user_id,
            currency,
        )
    )

    # ---------------------------------------------------------
    # Legacy compatibility path.
    #
    # This should only occur for data created before the
    # double-entry migration.
    # ---------------------------------------------------------

    if (
        transaction_count > 0
        and accounting_transaction_count == 0
    ):
        expected_balance = _legacy_expected_balance(
            db,
            user_id,
            currency,
        )

        actual_balance = Decimal(
            str(balance.available_balance)
        )

        difference = (
            expected_balance
            - actual_balance
        )

        status = (
            "MATCH"
            if difference == ZERO
            else "MISMATCH"
        )

        return {
            "user_id": user_id,
            "currency": currency,
            "status": status,
            "expected_balance": expected_balance,
            "actual_balance": actual_balance,
            "difference": difference,
            "ledger_mode": "LEGACY",
        }

    # =========================================================
    # STEP 4: True double-entry calculation
    # =========================================================

    wallet_credits = _wallet_account_total(
        db,
        user_id,
        currency,
        "CREDIT",
    )

    wallet_debits = _wallet_account_total(
        db,
        user_id,
        currency,
        "DEBIT",
    )

    # =========================================================
    # STEP 5: Calculate expected wallet balance
    # =========================================================

    expected_balance = (
        wallet_credits
        - wallet_debits
    )

    # =========================================================
    # STEP 6: Actual wallet balance
    # =========================================================

    actual_balance = Decimal(
        str(balance.available_balance)
    )

    # =========================================================
    # STEP 7: Calculate difference
    # =========================================================

    difference = (
        expected_balance
        - actual_balance
    )

    # =========================================================
    # STEP 8: Determine status
    # =========================================================

    if difference == ZERO:
        status = "MATCH"
    else:
        status = "MISMATCH"

    # =========================================================
    # STEP 9: Return report
    # =========================================================

    return {
        "user_id": user_id,
        "currency": currency,
        "status": status,
        "expected_balance": expected_balance,
        "actual_balance": actual_balance,
        "difference": difference,
        "ledger_mode": "DOUBLE_ENTRY",
    }
