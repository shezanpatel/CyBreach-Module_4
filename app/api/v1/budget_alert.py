from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.budget_alert import (
    BudgetAlertCheckResponse,
    BudgetAlertCreate,
    BudgetAlertResponse,
    BudgetAlertUpdate,
)
from app.services.budget_alert_service import (
    check_budget_alert,
    configure_budget_alert,
    get_configured_budget_alert,
    update_configured_budget_alert,
)

router = APIRouter(
    prefix="/budget-alert",
    tags=["Budget Alerts"],
)


@router.post(
    "",
    response_model=BudgetAlertResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_or_configure_alert(
    payload: BudgetAlertCreate,
    db: Session = Depends(get_db),
):
    try:
        return configure_budget_alert(
            db=db,
            user_id=payload.user_id,
            currency=payload.currency,
            threshold=payload.threshold,
            is_enabled=payload.is_enabled,
        )
    except Exception:
        db.rollback()
        raise


@router.get(
    "/{user_id}/{currency}",
    response_model=BudgetAlertResponse,
)
def get_alert(
    user_id: str,
    currency: str,
    db: Session = Depends(get_db),
):
    alert = get_configured_budget_alert(
        db=db,
        user_id=user_id,
        currency=currency.upper(),
    )

    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget alert does not exist",
        )

    return alert


@router.put(
    "/{user_id}/{currency}",
    response_model=BudgetAlertResponse,
)
def update_alert(
    user_id: str,
    currency: str,
    payload: BudgetAlertUpdate,
    db: Session = Depends(get_db),
):
    if payload.threshold is None and payload.is_enabled is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided for update",
        )

    try:
        alert = update_configured_budget_alert(
            db=db,
            user_id=user_id,
            currency=currency.upper(),
            threshold=payload.threshold,
            is_enabled=payload.is_enabled,
        )
    except Exception:
        db.rollback()
        raise

    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget alert does not exist",
        )

    return alert


@router.post(
    "/{user_id}/{currency}/check",
    response_model=BudgetAlertCheckResponse,
)
def evaluate_alert(
    user_id: str,
    currency: str,
    db: Session = Depends(get_db),
):
    try:
        return check_budget_alert(
            db=db,
            user_id=user_id,
            currency=currency.upper(),
        )
    except Exception:
        db.rollback()
        raise
