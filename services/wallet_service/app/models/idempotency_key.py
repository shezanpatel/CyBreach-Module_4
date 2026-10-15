from datetime import UTC, datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class IdempotencyKey(Base):
    """
    Stores the identity of a previously processed wallet request.

    The request_hash is calculated from the immutable request
    parameters. Reusing the same idempotency key with different
    request parameters must therefore be rejected.
    """

    __tablename__ = "idempotency_keys"

    key: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
    )

    user_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    endpoint: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    request_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    response_data: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )