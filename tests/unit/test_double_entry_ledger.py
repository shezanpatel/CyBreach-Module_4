from decimal import Decimal
from uuid import uuid4

from app.models.wallet_ledger import WalletLedger
from app.models.wallet_ledger_entry import WalletLedgerEntry
from app.repositories.wallet_repository import (
    LEDGER_ACCOUNT_MAPPING,
    create_double_entry,
)


def test_deposit_creates_balanced_double_entry():
    db = type(
        "MockDB",
        (),
        {
            "add_all": lambda self, entries: None,
            "flush": lambda self: None,
        },
    )()

    transaction_id = uuid4()

    ledger = WalletLedger(
        id=transaction_id,
        user_id="test-user",
        transaction_type="DEPOSIT",
        currency="USD",
        amount=Decimal("100.00"),
        reference_id="deposit-test",
    )

    debit, credit = create_double_entry(
        db=db,
        ledger=ledger,
    )

    assert isinstance(
        debit,
        WalletLedgerEntry,
    )

    assert isinstance(
        credit,
        WalletLedgerEntry,
    )

    assert debit.transaction_id == transaction_id
    assert credit.transaction_id == transaction_id

    assert debit.entry_type == "DEBIT"
    assert credit.entry_type == "CREDIT"

    assert debit.amount == Decimal("100.00")
    assert credit.amount == Decimal("100.00")

    assert debit.currency == "USD"
    assert credit.currency == "USD"

    assert debit.account_code == "CASH"
    assert credit.account_code == "WALLET"


def test_all_supported_transaction_types_have_double_entry_mapping():
    expected_types = {
        "DEPOSIT",
        "WITHDRAW",
        "CREDIT",
        "REFUND",
        "CREDIT_EXPIRY",
    }

    assert set(
        LEDGER_ACCOUNT_MAPPING.keys()
    ) == expected_types


def test_withdraw_uses_wallet_to_cash_direction():
    mapping = LEDGER_ACCOUNT_MAPPING["WITHDRAW"]

    assert mapping["debit"] == "WALLET"
    assert mapping["credit"] == "CASH"


def test_credit_uses_credit_source_to_wallet_direction():
    mapping = LEDGER_ACCOUNT_MAPPING["CREDIT"]

    assert mapping["debit"] == "CREDIT_SOURCE"
    assert mapping["credit"] == "WALLET"


def test_refund_uses_expense_to_wallet_direction():
    mapping = LEDGER_ACCOUNT_MAPPING["REFUND"]

    assert mapping["debit"] == "REFUND_EXPENSE"
    assert mapping["credit"] == "WALLET"


def test_credit_expiry_uses_wallet_to_expiry_revenue_direction():
    mapping = LEDGER_ACCOUNT_MAPPING["CREDIT_EXPIRY"]

    assert mapping["debit"] == "WALLET"
    assert mapping["credit"] == "CREDIT_EXPIRY_REVENUE"