from typing import List

from fastapi import APIRouter, HTTPException

from app.core.database import SessionLocal
from app.repositories.wallet_repository import resume_wallet
from app.schemas.reconciliation import ReconciliationResponse
from app.tasks.scheduler import (
    reconcile_and_handle_wallet,
    run_reconciliation_job,
)


router = APIRouter(
    prefix="/reconciliation",
    tags=["Reconciliation"],
)


@router.get(
    "/run",
    response_model=List[ReconciliationResponse],
)
def run_reconciliation():
    """
    Manually trigger reconciliation for every wallet.

    This executes the same reconciliation -> alert -> pause
    behavior used by the 6-hour scheduler.
    """

    return run_reconciliation_job()


@router.get(
    "/tenant/{tenant_id}",
    response_model=ReconciliationResponse,
)
def reconcile_tenant(
    tenant_id: str,
    currency: str = "USD",
):
    """
    Reconcile one wallet.

    Compatibility note:
    the current Pod Alpha wallet model is keyed by user_id,
    while the reference API uses tenant_id.

    Until Task 10 introduces proper tenant/authentication/
    authorization models, tenant_id is mapped to the existing
    user_id without pretending the identifiers have the same
    security meaning.
    """

    db = SessionLocal()

    try:
        report = reconcile_and_handle_wallet(
            db=db,
            user_id=tenant_id,
            currency=currency,
        )

        db.commit()

        return report

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


@router.post(
    "/unpause/{tenant_id}",
    response_model=ReconciliationResponse,
)
def unpause_tenant(
    tenant_id: str,
    currency: str = "USD",
):
    """
    Explicitly unpause a wallet after operational investigation.

    Compatibility note:
    tenant_id maps to the current user_id until proper
    tenant-aware authorization is implemented in Task 10.
    """

    db = SessionLocal()

    try:
        wallet = resume_wallet(
            db=db,
            user_id=tenant_id,
            currency=currency,
        )

        if wallet is None:
            db.rollback()

            raise HTTPException(
                status_code=404,
                detail="Wallet not found",
            )

        db.commit()

        return {
            "user_id": wallet.user_id,
            "currency": wallet.currency,
            "status": "MATCH",
            "expected_balance": wallet.available_balance,
            "actual_balance": wallet.available_balance,
            "difference": 0,
            "wallet_paused": False,
            "pause_reason": None,
            "paused_at": None,
        }

    except HTTPException:
        raise

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()