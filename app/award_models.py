from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel
from sqlalchemy import DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class BadgeAward(BaseModel):
    award_id: str
    badge_id: str
    tenant_id: str
    awarded_at: datetime
    evidence_ref: str | None = None


class BadgeAwardDB(Base):
    __tablename__ = "badge_award"

    award_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    badge_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    tenant_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    awarded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    evidence_ref: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "badge_id",
            "tenant_id",
            name="uq_badge_award_badge_tenant",
        ),
    )