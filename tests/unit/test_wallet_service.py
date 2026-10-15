from decimal import Decimal
from unittest.mock import MagicMock, patch

from app.services.wallet_service import deposit_money


@patch("app.services.wallet_service.publish_event_sync")
@patch("app.services.wallet_service.claim_idempotency_key")
@patch("app.services.wallet_service.create_ledger_entry")
@patch("app.services.wallet_service.update_wallet_balance")
@patch("app.services.wallet_service.get_or_create_wallet_balance")
def test_deposit_money(
    mock_get_or_create_wallet_balance,
    mock_update_wallet_balance,
    mock_create_ledger_entry,
    mock_claim_idempotency_key,
    mock_publish_event,
):
    # ---------------------------------------------------------
    # Mock database
    # ---------------------------------------------------------

    db = MagicMock()

    # ---------------------------------------------------------
    # New idempotency implementation
    # ---------------------------------------------------------

    idempotency_record = MagicMock()
    idempotency_record.request_hash = "test-hash"
    idempotency_record.user_id = "test_user"
    idempotency_record.endpoint = "/wallet/deposit"

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
    # Execute deposit
    # ---------------------------------------------------------

    result = deposit_money(
        db=db,
        user_id="test_user",
        amount=Decimal("50"),
        currency="USD",
        idempotency_key="test-key",
    )

    # ---------------------------------------------------------
    # Verify balance
    # ---------------------------------------------------------

    assert result.available_balance == Decimal("150.00")

    # ---------------------------------------------------------
    # Verify repository calls
    # ---------------------------------------------------------

    mock_get_or_create_wallet_balance.assert_called_once_with(
        db=db,
        user_id="test_user",
        currency="USD",
    )

    mock_update_wallet_balance.assert_called_once()

    mock_create_ledger_entry.assert_called_once()

    mock_claim_idempotency_key.assert_called_once()

    # ---------------------------------------------------------
    # Verify idempotency payload
    # ---------------------------------------------------------

    call_kwargs = mock_claim_idempotency_key.call_args.kwargs

    assert call_kwargs["key"] == "test-key"
    assert call_kwargs["user_id"] == "test_user"
    assert call_kwargs["endpoint"] == "/wallet/deposit"

    assert len(call_kwargs["request_hash"]) == 64

    # ---------------------------------------------------------
    # Verify database transaction
    # ---------------------------------------------------------

    db.commit.assert_called_once()