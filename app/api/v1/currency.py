 
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.currency_repository import (
    create_currency_rate,
    list_currency_rates,
)
from app.schemas.currency import (
    CurrencyConversionRequest,
    CurrencyConversionResponse,
    CurrencyRateCreate,
    CurrencyRateResponse,
)
from app.services.currency_service import (
    CurrencyRateNotFoundError,
    convert_currency,
    get_conversion_rate,
)

router = APIRouter(
    prefix="/currency",
    tags=["Currency"],
)


@router.post(
    "/rates",
    response_model=CurrencyRateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_rate(
    payload: CurrencyRateCreate,
    db: Session = Depends(get_db),
):
    effective_at = payload.effective_at or datetime.now(UTC)

    if payload.base_currency == payload.target_currency:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Base and target currencies must be different",
        )

    try:
        currency_rate = create_currency_rate(
            db=db,
            base_currency=payload.base_currency,
            target_currency=payload.target_currency,
            rate=payload.rate,
            effective_at=effective_at,
        )
        db.commit()
        db.refresh(currency_rate)
        return currency_rate
    except Exception:
        db.rollback()
        raise


@router.get(
    "/rates",
    response_model=list[CurrencyRateResponse],
)
def get_rates(
    base_currency: str | None = None,
    target_currency: str | None = None,
    db: Session = Depends(get_db),
):
    return list_currency_rates(
        db=db,
        base_currency=base_currency,
        target_currency=target_currency,
    )


@router.post(
    "/convert",
    response_model=CurrencyConversionResponse,
)
def convert(
    payload: CurrencyConversionRequest,
    db: Session = Depends(get_db),
):
    if payload.base_currency == payload.target_currency:
        return CurrencyConversionResponse(
            amount=payload.amount,
            base_currency=payload.base_currency,
            target_currency=payload.target_currency,
            converted_amount=payload.amount,
            rate=1,
            effective_at=payload.effective_at,
        )

    try:
        converted_amount = convert_currency(
            db=db,
            amount=payload.amount,
            base_currency=payload.base_currency,
            target_currency=payload.target_currency,
            effective_at=payload.effective_at,
        )

        rate = get_conversion_rate(
            db=db,
            base_currency=payload.base_currency,
            target_currency=payload.target_currency,
            effective_at=payload.effective_at,
        )

        return CurrencyConversionResponse(
            amount=payload.amount,
            base_currency=payload.base_currency,
            target_currency=payload.target_currency,
            converted_amount=converted_amount,
            rate=rate,
            effective_at=payload.effective_at,
        )

    except CurrencyRateNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc