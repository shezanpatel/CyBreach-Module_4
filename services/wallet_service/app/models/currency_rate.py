from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Numeric, String, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CurrencyRate(Base):
    """
    Configured currency conversion rate used by the display layer.

    Wallet balances and wallet ledger amounts remain the internal
    source of truth. CurrencyRate is only used to convert those
    amounts for display.
    """

    __tablename__ = "currency_rates"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    base_currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
    )

    target_currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
    )

    rate: Mapped[Decimal] = mapped_column(
        Numeric(20, 8),
        nullable=False,
    )

    effective_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
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
    )

    __table_args__ = (
        UniqueConstraint(
            "base_currency",
            "target_currency",
            "effective_at",
            name="currency_rates_unique_effective_rate",
        ),
        Index(
            "idx_currency_rates_lookup",
            "base_currency",
            "target_currency",
            "effective_at",
        ),
    )