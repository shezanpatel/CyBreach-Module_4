from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.wallet_balance import WalletBalance
from app.models.wallet_ledger import WalletLedger
from app.models.wallet_ledger_entry import WalletLedgerEntry


ZERO = Decimal("0.00")


# ============================================================
# DOUBLE-ENTRY WALLET ACCOUNT CALCULATION
# ============================================================


def _wallet_account_total(
    db: Session,
    user_id: str,
    currency: str,
    entry_type: str,
) -> Decimal:
    """
    Calculate the total amount posted to the WALLET
    accounting account for one entry type.

    The WALLET account represents the customer's wallet
    liability.

    Therefore:

        CREDIT to WALLET -> increases wallet balance
        DEBIT to WALLET  -> decreases wallet balance
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


# ============================================================
# TRANSACTION COUNTS
# ============================================================


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
    Count unique transactions represented in the
    double-entry accounting table.
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


# ============================================================
# LEGACY LEDGER COMPATIBILITY
# ============================================================


def _legacy_ledger_total(
    db: Session,
    user_id: str,
    currency: str,
    transaction_type: str,
) -> Decimal:
    """
    Calculate a transaction total from the original
    wallet_ledger table.

    This exists only for records created before the
    true double-entry ledger migration.
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
    Calculate the expected wallet balance from legacy
    single-entry transaction headers.

    This compatibility path must only be used when transaction
    headers exist but no double-entry accounting records exist.
    """

    deposits = _legacy_ledger_total(
        db=db,
        user_id=user_id,
        currency=currency,
        transaction_type="DEPOSIT",
    )

    credits = _legacy_ledger_total(
        db=db,
        user_id=user_id,
        currency=currency,
        transaction_type="CREDIT",
    )

    refunds = _legacy_ledger_total(
        db=db,
        user_id=user_id,
        currency=currency,
        transaction_type="REFUND",
    )

    withdrawals = _legacy_ledger_total(
        db=db,
        user_id=user_id,
        currency=currency,
        transaction_type="WITHDRAW",
    )

    expired_credits = _legacy_ledger_total(
        db=db,
        user_id=user_id,
        currency=currency,
        transaction_type="CREDIT_EXPIRY",
    )

    return (
        deposits
        + credits
        + refunds
        - withdrawals
        - expired_credits
    )


# ============================================================
# DOUBLE-ENTRY STRUCTURAL VALIDATION
# ============================================================


def _find_invalid_accounting_transactions(
    db: Session,
    user_id: str,
    currency: str,
) -> list:
    """
    Detect transaction IDs whose accounting entries do not
    form a valid two-entry accounting pair.

    A valid transaction must contain:

        exactly 2 entries
        exactly 1 DEBIT
        exactly 1 CREDIT
        equal DEBIT and CREDIT totals

    Database constraints should normally prevent invalid
    committed transactions. This check gives reconciliation
    an additional integrity-verification layer.
    """

    transaction_ids = (
        db.query(
            WalletLedgerEntry.transaction_id
        )
        .filter(
            WalletLedgerEntry.user_id == user_id,
            WalletLedgerEntry.currency == currency,
        )
        .distinct()
        .all()
    )

    invalid_transactions = []

    for row in transaction_ids:
        transaction_id = row[0]

        entries = (
            db.query(WalletLedgerEntry)
            .filter(
                WalletLedgerEntry.transaction_id
                == transaction_id
            )
            .all()
        )

        debit_entries = [
            entry
            for entry in entries
            if entry.entry_type == "DEBIT"
        ]

        credit_entries = [
            entry
            for entry in entries
            if entry.entry_type == "CREDIT"
        ]

        debit_total = sum(
            (
                Decimal(str(entry.amount))
                for entry in debit_entries
            ),
            ZERO,
        )

        credit_total = sum(
            (
                Decimal(str(entry.amount))
                for entry in credit_entries
            ),
            ZERO,
        )

        valid = (
            len(entries) == 2
            and len(debit_entries) == 1
            and len(credit_entries) == 1
            and debit_total == credit_total
        )

        if not valid:
            invalid_transactions.append(
                {
                    "transaction_id": str(
                        transaction_id
                    ),
                    "entry_count": len(entries),
                    "debit_count": len(
                        debit_entries
                    ),
                    "credit_count": len(
                        credit_entries
                    ),
                    "debit_total": debit_total,
                    "credit_total": credit_total,
                }
            )

    return invalid_transactions


# ============================================================
# RECONCILIATION SERVICE
# ============================================================


def reconcile_wallet(
    db: Session,
    user_id: str,
    currency: str = "USD",
):
    """
    Reconcile the materialized wallet balance against the
    accounting ledger.

    Current accounting model:

        WALLET CREDIT -> increases wallet balance
        WALLET DEBIT  -> decreases wallet balance

    Therefore:

        expected balance
            =
        WALLET credits - WALLET debits

    The service also validates the structural integrity of
    double-entry accounting records.

    A legacy compatibility path remains for wallets created
    before the true double-entry migration.
    """

    # ========================================================
    # STEP 1: Find wallet
    # ========================================================

    balance = (
        db.query(WalletBalance)
        .filter(
            WalletBalance.user_id == user_id,
            WalletBalance.currency == currency,
        )
        .first()
    )

    # ========================================================
    # STEP 2: Wallet does not exist
    # ========================================================

    if balance is None:
        return {
            "user_id": user_id,
            "currency": currency,
            "status": "NOT_FOUND",
            "expected_balance": ZERO,
            "actual_balance": ZERO,
            "difference": ZERO,
            "ledger_mode": None,
            "invalid_transaction_count": 0,
            "invalid_transactions": [],
        }

    # ========================================================
    # STEP 3: Determine available ledger format
    # ========================================================

    transaction_count = _count_transactions(
        db=db,
        user_id=user_id,
        currency=currency,
    )

    accounting_transaction_count = (
        _count_accounting_transactions(
            db=db,
            user_id=user_id,
            currency=currency,
        )
    )

    actual_balance = Decimal(
        str(balance.available_balance)
    )

    # ========================================================
    # STEP 4: Legacy compatibility
    # ========================================================

    if (
        transaction_count > 0
        and accounting_transaction_count == 0
    ):
        expected_balance = (
            _legacy_expected_balance(
                db=db,
                user_id=user_id,
                currency=currency,
            )
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
            "invalid_transaction_count": 0,
            "invalid_transactions": [],
        }

    # ========================================================
    # STEP 5: Validate double-entry transaction structure
    # ========================================================

    invalid_transactions = (
        _find_invalid_accounting_transactions(
            db=db,
            user_id=user_id,
            currency=currency,
        )
    )

    # ========================================================
    # STEP 6: Calculate WALLET accounting totals
    # ========================================================

    wallet_credits = _wallet_account_total(
        db=db,
        user_id=user_id,
        currency=currency,
        entry_type="CREDIT",
    )

    wallet_debits = _wallet_account_total(
        db=db,
        user_id=user_id,
        currency=currency,
        entry_type="DEBIT",
    )

    # ========================================================
    # STEP 7: Calculate expected balance
    # ========================================================

    expected_balance = (
        wallet_credits
        - wallet_debits
    )

    # ========================================================
    # STEP 8: Compare expected and actual balances
    # ========================================================

    difference = (
        expected_balance
        - actual_balance
    )

    # ========================================================
    # STEP 9: Determine reconciliation result
    # ========================================================

    if (
        difference == ZERO
        and not invalid_transactions
    ):
        status = "MATCH"
    else:
        status = "MISMATCH"

    # ========================================================
    # STEP 10: Return reconciliation report
    # ========================================================

    return {
        "user_id": user_id,
        "currency": currency,
        "status": status,
        "expected_balance": expected_balance,
        "actual_balance": actual_balance,
        "difference": difference,
        "ledger_mode": "DOUBLE_ENTRY",
        "invalid_transaction_count": len(
            invalid_transactions
        ),
        "invalid_transactions": invalid_transactions,
    }