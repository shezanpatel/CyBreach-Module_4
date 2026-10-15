from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    UUID as SQLUUID,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class WalletLedgerEntry(Base):
    """
    Individual accounting entry belonging to a wallet
    ledger transaction.

    Every wallet transaction must contain exactly:

        1 DEBIT
        1 CREDIT

    The two entries share the same transaction_id,
    currency, amount, and module_source.

    Ledger entries are append-only at the PostgreSQL level.
    Existing historical entries may have module_source=NULL
    because they predate audit-source tracking.
    """

    __tablename__ = "wallet_ledger_entries"

    id: Mapped[UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    transaction_id: Mapped[UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey(
            "wallet_ledger.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    user_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    transaction_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
    )

    entry_type: Mapped[str] = mapped_column(
        String(6),
        nullable=False,
    )

    account_code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    reference_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    module_source: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "transaction_id",
            "entry_type",
            name="uq_wallet_ledger_entry_transaction_type",
        ),
        CheckConstraint(
            "entry_type IN ('DEBIT', 'CREDIT')",
            name="ck_wallet_ledger_entry_type",
        ),
        CheckConstraint(
            "amount > 0",
            name="ck_wallet_ledger_entry_amount_positive",
        ),
    )