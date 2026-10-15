from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BudgetAlertCreate(BaseModel):
    user_id: str = Field(min_length=1, max_length=100)
    currency: str = Field(min_length=3, max_length=3)
    threshold: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
    is_enabled: bool = True

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class BudgetAlertUpdate(BaseModel):
    threshold: Decimal | None = Field(
        default=None,
        ge=0,
    )
    is_enabled: bool | None = None


class BudgetAlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    currency: str
    threshold: Decimal
    is_enabled: bool
    last_triggered_at: datetime | None
    created_at: datetime
    updated_at: datetime


class BudgetAlertCheckResponse(BaseModel):
    user_id: str
    currency: str
    balance: Decimal
    threshold: Decimal
    is_below_threshold: bool
    notification_sent: bool
