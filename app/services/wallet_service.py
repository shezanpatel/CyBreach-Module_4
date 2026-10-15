import time

from decimal import Decimal

from functools import wraps

from typing import Callable

from uuid import uuid4



from sqlalchemy.exc import IntegrityError, OperationalError

from sqlalchemy.orm import Session



from app.core.exceptions import (

    IdempotencyKeyReuseError,

    InsufficientBalance,

    WalletNotFound,

    WalletPaused,

)

from app.events.kafka_producer import publish_event_sync

from app.models.wallet_credit import WalletCredit

from app.models.wallet_ledger import WalletLedger

from app.repositories.idempotency_repository import (

    claim_idempotency_key,

    generate_request_hash,

)

from app.repositories.wallet_repository import (

    create_ledger_entry,

    create_wallet_credit,

    get_or_create_wallet_balance,

    get_user_transactions,

    get_wallet_audit_entries,

    get_wallet_audit_export_entries,

    get_wallet_balance,

    read_wallet_balance,

    update_wallet_balance,

)

from app.services.budget_alert_service import (

    check_budget_alert_after_balance_change,

)





# ============================================================

# SERIALIZATION RETRY CONFIGURATION

# ============================================================



MAX_SERIALIZATION_RETRIES = 8



SERIALIZATION_RETRY_DELAYS = (

    0.05,

    0.10,

    0.20,

    0.40,

    0.80,

    1.00,

    1.00,

    1.00,

)





def _is_serialization_failure(

    error: OperationalError,

) -> bool:

    """

    Determine whether an SQLAlchemy OperationalError was caused

    by a PostgreSQL serialization failure.



    PostgreSQL SQLSTATE:

        40001 = serialization_failure

    """



    original_error = getattr(

        error,

        "orig",

        None,

    )



    if original_error is None:

        return False



    sqlstate = getattr(

        original_error,

        "sqlstate",

        None,

    )



    if sqlstate == "40001":

        return True



    pgcode = getattr(

        original_error,

        "pgcode",

        None,

    )



    if pgcode == "40001":

        return True



    diagnostic = getattr(

        original_error,

        "diag",

        None,

    )



    diagnostic_sqlstate = getattr(

        diagnostic,

        "sqlstate",

        None,

    )



    return diagnostic_sqlstate == "40001"





def retry_on_serialization_failure(

    function: Callable,

):

    """

    Retry a complete wallet operation when PostgreSQL aborts

    the transaction because of SERIALIZABLE isolation.



    The wallet operation performs rollback before the

    OperationalError reaches this decorator.



    Therefore every retry starts with a clean transaction

    state.



    Non-serialization OperationalErrors are not retried.

    """



    @wraps(function)

    def wrapper(*args, **kwargs):

        for attempt in range(

            MAX_SERIALIZATION_RETRIES + 1

        ):

            try:

                return function(

                    *args,

                    **kwargs,

                )



            except OperationalError as error:

                if not _is_serialization_failure(error):

                    raise



                if attempt >= MAX_SERIALIZATION_RETRIES:

                    raise



                delay = SERIALIZATION_RETRY_DELAYS[

                    min(

                        attempt,

                        len(

                            SERIALIZATION_RETRY_DELAYS

                        ) - 1,

                    )

                ]



                time.sleep(delay)



    return wrapper





# ============================================================

# IDEMPOTENCY

# ============================================================



def _build_request_hash(

    *,

    user_id: str,

    endpoint: str,

    amount: Decimal,

    currency: str,

    reference_id: str | None = None,

) -> str:

    """

    Build the canonical request fingerprint used by all

    financial wallet operations.

    """



    return generate_request_hash(

        user_id=user_id,

        endpoint=endpoint,

        amount=str(amount),

        currency=currency,

        reference_id=reference_id,

    )





def _claim_or_validate_idempotency_key(

    db: Session,

    *,

    idempotency_key: str | None,

    user_id: str,

    endpoint: str,

    amount: Decimal,

    currency: str,

    reference_id: str | None = None,

):

    """

    Atomically claim an idempotency key or validate an existing

    key against the current request.



    Returns:

        New request:

            (record, False)



        Existing identical request:

            (record, True)



        Existing different request:

            raises IdempotencyKeyReuseError

    """



    if not idempotency_key:

        return None, False



    request_hash = _build_request_hash(

        user_id=user_id,

        endpoint=endpoint,

        amount=amount,

        currency=currency,

        reference_id=reference_id,

    )



    record, created = claim_idempotency_key(

        db=db,

        key=idempotency_key,

        user_id=user_id,

        endpoint=endpoint,

        request_hash=request_hash,

    )



    if record is None:

        raise RuntimeError(

            "Unable to retrieve idempotency record"

        )



    if created:

        return record, False



    if record.request_hash != request_hash:

        raise IdempotencyKeyReuseError(

            "Idempotency key has already been used "

            "with a different request payload"

        )



    if record.user_id != user_id:

        raise IdempotencyKeyReuseError(

            "Idempotency key belongs to a different user"

        )



    if record.endpoint != endpoint:

        raise IdempotencyKeyReuseError(

            "Idempotency key has already been used "

            "for a different wallet operation"

        )



    return record, True





# ============================================================

# BUDGET ALERT

# ============================================================



def _evaluate_budget_alert_safely(

    db: Session,

    user_id: str,

    currency: str,

) -> None:

    """

    Evaluate the budget alert after a successful wallet

    transaction.



    Budget-alert processing must never change the result of

    an already-committed financial transaction.



    Any transaction automatically opened by the post-commit

    budget-alert queries is explicitly closed before the

    request continues to Kafka publication.

    """



    try:

        check_budget_alert_after_balance_change(

            db=db,

            user_id=user_id,

            currency=currency,

        )



        if db.in_transaction():

            db.commit()



    except Exception:

        if db.in_transaction():

            db.rollback()





def _ensure_wallet_not_paused(balance) -> None:

    """Reject financial operations while a wallet is paused."""



    if bool(getattr(balance, "is_paused", False)):

        reason = getattr(balance, "pause_reason", None)



        if reason:

            raise WalletPaused(

                f"Wallet is paused: {reason}"

            )



        raise WalletPaused("Wallet is paused")





# ============================================================

# DEPOSIT

# ============================================================



@retry_on_serialization_failure

def deposit_money(

    db: Session,

    user_id: str,

    amount: Decimal,

    currency: str = "USD",

    idempotency_key: str | None = None,

    module_source: str | None = None,

):

    """

    Deposit money into a wallet.



    Guarantees:

    - positive amount

    - atomic wallet creation/update

    - row-level wallet locking

    - double-entry ledger

    - idempotency

    - request payload fingerprinting

    - concurrent duplicate protection

    - serialization retry

    - post-commit budget alert evaluation

    """



    if amount <= Decimal("0.00"):

        raise ValueError(

            "Deposit amount must be greater than zero"

        )



    endpoint = "/wallet/deposit"



    try:

        # ----------------------------------------------------

        # STEP 1: Claim / validate idempotency key

        # ----------------------------------------------------



        _, already_processed = (

            _claim_or_validate_idempotency_key(

                db=db,

                idempotency_key=idempotency_key,

                user_id=user_id,

                endpoint=endpoint,

                amount=amount,

                currency=currency,

            )

        )



        if already_processed:

            return read_wallet_balance(

                db,

                user_id,

                currency,

            )



        # ----------------------------------------------------

        # STEP 2: Get/create + lock wallet

        # ----------------------------------------------------



        balance = get_or_create_wallet_balance(

            db=db,

            user_id=user_id,

            currency=currency,

        )



        _ensure_wallet_not_paused(balance)



        # ----------------------------------------------------

        # STEP 3: Update balance

        # ----------------------------------------------------



        balance.available_balance = (

            balance.available_balance + amount

        )



        update_wallet_balance(

            db,

            balance,

        )



        # ----------------------------------------------------

        # STEP 4: Create double-entry ledger transaction

        # ----------------------------------------------------



        ledger = WalletLedger(

            id=uuid4(),

            user_id=user_id,

            transaction_type="DEPOSIT",

            currency=currency,

            amount=amount,

            reference_id=str(uuid4()),

            module_source=module_source,

        )



        create_ledger_entry(

            db,

            ledger,

        )



        # ----------------------------------------------------

        # STEP 5: Commit

        # ----------------------------------------------------



        db.commit()

        db.refresh(balance)



        # ----------------------------------------------------

        # STEP 6: Evaluate budget alert

        # ----------------------------------------------------



        _evaluate_budget_alert_safely(

            db=db,

            user_id=user_id,

            currency=currency,

        )



        # ----------------------------------------------------

        # STEP 7: Publish event

        # ----------------------------------------------------



        try:

            publish_event_sync(

                "wallet.deposited",

                {

                    "user_id": user_id,

                    "amount": str(amount),

                    "currency": currency,

                    "reference_id": ledger.reference_id,

                },

            )

        except Exception:

            pass



        return balance



    except IntegrityError:

        db.rollback()

        raise



    except OperationalError:

        db.rollback()

        raise



    except Exception:

        db.rollback()

        raise





# ============================================================

# WITHDRAW

# ============================================================



@retry_on_serialization_failure

def withdraw_money(

    db: Session,

    user_id: str,

    amount: Decimal,

    currency: str = "USD",

    idempotency_key: str | None = None,

    module_source: str | None = None,

):

    """

    Withdraw money from a wallet.



    Guarantees:

    - positive amount

    - wallet row locking

    - insufficient balance protection

    - double-entry ledger

    - idempotency

    - request payload fingerprinting

    - concurrent duplicate protection

    - serialization retry

    - post-commit budget alert evaluation

    """



    if amount <= Decimal("0.00"):

        raise ValueError(

            "Withdrawal amount must be greater than zero"

        )



    endpoint = "/wallet/withdraw"



    try:

        # ----------------------------------------------------

        # STEP 1: Claim / validate idempotency key

        # ----------------------------------------------------



        _, already_processed = (

            _claim_or_validate_idempotency_key(

                db=db,

                idempotency_key=idempotency_key,

                user_id=user_id,

                endpoint=endpoint,

                amount=amount,

                currency=currency,

            )

        )



        if already_processed:

            return read_wallet_balance(

                db,

                user_id,

                currency,

            )



        # ----------------------------------------------------

        # STEP 2: Get existing wallet + lock row

        # ----------------------------------------------------



        balance = get_wallet_balance(

            db,

            user_id,

            currency,

        )



        if balance is None:

            raise WalletNotFound()



        _ensure_wallet_not_paused(balance)



        # ----------------------------------------------------

        # STEP 3: Check balance

        # ----------------------------------------------------



        if balance.available_balance < amount:

            raise InsufficientBalance()



        # ----------------------------------------------------

        # STEP 4: Update balance

        # ----------------------------------------------------



        balance.available_balance = (

            balance.available_balance - amount

        )



        update_wallet_balance(

            db,

            balance,

        )



        # ----------------------------------------------------

        # STEP 5: Create double-entry ledger transaction

        # ----------------------------------------------------



        ledger = WalletLedger(

            id=uuid4(),

            user_id=user_id,

            transaction_type="WITHDRAW",

            currency=currency,

            amount=amount,

            reference_id=str(uuid4()),

            module_source=module_source,

        )



        create_ledger_entry(

            db,

            ledger,

        )



        # ----------------------------------------------------

        # STEP 6: Commit

        # ----------------------------------------------------



        db.commit()

        db.refresh(balance)



        # ----------------------------------------------------

        # STEP 7: Evaluate budget alert

        # ----------------------------------------------------



        _evaluate_budget_alert_safely(

            db=db,

            user_id=user_id,

            currency=currency,

        )



        # ----------------------------------------------------

        # STEP 8: Publish event

        # ----------------------------------------------------



        try:

            publish_event_sync(

                "wallet.withdrawn",

                {

                    "user_id": user_id,

                    "amount": str(amount),

                    "currency": currency,

                    "reference_id": ledger.reference_id,

                },

            )

        except Exception:

            pass



        return balance



    except IntegrityError:

        db.rollback()

        raise



    except OperationalError:

        db.rollback()

        raise



    except Exception:

        db.rollback()

        raise





# ============================================================

# CREATE WALLET CREDIT

# ============================================================



@retry_on_serialization_failure

def create_credit(

    db: Session,

    user_id: str,

    amount: Decimal,

    currency: str = "USD",

    reference_id: str | None = None,

    idempotency_key: str | None = None,

    module_source: str | None = None,

):

    """

    Create a wallet credit and add the credit amount to the

    user's available wallet balance.



    Each credit is tracked independently through WalletCredit.



    Guarantees:

    - positive amount

    - wallet row locking

    - double-entry ledger

    - idempotency

    - request payload fingerprinting

    - concurrent duplicate protection

    - serialization retry

    - post-commit budget alert evaluation

    """



    if amount <= Decimal("0.00"):

        raise ValueError(

            "Credit amount must be greater than zero"

        )



    endpoint = "/wallet/credit"



    stable_reference_id = (

        reference_id

        or str(uuid4())

    )



    try:

        # ----------------------------------------------------

        # STEP 1: Claim / validate idempotency key

        # ----------------------------------------------------



        _, already_processed = (

            _claim_or_validate_idempotency_key(

                db=db,

                idempotency_key=idempotency_key,

                user_id=user_id,

                endpoint=endpoint,

                amount=amount,

                currency=currency,

                reference_id=stable_reference_id,

            )

        )



        if already_processed:

            credit = (

                db.query(WalletCredit)

                .filter(

                    WalletCredit.user_id == user_id,

                    WalletCredit.currency == currency,

                    WalletCredit.reference_id

                    == stable_reference_id,

                )

                .order_by(

                    WalletCredit.created_at.desc()

                )

                .first()

            )



            if credit is None:

                raise RuntimeError(

                    "Idempotency key exists but the original "

                    "wallet credit could not be found"

                )



            return credit



        # ----------------------------------------------------

        # STEP 2: Get/create + lock wallet

        # ----------------------------------------------------



        balance = get_or_create_wallet_balance(

            db=db,

            user_id=user_id,

            currency=currency,

        )



        _ensure_wallet_not_paused(balance)



        # ----------------------------------------------------

        # STEP 3: Add credit to wallet balance

        # ----------------------------------------------------



        balance.available_balance = (

            balance.available_balance + amount

        )



        update_wallet_balance(

            db=db,

            balance=balance,

        )



        # ----------------------------------------------------

        # STEP 4: Create WalletCredit record

        # ----------------------------------------------------



        credit = WalletCredit(

            id=uuid4(),

            user_id=user_id,

            currency=currency,

            amount=amount,

            remaining_amount=amount,

            reference_id=stable_reference_id,

        )



        create_wallet_credit(

            db=db,

            credit=credit,

        )



        # ----------------------------------------------------

        # STEP 5: Create double-entry ledger transaction

        # ----------------------------------------------------



        ledger = WalletLedger(

            id=uuid4(),

            user_id=user_id,

            transaction_type="CREDIT",

            currency=currency,

            amount=amount,

            reference_id=str(credit.id),

            module_source=module_source,

        )



        create_ledger_entry(

            db=db,

            ledger=ledger,

        )



        # ----------------------------------------------------

        # STEP 6: Commit

        # ----------------------------------------------------



        db.commit()

        db.refresh(credit)



        # ----------------------------------------------------

        # STEP 7: Evaluate budget alert

        # ----------------------------------------------------



        _evaluate_budget_alert_safely(

            db=db,

            user_id=user_id,

            currency=currency,

        )



        # ----------------------------------------------------

        # STEP 8: Publish event

        # ----------------------------------------------------



        try:

            publish_event_sync(

                "wallet.credit_created",

                {

                    "credit_id": str(credit.id),

                    "user_id": user_id,

                    "amount": str(amount),

                    "currency": currency,

                    "reference_id": credit.reference_id,

                    "expires_at": (

                        credit.expires_at.isoformat()

                    ),

                },

            )

        except Exception:

            pass



        return credit



    except IntegrityError:

        db.rollback()

        raise



    except OperationalError:

        db.rollback()

        raise



    except Exception:

        db.rollback()

        raise





# ============================================================

# REFUND FOR NODATA VERDICT

# ============================================================



@retry_on_serialization_failure

def refund_no_data(

    db: Session,

    user_id: str,

    amount: Decimal,

    currency: str = "USD",

    reference_id: str | None = None,

    idempotency_key: str | None = None,

    module_source: str | None = "mod2",

):

    """

    Automatically refund a wallet debit when Module 2 returns

    an inconclusive NoData verdict.



    Guarantees:

    - positive amount

    - reference ID required

    - wallet row locking

    - double-entry ledger

    - idempotency

    - request payload fingerprinting

    - concurrent duplicate protection

    - serialization retry

    - post-commit budget alert evaluation

    """



    if amount <= Decimal("0.00"):

        raise ValueError(

            "Refund amount must be greater than zero"

        )



    if not reference_id:

        raise ValueError(

            "reference_id is required for NoData refund"

        )



    endpoint = "/wallet/refund/no-data"



    try:

        # ----------------------------------------------------

        # STEP 1: Claim / validate idempotency key

        # ----------------------------------------------------



        _, already_processed = (

            _claim_or_validate_idempotency_key(

                db=db,

                idempotency_key=idempotency_key,

                user_id=user_id,

                endpoint=endpoint,

                amount=amount,

                currency=currency,

                reference_id=reference_id,

            )

        )



        if already_processed:

            return read_wallet_balance(

                db,

                user_id,

                currency,

            )



        # ----------------------------------------------------

        # STEP 2: Get/create + lock wallet

        # ----------------------------------------------------



        balance = get_or_create_wallet_balance(

            db=db,

            user_id=user_id,

            currency=currency,

        )



        _ensure_wallet_not_paused(balance)



        # ----------------------------------------------------

        # STEP 3: Add refund

        # ----------------------------------------------------



        balance.available_balance = (

            balance.available_balance + amount

        )



        update_wallet_balance(

            db=db,

            balance=balance,

        )



        # ----------------------------------------------------

        # STEP 4: Create double-entry refund transaction

        # ----------------------------------------------------



        ledger = WalletLedger(

            id=uuid4(),

            user_id=user_id,

            transaction_type="REFUND",

            currency=currency,

            amount=amount,

            reference_id=reference_id,

            module_source=module_source,

        )



        create_ledger_entry(

            db,

            ledger,

        )



        # ----------------------------------------------------

        # STEP 5: Commit

        # ----------------------------------------------------



        db.commit()

        db.refresh(balance)



        # ----------------------------------------------------

        # STEP 6: Evaluate budget alert

        # ----------------------------------------------------



        _evaluate_budget_alert_safely(

            db=db,

            user_id=user_id,

            currency=currency,

        )



        # ----------------------------------------------------

        # STEP 7: Publish event

        # ----------------------------------------------------



        try:

            publish_event_sync(

                "wallet.refunded",

                {

                    "user_id": user_id,

                    "amount": str(amount),

                    "currency": currency,

                    "reference_id": reference_id,

                    "reason": "NoData",

                },

            )

        except Exception:

            pass



        return balance



    except IntegrityError:

        db.rollback()

        raise



    except OperationalError:

        db.rollback()

        raise



    except Exception:

        db.rollback()

        raise





# ============================================================

# GET BALANCE

# ============================================================



def get_balance(
    db: Session,
    user_id: str,
    currency: str = "USD",
):
    """
    Return the current wallet balance for a user.

    This is a read-only operation and therefore does not acquire
    a SELECT ... FOR UPDATE row lock.
    """
    return read_wallet_balance(
        db=db,
        user_id=user_id,
        currency=currency,
    )





# ============================================================

# GET TRANSACTIONS

# ============================================================



def get_wallet_audit_export(

    db: Session,

    user_id: str,

    *,

    date_from=None,

    date_to=None,

    entry_type: str | None = None,

    module_source: str | None = None,

):

    """

    Return the full filtered append-only audit trail for CSV export.

    """



    return get_wallet_audit_export_entries(

        db=db,

        user_id=user_id,

        date_from=date_from,

        date_to=date_to,

        entry_type=entry_type,

        module_source=module_source,

    )





def get_wallet_audit_history(

    db: Session,

    user_id: str,

    *,

    date_from=None,

    date_to=None,

    entry_type: str | None = None,

    module_source: str | None = None,

    limit: int = 100,

    offset: int = 0,

):

    """

    Return the append-only wallet audit trail for a user.



    Supports Week 9 audit filtering and pagination.

    """



    return get_wallet_audit_entries(

        db=db,

        user_id=user_id,

        date_from=date_from,

        date_to=date_to,

        entry_type=entry_type,

        module_source=module_source,

        limit=limit,

        offset=offset,

    )





def get_transactions(

    db: Session,

    user_id: str,

):

    """

    Return all wallet transactions for a user,

    newest first.

    """



    return get_user_transactions(

        db,

        user_id,

    )
