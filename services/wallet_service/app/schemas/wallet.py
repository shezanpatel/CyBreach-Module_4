from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DepositRequest(BaseModel):
    user_id: str
    amount: Decimal
    currency: str = "USD"


class WithdrawRequest(BaseModel):
    user_id: str
    amount: Decimal
    currency: str = "USD"


class CreditRequest(BaseModel):
    user_id: str
    amount: Decimal
    currency: str = "USD"
    reference_id: str | None = None


class BalanceResponse(BaseModel):
    user_id: str
    currency: str
    available_balance: Decimal


class CreditResponse(BaseModel):
    id: UUID
    user_id: str
    currency: str
    amount: Decimal
    remaining_amount: Decimal
    reference_id: str
    created_at: datetime
    expires_at: datetime
    expired_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class TransactionResponse(BaseModel):
    id: UUID
    user_id: str
    transaction_type: str
    currency: str
    amount: Decimal
    reference_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class WalletAuditEntryResponse(BaseModel):
    id: UUID
    transaction_id: UUID
    user_id: str
    transaction_type: str
    currency: str
    entry_type: str
    account_code: str
    amount: Decimal
    reference_id: str
    module_source: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WalletAuditHistoryResponse(BaseModel):
    user_id: str
    total: int
    limit: int
    offset: int
    entries: list[WalletAuditEntryResponse]
