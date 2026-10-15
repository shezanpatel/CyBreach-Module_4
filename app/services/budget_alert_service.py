from decimal import Decimal

from sqlalchemy.orm import Session

from app.events.kafka_producer import publish_event_sync
from app.repositories.budget_alert_repository import (
    create_budget_alert,
    get_budget_alert,
    mark_budget_alert_triggered,
    update_budget_alert,
)
from app.repositories.wallet_repository import get_wallet_balance


# ============================================================
# CONFIGURE BUDGET ALERT
# ============================================================

def configure_budget_alert(
    db: Session,
    user_id: str,
    currency: str,
    threshold: Decimal,
    is_enabled: bool = True,
):
    """
    Create or update the budget alert for a wallet.

    A wallet can have one configurable alert per currency.
    This function does not modify the wallet balance or ledger.
    """

    currency = currency.upper()

    existing_alert = get_budget_alert(
        db=db,
        user_id=user_id,
        currency=currency,
    )

    if existing_alert is not None:
        alert = update_budget_alert(
            db=db,
            alert=existing_alert,
            threshold=threshold,
            is_enabled=is_enabled,
        )
    else:
        alert = create_budget_alert(
            db=db,
            user_id=user_id,
            currency=currency,
            threshold=threshold,
            is_enabled=is_enabled,
        )

    db.commit()
    db.refresh(alert)

    return alert


# ============================================================
# GET CONFIGURED BUDGET ALERT
# ============================================================

def get_configured_budget_alert(
    db: Session,
    user_id: str,
    currency: str,
):
    """
    Return the configured budget alert for a wallet.
    """

    return get_budget_alert(
        db=db,
        user_id=user_id,
        currency=currency.upper(),
    )


# ============================================================
# UPDATE CONFIGURED BUDGET ALERT
# ============================================================

def update_configured_budget_alert(
    db: Session,
    user_id: str,
    currency: str,
    threshold: Decimal | None = None,
    is_enabled: bool | None = None,
):
    """
    Update an existing budget alert.

    The caller must configure at least one field to update.
    """

    alert = get_budget_alert(
        db=db,
        user_id=user_id,
        currency=currency.upper(),
    )

    if alert is None:
        return None

    update_budget_alert(
        db=db,
        alert=alert,
        threshold=threshold,
        is_enabled=is_enabled,
    )

    db.commit()
    db.refresh(alert)

    return alert


# ============================================================
# PUBLISH BUDGET ALERT EVENT
# ============================================================

def _publish_budget_alert_event(
    user_id: str,
    currency: str,
    balance: Decimal,
    threshold: Decimal,
) -> bool:
    """
    Publish a low-balance notification event.

    Kafka/Notification Hub failures must not break the wallet
    transaction or budget-alert evaluation.

    Uses the shared sync-to-async Kafka bridge so the global
    AIOKafkaProducer remains on the FastAPI lifespan event loop.
    """

    try:
        publish_event_sync(
            "wallet.budget_alert",
            {
                "user_id": user_id,
                "currency": currency,
                "balance": str(balance),
                "threshold": str(threshold),
                "alert_type": "LOW_BALANCE",
            },
        )

        return True

    except Exception:
        return False


# ============================================================
# CHECK BUDGET ALERT
# ============================================================

def check_budget_alert(
    db: Session,
    user_id: str,
    currency: str,
):
    """
    Check the wallet balance against its configured threshold.

    A notification is generated only when:
      - the alert exists,
      - the alert is enabled,
      - the wallet exists,
      - the balance is at or below the threshold,
      - and the alert has not already been triggered.

    This prevents repeated notification events while a wallet
    remains below the configured threshold.
    """

    currency = currency.upper()

    alert = get_budget_alert(
        db=db,
        user_id=user_id,
        currency=currency,
    )

    wallet = get_wallet_balance(
        db=db,
        user_id=user_id,
        currency=currency,
    )

    balance = (
        wallet.available_balance
        if wallet is not None
        else Decimal("0.00")
    )

    if alert is None:
        return {
            "user_id": user_id,
            "currency": currency,
            "balance": balance,
            "threshold": Decimal("0.00"),
            "is_below_threshold": False,
            "notification_sent": False,
        }

    is_below_threshold = balance <= alert.threshold

    notification_sent = False

    if (
        alert.is_enabled
        and is_below_threshold
        and alert.last_triggered_at is None
    ):
        notification_sent = _publish_budget_alert_event(
            user_id=user_id,
            currency=currency,
            balance=balance,
            threshold=alert.threshold,
        )

        if notification_sent:
            mark_budget_alert_triggered(
                db=db,
                alert=alert,
            )

            db.commit()

    return {
        "user_id": user_id,
        "currency": currency,
        "balance": balance,
        "threshold": alert.threshold,
        "is_below_threshold": is_below_threshold,
        "notification_sent": notification_sent,
    }


# ============================================================
# POST-BALANCE-CHANGE CHECK
# ============================================================

def check_budget_alert_after_balance_change(
    db: Session,
    user_id: str,
    currency: str,
):
    """
    Evaluate a budget alert after a wallet balance change.

    This is intended to be called after a successful financial
    operation has committed its wallet balance update.
    """

    return check_budget_alert(
        db=db,
        user_id=user_id,
        currency=currency,
    )