from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.schemas.subscription import (
    SubscriptionSignupRequest,
    SubscriptionRenewRequest,
    SubscriptionCancelRequest,
    SubscriptionChangeTierRequest,
    SubscriptionResponse,
)
from app.services.subscription_service import SubscriptionService


router = APIRouter(
    prefix="/subscription",
    tags=["Subscription"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "/signup",
    response_model=SubscriptionResponse,
)
def signup(
    request: SubscriptionSignupRequest,
    db: Session = Depends(get_db),
):
    service = SubscriptionService(db)

    try:
        subscription = service.signup(
            user_id=request.user_id,
            tier=request.tier,
        )
        return subscription
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


@router.post(
    "/renew",
    response_model=SubscriptionResponse,
)
def renew(
    request: SubscriptionRenewRequest,
    db: Session = Depends(get_db),
):
    service = SubscriptionService(db)

    try:
        subscription = service.renew(
            user_id=request.user_id,
        )
        return subscription
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


@router.post(
    "/cancel",
    response_model=SubscriptionResponse,
)
def cancel(
    request: SubscriptionCancelRequest,
    db: Session = Depends(get_db),
):
    service = SubscriptionService(db)

    try:
        subscription = service.cancel(
            user_id=request.user_id,
        )
        return subscription
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


@router.post(
    "/change-tier",
    response_model=SubscriptionResponse,
)
def change_tier(
    request: SubscriptionChangeTierRequest,
    db: Session = Depends(get_db),
):
    service = SubscriptionService(db)

    try:
        subscription = service.change_tier(
            user_id=request.user_id,
            tier=request.tier,
        )
        return subscription
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )