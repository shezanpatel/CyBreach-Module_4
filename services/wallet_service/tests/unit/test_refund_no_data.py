from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.services.wallet_service import (
    _build_request_hash,
    refund_no_data,
)


@patch("app.services.wallet_service.publish_event_sync")
@patch("app.services.wallet_service.claim_idempotency_key")
@patch("app.services.wallet_service.create_ledger_entry")
@patch("app.services.wallet_service.update_wallet_balance")
@patch("app.services.wallet_service.get_or_create_wallet_balance")
def test_refund_no_data(
    mock_get_or_create_wallet_balance,
    mock_update_wallet_balance,
    mock_create_ledger_entry,
    mock_claim_idempotency_key,
    mock_publish_event,
):
    db = MagicMock()

    # ---------------------------------------------------------
    # New atomic idempotency implementation
    # ---------------------------------------------------------

    idempotency_record = MagicMock()

    mock_claim_idempotency_key.return_value = (
        idempotency_record,
        True,
    )

    # ---------------------------------------------------------
    # Existing wallet
    # ---------------------------------------------------------

    wallet = MagicMock()

    wallet.user_id = "test_user"
    wallet.currency = "USD"
    wallet.available_balance = Decimal("100.00")

    # Explicitly represent a normal, active wallet.
    # MagicMock attributes are truthy by default, so without this
    # the wallet pause protection would treat this mock as paused.
    wallet.is_paused = False
    wallet.pause_reason = None

    mock_get_or_create_wallet_balance.return_value = wallet

    # ---------------------------------------------------------
    # Execute refund
    # ---------------------------------------------------------

    result = refund_no_data(
        db=db,
        user_id="test_user",
        amount=Decimal("50.00"),
        currency="USD",
        reference_id="module2-session-123",
        idempotency_key="refund-module2-session-123",
    )

    # ---------------------------------------------------------
    # Verify balance
    # ---------------------------------------------------------

    assert result.available_balance == Decimal("150.00")

    # ---------------------------------------------------------
    # Verify wallet update
    # ---------------------------------------------------------

    mock_update_wallet_balance.assert_called_once_with(
        db=db,
        balance=wallet,
    )

    # ---------------------------------------------------------
    # Verify ledger
    # ---------------------------------------------------------

    mock_create_ledger_entry.assert_called_once()

    ledger = mock_create_ledger_entry.call_args.args[1]

    assert ledger.user_id == "test_user"
    assert ledger.transaction_type == "REFUND"
    assert ledger.currency == "USD"
    assert ledger.amount == Decimal("50.00")
    assert ledger.reference_id == "module2-session-123"

    # ---------------------------------------------------------
    # Verify idempotency claim
    # ---------------------------------------------------------

    mock_claim_idempotency_key.assert_called_once()

    call_kwargs = mock_claim_idempotency_key.call_args.kwargs

    assert (
        call_kwargs["key"]
        == "refund-module2-session-123"
    )

    assert call_kwargs["user_id"] == "test_user"

    assert (
        call_kwargs["endpoint"]
        == "/wallet/refund/no-data"
    )

    assert len(call_kwargs["request_hash"]) == 64

    # ---------------------------------------------------------
    # Verify transaction
    # ---------------------------------------------------------

    db.commit.assert_called_once()


@patch("app.services.wallet_service.read_wallet_balance")
@patch("app.services.wallet_service.claim_idempotency_key")
def test_refund_no_data_is_idempotent(
    mock_claim_idempotency_key,
    mock_read_wallet_balance,
):
    db = MagicMock()

    existing = MagicMock()

    mock_claim_idempotency_key.return_value = (
        existing,
        False,
    )

    # The existing record must match the current request.
    existing.request_hash = _build_request_hash(
        user_id="test_user",
        endpoint="/wallet/refund/no-data",
        amount=Decimal("50.00"),
        currency="USD",
        reference_id="module2-session-123",
    )

    existing.user_id = "test_user"
    existing.endpoint = "/wallet/refund/no-data"

    wallet = MagicMock()
    wallet.available_balance = Decimal("150.00")

    mock_read_wallet_balance.return_value = wallet

    result = refund_no_data(
        db=db,
        user_id="test_user",
        amount=Decimal("50.00"),
        currency="USD",
        reference_id="module2-session-123",
        idempotency_key="refund-module2-session-123",
    )

    assert result.available_balance == Decimal("150.00")

    mock_read_wallet_balance.assert_called_once_with(
        db,
        "test_user",
        "USD",
    )

    db.commit.assert_not_called()


def test_refund_no_data_requires_reference_id():
    db = MagicMock()

    with pytest.raises(
        ValueError,
        match="reference_id is required for NoData refund",
    ):
        refund_no_data(
            db=db,
            user_id="test_user",
            amount=Decimal("50.00"),
            currency="USD",
            reference_id=None,
            idempotency_key="refund-test",
        )