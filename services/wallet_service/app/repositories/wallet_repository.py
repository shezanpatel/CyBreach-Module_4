from datetime import datetime

from decimal import Decimal

from uuid import uuid4



from sqlalchemy.dialects.postgresql import insert

from sqlalchemy.orm import Session



from app.models.wallet_balance import WalletBalance

from app.models.wallet_credit import WalletCredit

from app.models.wallet_ledger import WalletLedger

from app.models.wallet_ledger_entry import WalletLedgerEntry





# ============================================================

# WALLET BALANCE

# ============================================================





def get_wallet_balance(

    db: Session,

    user_id: str,

    currency: str,

):

    """

    Fetch a wallet balance and lock the row for update.



    The row lock prevents concurrent financial operations from

    modifying the same wallet simultaneously.

    """

    return (

        db.query(WalletBalance)

        .filter(

            WalletBalance.user_id == user_id,

            WalletBalance.currency == currency,

        )

        .with_for_update()

        .first()

    )





def read_wallet_balance(
    db: Session,
    user_id: str,
    currency: str,
):
    """
    Read the current wallet balance without acquiring a row lock.

    This helper is intended only for read-only operations such as
    tenant-facing balance queries and completed idempotency replays.

    Financial mutation paths must continue to use
    get_wallet_balance() or get_or_create_wallet_balance(), both of
    which acquire SELECT ... FOR UPDATE locks where required.
    """
    return (
        db.query(WalletBalance)
        .filter(
            WalletBalance.user_id == user_id,
            WalletBalance.currency == currency,
        )
        .first()
    )


def get_or_create_wallet_balance(

    db: Session,

    user_id: str,

    currency: str,

):

    """

    Atomically get or create a wallet balance.



    PostgreSQL INSERT ... ON CONFLICT DO NOTHING prevents

    concurrent requests from creating duplicate wallet rows.



    The wallet is then selected with FOR UPDATE so the caller

    owns the row lock before modifying the balance.

    """



    stmt = (

        insert(WalletBalance)

        .values(

            user_id=user_id,

            currency=currency,

            available_balance=Decimal("0.00"),

            is_paused=False,

        )

        .on_conflict_do_nothing(

            index_elements=[

                WalletBalance.user_id,

                WalletBalance.currency,

            ]

        )

    )



    db.execute(stmt)

    db.flush()



    balance = (

        db.query(WalletBalance)

        .filter(

            WalletBalance.user_id == user_id,

            WalletBalance.currency == currency,

        )

        .with_for_update()

        .first()

    )



    if balance is None:

        raise RuntimeError(

            "Failed to create or retrieve wallet balance"

        )



    return balance





def create_wallet_balance(

    db: Session,

    balance: WalletBalance,

):

    """

    Create a new wallet balance record.

    """

    db.add(balance)

    db.flush()

    return balance





def update_wallet_balance(

    db: Session,

    balance: WalletBalance,

):

    """

    Update an existing wallet balance.

    """

    db.add(balance)

    db.flush()

    return balance





# ============================================================

# WALLET PAUSE / RESUME

# ============================================================





def pause_wallet(

    db: Session,

    user_id: str,

    currency: str,

    reason: str,

):

    """

    Pause a wallet after a financial-integrity problem.



    The wallet row is locked before the pause state is changed.



    This function does NOT commit.

    The caller owns the transaction boundary.

    """

    from datetime import UTC, datetime



    balance = (

        db.query(WalletBalance)

        .filter(

            WalletBalance.user_id == user_id,

            WalletBalance.currency == currency,

        )

        .with_for_update()

        .first()

    )



    if balance is None:

        return None



    balance.is_paused = True

    balance.pause_reason = reason

    balance.paused_at = datetime.now(UTC)



    db.add(balance)

    db.flush()



    return balance





def resume_wallet(

    db: Session,

    user_id: str,

    currency: str,

):

    """

    Resume a previously paused wallet.



    This operation is intentionally explicit.

    Reconciliation must not automatically resume a wallet

    merely because a later reconciliation happens to match.



    This function does NOT commit.

    The caller owns the transaction boundary.

    """

    balance = (

        db.query(WalletBalance)

        .filter(

            WalletBalance.user_id == user_id,

            WalletBalance.currency == currency,

        )

        .with_for_update()

        .first()

    )



    if balance is None:

        return None



    balance.is_paused = False

    balance.pause_reason = None

    balance.paused_at = None



    db.add(balance)

    db.flush()



    return balance





def is_wallet_paused(

    db: Session,

    user_id: str,

    currency: str,

) -> bool:

    """

    Return whether a wallet is currently paused.



    This performs a normal read and does not acquire a row lock.

    Financial operations should use get_wallet_balance() or

    get_or_create_wallet_balance() when they need a lock.

    """

    balance = (

        db.query(WalletBalance)

        .filter(

            WalletBalance.user_id == user_id,

            WalletBalance.currency == currency,

        )

        .first()

    )



    if balance is None:

        return False



    return bool(balance.is_paused)





# ============================================================

# DOUBLE-ENTRY LEDGER

# ============================================================





LEDGER_ACCOUNT_MAPPING = {

    "DEPOSIT": {

        "debit": "CASH",

        "credit": "WALLET",

    },

    "WITHDRAW": {

        "debit": "WALLET",

        "credit": "CASH",

    },

    "CREDIT": {

        "debit": "CREDIT_SOURCE",

        "credit": "WALLET",

    },

    "REFUND": {

        "debit": "REFUND_EXPENSE",

        "credit": "WALLET",

    },

    "CREDIT_EXPIRY": {

        "debit": "WALLET",

        "credit": "CREDIT_EXPIRY_REVENUE",

    },

}





def create_double_entry(

    db: Session,

    ledger: WalletLedger,

):

    """

    Create the two accounting entries belonging to a

    wallet transaction.



    Every transaction produces:



        DEBIT  -> source account

        CREDIT -> destination account



    Both entries use:



        - the same transaction ID

        - the same user

        - the same transaction type

        - the same currency

        - the same amount

        - the same reference ID

        - the same module source



    The database migration additionally enforces that the

    transaction contains exactly one DEBIT and one CREDIT

    with equal amounts.



    Week 9:

    module_source is propagated from the transaction header

    to both accounting entries so audit queries can identify

    the originating CyBreach module.

    """



    if ledger.amount <= Decimal("0.00"):

        raise ValueError(

            "Ledger amount must be greater than zero"

        )



    mapping = LEDGER_ACCOUNT_MAPPING.get(

        ledger.transaction_type

    )



    if mapping is None:

        raise ValueError(

            "Unsupported wallet transaction type: "

            f"{ledger.transaction_type}"

        )



    debit_entry = WalletLedgerEntry(

        id=uuid4(),

        transaction_id=ledger.id,

        user_id=ledger.user_id,

        transaction_type=ledger.transaction_type,

        currency=ledger.currency,

        entry_type="DEBIT",

        account_code=mapping["debit"],

        amount=ledger.amount,

        reference_id=ledger.reference_id,

        module_source=ledger.module_source,

    )



    credit_entry = WalletLedgerEntry(

        id=uuid4(),

        transaction_id=ledger.id,

        user_id=ledger.user_id,

        transaction_type=ledger.transaction_type,

        currency=ledger.currency,

        entry_type="CREDIT",

        account_code=mapping["credit"],

        amount=ledger.amount,

        reference_id=ledger.reference_id,

        module_source=ledger.module_source,

    )



    db.add_all(

        [

            debit_entry,

            credit_entry,

        ]

    )



    db.flush()



    return debit_entry, credit_entry





def create_ledger_entry(

    db: Session,

    ledger: WalletLedger,

):

    """

    Record a wallet transaction header and its complete

    double-entry accounting pair.



    Supported transaction types:



        DEPOSIT

        WITHDRAW

        CREDIT

        REFUND

        CREDIT_EXPIRY

    """

    db.add(ledger)

    db.flush()



    create_double_entry(

        db=db,

        ledger=ledger,

    )



    return ledger





def get_ledger_entries_for_transaction(

    db: Session,

    transaction_id,

):

    """

    Retrieve the accounting entries belonging to a

    wallet transaction.

    """

    return (

        db.query(WalletLedgerEntry)

        .filter(

            WalletLedgerEntry.transaction_id

            == transaction_id

        )

        .order_by(

            WalletLedgerEntry.entry_type.asc()

        )

        .all()

    )





def get_user_ledger_entries(

    db: Session,

    user_id: str,

    currency: str | None = None,

):

    """

    Retrieve accounting entries for a user.



    Entries are returned newest first.

    """

    query = (

        db.query(WalletLedgerEntry)

        .filter(

            WalletLedgerEntry.user_id == user_id

        )

    )



    if currency:

        query = query.filter(

            WalletLedgerEntry.currency == currency

        )



    return (

        query

        .order_by(

            WalletLedgerEntry.created_at.desc()

        )

        .all()

    )





def get_wallet_audit_entries(

    db: Session,

    user_id: str,

    *,

    date_from: datetime | None = None,

    date_to: datetime | None = None,

    entry_type: str | None = None,

    module_source: str | None = None,

    limit: int = 100,

    offset: int = 0,

):

    """

    Retrieve the append-only wallet audit trail for a user.



    Week 9 audit filters:



        - date range

        - entry type

        - module source



    Results are returned newest first and support offset-based

    pagination.



    This query is read-only and operates on the double-entry

    accounting ledger.

    """



    if limit < 1:

        raise ValueError("limit must be greater than zero")



    if limit > 1000:

        raise ValueError("limit must not exceed 1000")



    if offset < 0:

        raise ValueError("offset must not be negative")



    if date_from and date_to and date_from > date_to:

        raise ValueError(

            "date_from must be earlier than or equal to date_to"

        )



    query = (

        db.query(WalletLedgerEntry)

        .filter(

            WalletLedgerEntry.user_id == user_id

        )

    )



    if date_from is not None:

        query = query.filter(

            WalletLedgerEntry.created_at >= date_from

        )



    if date_to is not None:

        query = query.filter(

            WalletLedgerEntry.created_at <= date_to

        )



    if entry_type is not None:

        normalized_entry_type = entry_type.upper()



        if normalized_entry_type not in {

            "DEBIT",

            "CREDIT",

        }:

            raise ValueError(

                "entry_type must be DEBIT or CREDIT"

            )



        query = query.filter(

            WalletLedgerEntry.entry_type

            == normalized_entry_type

        )



    if module_source is not None:

        query = query.filter(

            WalletLedgerEntry.module_source

            == module_source

        )



    total = query.count()



    entries = (

        query

        .order_by(

            WalletLedgerEntry.created_at.desc(),

            WalletLedgerEntry.id.desc(),

        )

        .offset(offset)

        .limit(limit)

        .all()

    )



    return entries, total





def get_wallet_audit_export_entries(

    db: Session,

    user_id: str,

    *,

    date_from: datetime | None = None,

    date_to: datetime | None = None,

    entry_type: str | None = None,

    module_source: str | None = None,

):

    """

    Retrieve the full filtered wallet audit trail for CSV export.



    Unlike the paginated history query, this export query does not

    apply the 1000-row API page limit.

    """



    if date_from and date_to and date_from > date_to:

        raise ValueError(

            "date_from must be earlier than or equal to date_to"

        )



    query = (

        db.query(WalletLedgerEntry)

        .filter(WalletLedgerEntry.user_id == user_id)

    )



    if date_from is not None:

        query = query.filter(

            WalletLedgerEntry.created_at >= date_from

        )



    if date_to is not None:

        query = query.filter(

            WalletLedgerEntry.created_at <= date_to

        )



    if entry_type is not None:

        normalized_entry_type = entry_type.upper()



        if normalized_entry_type not in {

            "DEBIT",

            "CREDIT",

        }:

            raise ValueError(

                "entry_type must be DEBIT or CREDIT"

            )



        query = query.filter(

            WalletLedgerEntry.entry_type

            == normalized_entry_type

        )



    if module_source is not None:

        query = query.filter(

            WalletLedgerEntry.module_source

            == module_source

        )



    return (

        query

        .order_by(

            WalletLedgerEntry.created_at.desc(),

            WalletLedgerEntry.id.desc(),

        )

        .all()

    )





def get_user_transactions(

    db: Session,

    user_id: str,

):

    """

    Retrieve all wallet transaction headers for a user.



    Transactions are returned newest first.

    """

    return (

        db.query(WalletLedger)

        .filter(

            WalletLedger.user_id == user_id

        )

        .order_by(

            WalletLedger.created_at.desc()

        )

        .all()

    )





# ============================================================

# WALLET CREDIT

# ============================================================





def create_wallet_credit(

    db: Session,

    credit: WalletCredit,

):

    """

    Create a WalletCredit record.

    """

    db.add(credit)

    db.flush()



    return credit





def get_expired_wallet_credits(

    db: Session,

):

    """

    Retrieve wallet credits that have expired and still have

    a positive remaining amount.



    The rows are locked so concurrent expiry processing cannot

    process the same credit simultaneously.

    """

    from datetime import UTC, datetime



    return (

        db.query(WalletCredit)

        .filter(

            WalletCredit.expires_at <= datetime.now(UTC),

            WalletCredit.remaining_amount > Decimal("0.00"),

            WalletCredit.expired_at.is_(None),

        )

        .with_for_update()

        .all()

    )





def update_wallet_credit(

    db: Session,

    credit: WalletCredit,

):

    """

    Update an existing wallet credit.



    The caller owns the transaction boundary.

    """

    db.add(credit)

    db.flush()



    return credit
