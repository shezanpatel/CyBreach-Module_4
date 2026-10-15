from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import IdempotencyKeyReuseError
from app.services.wallet_service import (
    _claim_or_validate_idempotency_key,
    _build_request_hash,
)


def _existing_record(
    *,
    user_id="test_user",
    endpoint="/wallet/deposit",
    amount=Decimal("50.00"),
    currency="USD",
    reference_id=None,
):
    record = MagicMock()

    record.request_hash = _build_request_hash(
        user_id=user_id,
        endpoint=endpoint,
        amount=amount,
        currency=currency,
        reference_id=reference_id,
    )

    record.user_id = user_id
    record.endpoint = endpoint

    return record


@patch("app.services.wallet_service.claim_idempotency_key")
def test_same_key_same_payload_is_idempotent(
    mock_claim_idempotency_key,
):
    db = MagicMock()

    record = _existing_record()

    mock_claim_idempotency_key.return_value = (
        record,
        False,
    )

    result_record, already_processed = (
        _claim_or_validate_idempotency_key(
            db=db,
            idempotency_key="test-key",
            user_id="test_user",
            endpoint="/wallet/deposit",
            amount=Decimal("50.00"),
            currency="USD",
            reference_id=None,
        )
    )

    assert result_record is record
    assert already_processed is True


@patch("app.services.wallet_service.claim_idempotency_key")
def test_same_key_different_amount_is_rejected(
    mock_claim_idempotency_key,
):
    db = MagicMock()

    record = _existing_record(
        amount=Decimal("50.00"),
    )

    mock_claim_idempotency_key.return_value = (
        record,
        False,
    )

    with pytest.raises(
        IdempotencyKeyReuseError,
        match="different request payload",
    ):
        _claim_or_validate_idempotency_key(
            db=db,
            idempotency_key="test-key",
            user_id="test_user",
            endpoint="/wallet/deposit",
            amount=Decimal("75.00"),
            currency="USD",
            reference_id=None,
        )


@patch("app.services.wallet_service.claim_idempotency_key")
def test_same_key_different_currency_is_rejected(
    mock_claim_idempotency_key,
):
    db = MagicMock()

    record = _existing_record(
        currency="USD",
    )

    mock_claim_idempotency_key.return_value = (
        record,
        False,
    )

    with pytest.raises(
        IdempotencyKeyReuseError,
        match="different request payload",
    ):
        _claim_or_validate_idempotency_key(
            db=db,
            idempotency_key="test-key",
            user_id="test_user",
            endpoint="/wallet/deposit",
            amount=Decimal("50.00"),
            currency="EUR",
            reference_id=None,
        )


@patch("app.services.wallet_service.claim_idempotency_key")
def test_same_key_different_user_is_rejected(
    mock_claim_idempotency_key,
):
    db = MagicMock()

    record = _existing_record(
        user_id="user_a",
    )

    mock_claim_idempotency_key.return_value = (
        record,
        False,
    )

    with pytest.raises(
        IdempotencyKeyReuseError,
    ):
        _claim_or_validate_idempotency_key(
            db=db,
            idempotency_key="test-key",
            user_id="user_b",
            endpoint="/wallet/deposit",
            amount=Decimal("50.00"),
            currency="USD",
            reference_id=None,
        )


@patch("app.services.wallet_service.claim_idempotency_key")
def test_same_key_different_endpoint_is_rejected(
    mock_claim_idempotency_key,
):
    db = MagicMock()

    record = _existing_record(
        endpoint="/wallet/deposit",
    )

    mock_claim_idempotency_key.return_value = (
        record,
        False,
    )

    with pytest.raises(
        IdempotencyKeyReuseError,
    ):
        _claim_or_validate_idempotency_key(
            db=db,
            idempotency_key="test-key",
            user_id="test_user",
            endpoint="/wallet/withdraw",
            amount=Decimal("50.00"),
            currency="USD",
            reference_id=None,
        )


@patch("app.services.wallet_service.claim_idempotency_key")
def test_same_key_different_reference_id_is_rejected(
    mock_claim_idempotency_key,
):
    db = MagicMock()

    record = _existing_record(
        reference_id="reference-a",
    )

    mock_claim_idempotency_key.return_value = (
        record,
        False,
    )

    with pytest.raises(
        IdempotencyKeyReuseError,
        match="different request payload",
    ):
        _claim_or_validate_idempotency_key(
            db=db,
            idempotency_key="test-key",
            user_id="test_user",
            endpoint="/wallet/credit",
            amount=Decimal("50.00"),
            currency="USD",
            reference_id="reference-b",
        )


@patch("app.services.wallet_service.claim_idempotency_key")
def test_new_key_is_claimed(
    mock_claim_idempotency_key,
):
    db = MagicMock()

    record = _existing_record()

    mock_claim_idempotency_key.return_value = (
        record,
        True,
    )

    result_record, already_processed = (
        _claim_or_validate_idempotency_key(
            db=db,
            idempotency_key="new-key",
            user_id="test_user",
            endpoint="/wallet/deposit",
            amount=Decimal("50.00"),
            currency="USD",
            reference_id=None,
        )
    )

    assert result_record is record
    assert already_processed is False

    mock_claim_idempotency_key.assert_called_once()

    call_kwargs = (
        mock_claim_idempotency_key.call_args.kwargs
    )

    assert call_kwargs["key"] == "new-key"
    assert call_kwargs["user_id"] == "test_user"
    assert call_kwargs["endpoint"] == "/wallet/deposit"
    assert len(call_kwargs["request_hash"]) == 64