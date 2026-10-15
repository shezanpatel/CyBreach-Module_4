from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Numeric, String
from sqlalchemy import UUID as SQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class WalletLedger(Base):
    """
    Wallet transaction header.

    This table represents the transaction itself.
    The actual accounting movement is stored in
    wallet_ledger_entries as a DEBIT/CREDIT pair.

    Week 9 audit metadata:
        module_source identifies the CyBreach module or
        internal subsystem responsible for the transaction.

    Ledger rows are append-only at the PostgreSQL level.
    Existing historical rows may have module_source=NULL
    because they predate audit-source tracking.
    """

    __tablename__ = "wallet_ledger"

    id: Mapped[UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
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
        default="USD",
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