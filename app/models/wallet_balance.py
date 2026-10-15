from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class WalletBalance(Base):
    """
    Current balance and operational safety state for a wallet.

    A wallet can be paused when reconciliation detects a
    financial-integrity mismatch.

    Paused wallets must not perform financial operations until
    the pause is explicitly cleared.
    """

    __tablename__ = "wallet_balance"

    user_id: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        primary_key=True,
        default="USD",
    )

    available_balance: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # ========================================================
    # RECONCILIATION SAFETY STATE
    # ========================================================

    is_paused: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    pause_reason: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    paused_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )