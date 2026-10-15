from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.subscription import Subscription


class SubscriptionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_user_id(self, user_id: str) -> Subscription | None:
        stmt = (
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .order_by(Subscription.created_at.desc())
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_active_by_user_id(self, user_id: str) -> Subscription | None:
        stmt = (
            select(Subscription)
            .where(
                Subscription.user_id == user_id,
                Subscription.status == "ACTIVE",
            )
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_id(self, subscription_id: UUID) -> Subscription | None:
        stmt = select(Subscription).where(
            Subscription.id == subscription_id
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def create(
        self,
        *,
        user_id: str,
        tier: str,
        credits_per_period,
        current_period_start: datetime,
        current_period_end: datetime,
    ) -> Subscription:
        subscription = Subscription(
            user_id=user_id,
            tier=tier,
            status="ACTIVE",
            credits_per_period=credits_per_period,
            current_period_start=current_period_start,
            current_period_end=current_period_end,
        )

        self.db.add(subscription)
        self.db.flush()

        return subscription

    def update(self, subscription: Subscription) -> Subscription:
        self.db.add(subscription)
        self.db.flush()
        return subscription