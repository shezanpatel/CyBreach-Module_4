from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Index, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class BudgetAlert(Base):
    """
    Configurable low-balance alert for a wallet.

    Budget alerts monitor the wallet balance only. They do not
    modify wallet balances or ledger records.
    """

    __tablename__ = "budget_alerts"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    user_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
    )

    threshold: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    last_triggered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "currency",
            name="budget_alerts_unique_wallet",
        ),
        Index(
            "idx_budget_alerts_user_currency",
            "user_id",
            "currency",
        ),
        Index(
            "idx_budget_alerts_enabled",
            "is_enabled",
        ),
    )
