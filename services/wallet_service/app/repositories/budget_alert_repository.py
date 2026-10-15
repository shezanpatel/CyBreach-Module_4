from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.budget_alert import BudgetAlert


def create_budget_alert(
    db: Session,
    user_id: str,
    currency: str,
    threshold: Decimal,
    is_enabled: bool = True,
) -> BudgetAlert:
    alert = BudgetAlert(
        user_id=user_id,
        currency=currency.upper(),
        threshold=threshold,
        is_enabled=is_enabled,
    )
    db.add(alert)
    db.flush()
    return alert


def get_budget_alert(
    db: Session,
    user_id: str,
    currency: str,
) -> BudgetAlert | None:
    statement = select(BudgetAlert).where(
        BudgetAlert.user_id == user_id,
        BudgetAlert.currency == currency.upper(),
    )
    return db.execute(statement).scalar_one_or_none()


def list_budget_alerts(
    db: Session,
    user_id: str | None = None,
    currency: str | None = None,
    enabled_only: bool = False,
) -> list[BudgetAlert]:
    statement = select(BudgetAlert)

    if user_id is not None:
        statement = statement.where(BudgetAlert.user_id == user_id)

    if currency is not None:
        statement = statement.where(
            BudgetAlert.currency == currency.upper()
        )

    if enabled_only:
        statement = statement.where(BudgetAlert.is_enabled.is_(True))

    statement = statement.order_by(BudgetAlert.created_at.desc())

    return list(db.execute(statement).scalars().all())


def update_budget_alert(
    db: Session,
    alert: BudgetAlert,
    threshold: Decimal | None = None,
    is_enabled: bool | None = None,
) -> BudgetAlert:
    if threshold is not None:
        alert.threshold = threshold

    if is_enabled is not None:
        alert.is_enabled = is_enabled

    db.flush()
    return alert


def mark_budget_alert_triggered(
    db: Session,
    alert: BudgetAlert,
) -> BudgetAlert:
    from datetime import UTC, datetime

    alert.last_triggered_at = datetime.now(UTC)
    db.flush()
    return alert


def delete_budget_alert(
    db: Session,
    alert: BudgetAlert,
) -> None:
    db.delete(alert)
    db.flush()
