from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class UserProfileDB(Base):
    __tablename__ = "user_profile"

    user_id: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
    )

    tenant_id: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
        default="default",
    )

    current_streak: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )

    last_completion_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    verified_activity_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )