import re

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.api.v1.wallet import get_db
from app.core.exceptions import IdempotencyKeyReuseError
from app.schemas.wallet import BalanceResponse
from app.schemas.wallet_integration import WalletDebitRequest
from app.services.wallet_service import withdraw_money


router = APIRouter(
    prefix="/wallet",
    tags=["Wallet Integration"],
)


MODULE_PATTERNS = {
    "mod1": re.compile(r"^mod1:[^:]+:[^:]+:[^:]+$"),
    "mod2": re.compile(r"^mod2:[^:]+:[^:]+:[^:]+$"),
    "mod3": re.compile(r"^mod3:[^:]+:[^:]+:[^:]+$"),
}


def _resolve_module_source(idempotency_key: str) -> str:
    for module_source, pattern in MODULE_PATTERNS.items():
        if pattern.fullmatch(idempotency_key):
            return module_source

    raise HTTPException(
        status_code=400,
        detail=(
            "Invalid cross-module idempotency key. Expected one of: "
            "mod1:{playbook_hash}:{tenant_id}:{run_id}, "
            "mod2:{rule_hash}:{tenant_id}:{reval_id}, "
            "mod3:{framework}:{tenant_id}:{report_id}"
        ),
    )


@router.post(
    "/debit",
    response_model=BalanceResponse,
)
def debit(
    request: WalletDebitRequest,
    idempotency_key: str = Header(...),
    db: Session = Depends(get_db),
):
    module_source = _resolve_module_source(idempotency_key)

    try:
        return withdraw_money(
            db=db,
            user_id=request.user_id,
            amount=request.amount,
            currency=request.currency,
            idempotency_key=idempotency_key,
            module_source=module_source,
        )

    except IdempotencyKeyReuseError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
