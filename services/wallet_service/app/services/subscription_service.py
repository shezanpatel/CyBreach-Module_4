from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.subscription import Subscription
from app.repositories.subscription_repository import SubscriptionRepository
from app.services.wallet_service import create_credit


class SubscriptionService:
    """
    Handles the Arena subscription lifecycle.

    Monthly subscription allocations:
    - FREE: 5 credits
    - STARTER: 50 credits
    - PROFESSIONAL: 200 credits
    - ENTERPRISE: unlimited

    Paid finite-credit subscriptions are allocated through the
    existing wallet create_credit() operation so that wallet
    balance updates, WalletCredit creation, ledger creation,
    idempotency, locking, and wallet events remain centralized.

    ENTERPRISE is handled separately because "unlimited" is an
    entitlement, not a finite number of wallet credits.

    The current numeric subscriptions.credits_per_period column
    cannot store the literal concept of unlimited, so Decimal("0")
    is used only as a storage sentinel for ENTERPRISE.
    """

    TIER_CREDITS: dict[str, Decimal | None] = {
        "FREE": Decimal("5"),
        "STARTER": Decimal("50"),
        "PROFESSIONAL": Decimal("200"),
        "ENTERPRISE": None,
    }

    PERIOD_DAYS = 30
    CREDIT_EXPIRY_DAYS = 90
    DEFAULT_CURRENCY = "USD"

    VALID_TIERS = {
        "FREE",
        "STARTER",
        "PROFESSIONAL",
        "ENTERPRISE",
    }

    PAID_FINITE_TIERS = {
        "STARTER",
        "PROFESSIONAL",
    }

    def __init__(self, db: Session):
        self.db = db
        self.repository = SubscriptionRepository(db)

    def _validate_tier(self, tier: str) -> str:
        normalized_tier = tier.upper()

        if normalized_tier not in self.VALID_TIERS:
            raise ValueError(
                f"Invalid subscription tier: {tier}. "
                f"Valid tiers are: {', '.join(sorted(self.VALID_TIERS))}"
            )

        return normalized_tier

    def _credits_for_tier(self, tier: str) -> Decimal:
        credits = self.TIER_CREDITS[tier]

        if credits is None:
            return Decimal("0")

        return credits

    def _period_start(self) -> datetime:
        return datetime.now(timezone.utc)

    def _period_end(self, start: datetime) -> datetime:
        return start + timedelta(days=self.PERIOD_DAYS)

    def _allocation_reference(
        self,
        *,
        subscription_id: UUID,
        period_start: datetime,
    ) -> str:
        """
        Stable reference for one subscription billing-period allocation.
        """
        return (
            f"subscription:{subscription_id}:"
            f"{period_start.isoformat()}"
        )

    def _allocate_paid_tier_credits(
        self,
        *,
        subscription: Subscription,
        period_start: datetime,
    ) -> None:
        """
        Allocate a finite paid tier's monthly credits through the
        existing wallet financial transaction path.

        FREE is not processed here because the Week 8 subscription
        requirement specifically describes paid-tier subscription
        allocation.

        ENTERPRISE is not processed here because unlimited access
        cannot be represented as a finite wallet credit amount.
        """
        if subscription.tier not in self.PAID_FINITE_TIERS:
            return

        amount = self._credits_for_tier(subscription.tier)

        reference_id = self._allocation_reference(
            subscription_id=subscription.id,
            period_start=period_start,
        )

        idempotency_key = (
            f"subscription-allocation:"
            f"{subscription.id}:"
            f"{period_start.isoformat()}"
        )

        create_credit(
            db=self.db,
            user_id=subscription.user_id,
            amount=amount,
            currency=self.DEFAULT_CURRENCY,
            reference_id=reference_id,
            idempotency_key=idempotency_key,
            module_source="mod4",
        )

    def signup(
        self,
        *,
        user_id: str,
        tier: str,
    ) -> Subscription:
        tier = self._validate_tier(tier)

        existing = self.repository.get_active_by_user_id(user_id)

        if existing is not None:
            raise ValueError(
                f"User {user_id} already has an active subscription."
            )

        period_start = self._period_start()
        period_end = self._period_end(period_start)

        try:
            subscription = self.repository.create(
                user_id=user_id,
                tier=tier,
                credits_per_period=self._credits_for_tier(tier),
                current_period_start=period_start,
                current_period_end=period_end,
            )

            self._allocate_paid_tier_credits(
                subscription=subscription,
                period_start=period_start,
            )

            # create_credit() commits finite paid-tier allocations.
            # FREE and ENTERPRISE do not call create_credit(), so their
            # subscription records must be committed explicitly.
            if tier not in self.PAID_FINITE_TIERS:
                self.db.commit()

            self.db.refresh(subscription)

            return subscription

        except Exception:
            self.db.rollback()
            raise

    def renew(
        self,
        *,
        user_id: str,
    ) -> Subscription:
        subscription = self.repository.get_active_by_user_id(user_id)

        if subscription is None:
            raise ValueError(
                f"No active subscription found for user {user_id}."
            )

        now = datetime.now(timezone.utc)

        period_start = max(
            subscription.current_period_end,
            now,
        )

        period_end = self._period_end(period_start)

        try:
            subscription.current_period_start = period_start
            subscription.current_period_end = period_end
            subscription.credits_per_period = self._credits_for_tier(
                subscription.tier
            )

            self.repository.update(subscription)

            self._allocate_paid_tier_credits(
                subscription=subscription,
                period_start=period_start,
            )

            if subscription.tier not in self.PAID_FINITE_TIERS:
                self.db.commit()

            self.db.refresh(subscription)

            return subscription

        except Exception:
            self.db.rollback()
            raise

    def cancel(
        self,
        *,
        user_id: str,
    ) -> Subscription:
        subscription = self.repository.get_active_by_user_id(user_id)

        if subscription is None:
            raise ValueError(
                f"No active subscription found for user {user_id}."
            )

        try:
            subscription.status = "CANCELLED"
            subscription.cancelled_at = datetime.now(timezone.utc)

            self.repository.update(subscription)

            # Cancellation deliberately does not alter WalletCredit.
            # Existing credits continue through normal expiry.
            self.db.commit()
            self.db.refresh(subscription)

            return subscription

        except Exception:
            self.db.rollback()
            raise

    def change_tier(
        self,
        *,
        user_id: str,
        tier: str,
    ) -> Subscription:
        tier = self._validate_tier(tier)

        subscription = self.repository.get_active_by_user_id(user_id)

        if subscription is None:
            raise ValueError(
                f"No active subscription found for user {user_id}."
            )

        try:
            subscription.tier = tier
            subscription.credits_per_period = self._credits_for_tier(tier)

            # No immediate prorated allocation is performed here because
            # the Arena Week 8 lifecycle requirement does not define a
            # proration formula for upgrade/downgrade.
            self.repository.update(subscription)

            self.db.commit()
            self.db.refresh(subscription)

            return subscription

        except Exception:
            self.db.rollback()
            raise

    def get_subscription(
        self,
        *,
        user_id: str,
    ) -> Subscription | None:
        return self.repository.get_by_user_id(user_id)

    def get_subscription_by_id(
        self,
        *,
        subscription_id: UUID,
    ) -> Subscription | None:
        return self.repository.get_by_id(subscription_id)
