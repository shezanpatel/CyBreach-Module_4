from decimal import Decimal

from pydantic import BaseModel


class WalletDebitRequest(BaseModel):
    user_id: str
    amount: Decimal
    currency: str = "USD"
