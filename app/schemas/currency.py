from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CurrencyRateCreate(BaseModel):
    base_currency: str = Field(min_length=3, max_length=3)
    target_currency: str = Field(min_length=3, max_length=3)
    rate: Decimal = Field(gt=0, max_digits=20, decimal_places=8)
    effective_at: datetime | None = None

    @field_validator("base_currency", "target_currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class CurrencyRateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    base_currency: str
    target_currency: str
    rate: Decimal
    effective_at: datetime
    created_at: datetime
    updated_at: datetime


class CurrencyConversionRequest(BaseModel):
    amount: Decimal = Field(ge=0)
    base_currency: str = Field(min_length=3, max_length=3)
    target_currency: str = Field(min_length=3, max_length=3)
    effective_at: datetime | None = None

    @field_validator("base_currency", "target_currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class CurrencyConversionResponse(BaseModel):
    amount: Decimal
    base_currency: str
    target_currency: str
    converted_amount: Decimal
    rate: Decimal
    effective_at: datetime | None