from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SubscriptionSignupRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=255)
    tier: str = Field(..., min_length=1, max_length=50)


class SubscriptionRenewRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=255)


class SubscriptionCancelRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=255)


class SubscriptionChangeTierRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=255)
    tier: str = Field(..., min_length=1, max_length=50)


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: str
    tier: str
    status: str
    credits_per_period: Decimal
    current_period_start: datetime
    current_period_end: datetime
    cancelled_at: datetime | None
    created_at: datetime
    updated_at: datetime