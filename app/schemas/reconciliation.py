from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class ReconciliationResponse(BaseModel):
    user_id: str
    currency: str
    status: str
    expected_balance: Decimal
    actual_balance: Decimal
    difference: Decimal
    wallet_paused: bool = False
    ledger_mode: str | None = None
    pause_reason: str | None = None
    paused_at: datetime | None = None