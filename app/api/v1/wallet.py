import csv
import io
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.exceptions import IdempotencyKeyReuseError
from app.schemas.wallet import (
    BalanceResponse,
    CreditRequest,
    CreditResponse,
    DepositRequest,
    TransactionResponse,
    WalletAuditHistoryResponse,
    WithdrawRequest,
)
from app.services.wallet_service import (
    create_credit,
    deposit_money,
    get_balance,
    get_transactions,
    get_wallet_audit_export,
    get_wallet_audit_history,
    withdraw_money,
)


router = APIRouter(
    prefix="/wallet",
    tags=["Wallet"],
)


def get_db():
    """
    Create one database session for each wallet API request.

    Any transaction still active when request processing
    finishes is rolled back before the session is closed.
    This prevents read-only or post-commit transactions from
    remaining idle in PostgreSQL under high concurrency.
    """
    db = SessionLocal()

    try:
        yield db

    finally:
        try:
            if db.in_transaction():
                db.rollback()

        finally:
            db.close()


# =========================================================
# DEPOSIT
# =========================================================

@router.post(
    "/deposit",
    response_model=BalanceResponse,
)
def deposit(
    request: DepositRequest,
    idempotency_key: str = Header(...),
    db: Session = Depends(get_db),
):
    try:
        balance = deposit_money(
            db=db,
            user_id=request.user_id,
            amount=request.amount,
            currency=request.currency,
            idempotency_key=idempotency_key,
        )

        return balance

    except IdempotencyKeyReuseError as e:
        raise HTTPException(
            status_code=409,
            detail=str(e),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


# =========================================================
# WITHDRAW
# =========================================================

@router.post(
    "/withdraw",
    response_model=BalanceResponse,
)
def withdraw(
    request: WithdrawRequest,
    idempotency_key: str = Header(...),
    db: Session = Depends(get_db),
):
    try:
        balance = withdraw_money(
            db=db,
            user_id=request.user_id,
            amount=request.amount,
            currency=request.currency,
            idempotency_key=idempotency_key,
        )

        return balance

    except IdempotencyKeyReuseError as e:
        raise HTTPException(
            status_code=409,
            detail=str(e),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


# =========================================================
# CREDIT
# =========================================================

@router.post(
    "/credit",
    response_model=CreditResponse,
)
def credit(
    request: CreditRequest,
    idempotency_key: str = Header(...),
    db: Session = Depends(get_db),
):
    try:
        return create_credit(
            db=db,
            user_id=request.user_id,
            amount=request.amount,
            currency=request.currency,
            reference_id=request.reference_id,
            idempotency_key=idempotency_key,
        )

    except IdempotencyKeyReuseError as e:
        raise HTTPException(
            status_code=409,
            detail=str(e),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


# =========================================================
# BALANCE
# =========================================================

@router.get(
    "/balance/{user_id}",
    response_model=BalanceResponse,
)
def balance(
    user_id: str,
    currency: str = "USD",
    db: Session = Depends(get_db),
):
    wallet = get_balance(
        db,
        user_id,
        currency,
    )

    if wallet is None:
        raise HTTPException(
            status_code=404,
            detail="Wallet not found",
        )

    return wallet


# =========================================================
# AUDIT HISTORY
# =========================================================

@router.get(
    "/history/{user_id}",
    response_model=WalletAuditHistoryResponse,
)
def wallet_history(
    user_id: str,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    entry_type: str | None = None,
    module_source: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    try:
        entries, total = get_wallet_audit_history(
            db=db,
            user_id=user_id,
            date_from=date_from,
            date_to=date_to,
            entry_type=entry_type,
            module_source=module_source,
            limit=limit,
            offset=offset,
        )

        return WalletAuditHistoryResponse(
            user_id=user_id,
            total=total,
            limit=limit,
            offset=offset,
            entries=entries,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


# =========================================================
# AUDIT CSV EXPORT
# =========================================================

@router.get("/history/{user_id}/export")
def wallet_history_export(
    user_id: str,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    entry_type: str | None = None,
    module_source: str | None = None,
    db: Session = Depends(get_db),
):
    try:
        entries = get_wallet_audit_export(
            db=db,
            user_id=user_id,
            date_from=date_from,
            date_to=date_to,
            entry_type=entry_type,
            module_source=module_source,
        )

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "id",
            "transaction_id",
            "user_id",
            "transaction_type",
            "currency",
            "entry_type",
            "account_code",
            "amount",
            "reference_id",
            "module_source",
            "created_at",
        ])

        for entry in entries:
            writer.writerow([
                entry.id,
                entry.transaction_id,
                entry.user_id,
                entry.transaction_type,
                entry.currency,
                entry.entry_type,
                entry.account_code,
                entry.amount,
                entry.reference_id,
                entry.module_source or "",
                entry.created_at.isoformat(),
            ])

        output.seek(0)

        filename = f"wallet-audit-{user_id}.csv"

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition":
                    f'attachment; filename="{filename}"'
            },
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


# =========================================================
# TRANSACTIONS
# =========================================================

@router.get(
    "/transactions/{user_id}",
    response_model=List[TransactionResponse],
)
def transactions(
    user_id: str,
    db: Session = Depends(get_db),
):
    return get_transactions(
        db,
        user_id,
    )