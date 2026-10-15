import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


# ============================================================
# TEST DATA HELPERS
# ============================================================

def unique_user(prefix: str = "contract-user") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def unique_key(prefix: str = "contract-key") -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


# ============================================================
# DEPOSIT
# ============================================================

def test_deposit():
    user_id = unique_user()
    idempotency_key = unique_key("deposit")

    response = client.post(
        "/wallet/deposit",
        json={
            "user_id": user_id,
            "amount": "100.00",
            "currency": "USD",
        },
        headers={
            "Idempotency-Key": idempotency_key,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["user_id"] == user_id
    assert data["currency"] == "USD"
    assert Decimal(data["available_balance"]) == Decimal("100.00")


# ============================================================
# BALANCE
# ============================================================

def test_balance():
    user_id = unique_user()
    deposit_key = unique_key("balance-deposit")

    deposit_response = client.post(
        "/wallet/deposit",
        json={
            "user_id": user_id,
            "amount": "150.00",
            "currency": "USD",
        },
        headers={
            "Idempotency-Key": deposit_key,
        },
    )

    assert deposit_response.status_code == 200

    response = client.get(
        f"/wallet/balance/{user_id}",
        params={
            "currency": "USD",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["user_id"] == user_id
    assert data["currency"] == "USD"
    assert Decimal(data["available_balance"]) == Decimal("150.00")


# ============================================================
# WITHDRAW
# ============================================================

def test_withdraw():
    user_id = unique_user()

    deposit_response = client.post(
        "/wallet/deposit",
        json={
            "user_id": user_id,
            "amount": "200.00",
            "currency": "USD",
        },
        headers={
            "Idempotency-Key": unique_key("withdraw-deposit"),
        },
    )

    assert deposit_response.status_code == 200

    withdraw_response = client.post(
        "/wallet/withdraw",
        json={
            "user_id": user_id,
            "amount": "75.00",
            "currency": "USD",
        },
        headers={
            "Idempotency-Key": unique_key("withdraw"),
        },
    )

    assert withdraw_response.status_code == 200

    data = withdraw_response.json()

    assert data["user_id"] == user_id
    assert data["currency"] == "USD"
    assert Decimal(data["available_balance"]) == Decimal("125.00")


# ============================================================
# TRANSACTION HISTORY
# ============================================================

def test_transaction_history():
    user_id = unique_user()

    deposit_response = client.post(
        "/wallet/deposit",
        json={
            "user_id": user_id,
            "amount": "100.00",
            "currency": "USD",
        },
        headers={
            "Idempotency-Key": unique_key("history-deposit"),
        },
    )

    assert deposit_response.status_code == 200

    response = client.get(
        f"/wallet/transactions/{user_id}",
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert len(data) >= 1

    transaction = data[0]

    assert transaction["user_id"] == user_id
    assert transaction["currency"] == "USD"
    assert transaction["transaction_type"] == "DEPOSIT"
    assert Decimal(transaction["amount"]) == Decimal("100.00")


# ============================================================
# CREDIT
# ============================================================

def test_credit():
    user_id = unique_user()
    reference_id = f"contract-credit-{uuid.uuid4().hex}"

    response = client.post(
        "/wallet/credit",
        json={
            "user_id": user_id,
            "amount": "50.00",
            "currency": "USD",
            "reference_id": reference_id,
        },
        headers={
            "Idempotency-Key": unique_key("credit"),
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["user_id"] == user_id
    assert data["currency"] == "USD"
    assert Decimal(data["amount"]) == Decimal("50.00")
    assert Decimal(data["remaining_amount"]) == Decimal("50.00")
    assert data["reference_id"] == reference_id
    assert "id" in data
    assert "created_at" in data
    assert "expires_at" in data


# ============================================================
# DEPOSIT IDEMPOTENCY
# ============================================================

def test_deposit_idempotency():
    user_id = unique_user()
    idempotency_key = unique_key("deposit-idempotency")

    payload = {
        "user_id": user_id,
        "amount": "100.00",
        "currency": "USD",
    }

    first_response = client.post(
        "/wallet/deposit",
        json=payload,
        headers={
            "Idempotency-Key": idempotency_key,
        },
    )

    assert first_response.status_code == 200

    second_response = client.post(
        "/wallet/deposit",
        json=payload,
        headers={
            "Idempotency-Key": idempotency_key,
        },
    )

    assert second_response.status_code == 200

    first_data = first_response.json()
    second_data = second_response.json()

    assert Decimal(
        first_data["available_balance"]
    ) == Decimal(
        second_data["available_balance"]
    )

    balance_response = client.get(
        f"/wallet/balance/{user_id}",
        params={
            "currency": "USD",
        },
    )

    assert balance_response.status_code == 200

    balance_data = balance_response.json()

    # The deposit must only have been applied once.
    assert Decimal(
        balance_data["available_balance"]
    ) == Decimal("100.00")


# ============================================================
# CREDIT IDEMPOTENCY
# ============================================================

def test_credit_idempotency():
    user_id = unique_user()
    idempotency_key = unique_key("credit-idempotency")
    reference_id = f"credit-idempotency-{uuid.uuid4().hex}"

    payload = {
        "user_id": user_id,
        "amount": "75.00",
        "currency": "USD",
        "reference_id": reference_id,
    }

    first_response = client.post(
        "/wallet/credit",
        json=payload,
        headers={
            "Idempotency-Key": idempotency_key,
        },
    )

    assert first_response.status_code == 200

    second_response = client.post(
        "/wallet/credit",
        json=payload,
        headers={
            "Idempotency-Key": idempotency_key,
        },
    )

    assert second_response.status_code == 200

    first_data = first_response.json()
    second_data = second_response.json()

    # The same original credit must be returned.
    assert first_data["id"] == second_data["id"]
    assert first_data["user_id"] == second_data["user_id"]
    assert first_data["currency"] == second_data["currency"]
    assert Decimal(first_data["amount"]) == Decimal(
        second_data["amount"]
    )
    assert Decimal(
        first_data["remaining_amount"]
    ) == Decimal(
        second_data["remaining_amount"]
    )
    assert first_data["reference_id"] == second_data[
        "reference_id"
    ]


# ============================================================
# CREDIT IDEMPOTENCY — DIFFERENT AMOUNT
# ============================================================

def test_credit_idempotency_rejects_different_amount():
    user_id = unique_user()
    idempotency_key = unique_key("credit-amount")
    reference_id = f"credit-amount-{uuid.uuid4().hex}"

    first_payload = {
        "user_id": user_id,
        "amount": "50.00",
        "currency": "USD",
        "reference_id": reference_id,
    }

    second_payload = {
        "user_id": user_id,
        "amount": "75.00",
        "currency": "USD",
        "reference_id": reference_id,
    }

    first_response = client.post(
        "/wallet/credit",
        json=first_payload,
        headers={
            "Idempotency-Key": idempotency_key,
        },
    )

    assert first_response.status_code == 200

    second_response = client.post(
        "/wallet/credit",
        json=second_payload,
        headers={
            "Idempotency-Key": idempotency_key,
        },
    )

    assert second_response.status_code == 409


# ============================================================
# CREDIT IDEMPOTENCY — DIFFERENT CURRENCY
# ============================================================

def test_credit_idempotency_rejects_different_currency():
    user_id = unique_user()
    idempotency_key = unique_key("credit-currency")
    reference_id = f"credit-currency-{uuid.uuid4().hex}"

    first_payload = {
        "user_id": user_id,
        "amount": "50.00",
        "currency": "USD",
        "reference_id": reference_id,
    }

    second_payload = {
        "user_id": user_id,
        "amount": "50.00",
        "currency": "EUR",
        "reference_id": reference_id,
    }

    first_response = client.post(
        "/wallet/credit",
        json=first_payload,
        headers={
            "Idempotency-Key": idempotency_key,
        },
    )

    assert first_response.status_code == 200

    second_response = client.post(
        "/wallet/credit",
        json=second_payload,
        headers={
            "Idempotency-Key": idempotency_key,
        },
    )

    assert second_response.status_code == 409


# ============================================================
# CREDIT IDEMPOTENCY — DIFFERENT REFERENCE
# ============================================================

def test_credit_idempotency_rejects_different_reference():
    user_id = unique_user()
    idempotency_key = unique_key("credit-reference")

    first_payload = {
        "user_id": user_id,
        "amount": "50.00",
        "currency": "USD",
        "reference_id": f"reference-a-{uuid.uuid4().hex}",
    }

    second_payload = {
        "user_id": user_id,
        "amount": "50.00",
        "currency": "USD",
        "reference_id": f"reference-b-{uuid.uuid4().hex}",
    }

    first_response = client.post(
        "/wallet/credit",
        json=first_payload,
        headers={
            "Idempotency-Key": idempotency_key,
        },
    )

    assert first_response.status_code == 200

    second_response = client.post(
        "/wallet/credit",
        json=second_payload,
        headers={
            "Idempotency-Key": idempotency_key,
        },
    )

    assert second_response.status_code == 409


# ============================================================
# CREDIT REQUIRES IDEMPOTENCY KEY
# ============================================================

def test_credit_requires_idempotency():
    user_id = unique_user()

    response = client.post(
        "/wallet/credit",
        json={
            "user_id": user_id,
            "amount": "50.00",
            "currency": "USD",
            "reference_id": f"missing-key-{uuid.uuid4().hex}",
        },
    )

    assert response.status_code == 422


# ============================================================
# WITHDRAW INSUFFICIENT BALANCE
# ============================================================

def test_withdraw_insufficient_balance():
    user_id = unique_user()

    deposit_response = client.post(
        "/wallet/deposit",
        json={
            "user_id": user_id,
            "amount": "20.00",
            "currency": "USD",
        },
        headers={
            "Idempotency-Key": unique_key("insufficient-deposit"),
        },
    )

    assert deposit_response.status_code == 200

    response = client.post(
        "/wallet/withdraw",
        json={
            "user_id": user_id,
            "amount": "50.00",
            "currency": "USD",
        },
        headers={
            "Idempotency-Key": unique_key("insufficient-withdraw"),
        },
    )

    assert response.status_code in (400, 409)


# ============================================================
# BALANCE NOT FOUND
# ============================================================

def test_balance_not_found():
    user_id = unique_user("nonexistent")

    response = client.get(
        f"/wallet/balance/{user_id}",
        params={
            "currency": "USD",
        },
    )

    assert response.status_code == 404


# ============================================================
# DEPOSIT MISSING IDEMPOTENCY KEY
# ============================================================

def test_deposit_missing_idempotency_key():
    user_id = unique_user()

    response = client.post(
        "/wallet/deposit",
        json={
            "user_id": user_id,
            "amount": "25.00",
            "currency": "USD",
        },
    )

    assert response.status_code == 422


# ============================================================
# WITHDRAW MISSING IDEMPOTENCY KEY
# ============================================================

def test_withdraw_missing_idempotency_key():
    user_id = unique_user()

    response = client.post(
        "/wallet/withdraw",
        json={
            "user_id": user_id,
            "amount": "25.00",
            "currency": "USD",
        },
    )

    assert response.status_code == 422


# ============================================================
# INVALID DEPOSIT AMOUNT
# ============================================================

def test_invalid_deposit_amount():
    user_id = unique_user()

    response = client.post(
        "/wallet/deposit",
        json={
            "user_id": user_id,
            "amount": "0.00",
            "currency": "USD",
        },
        headers={
            "Idempotency-Key": unique_key("invalid-deposit"),
        },
    )

    assert response.status_code == 400


# ============================================================
# INVALID WITHDRAW AMOUNT
# ============================================================

def test_invalid_withdraw_amount():
    user_id = unique_user()

    response = client.post(
        "/wallet/withdraw",
        json={
            "user_id": user_id,
            "amount": "0.00",
            "currency": "USD",
        },
        headers={
            "Idempotency-Key": unique_key("invalid-withdraw"),
        },
    )

    assert response.status_code == 400


# ============================================================
# COMPLETE WALLET FLOW
# ============================================================

def test_complete_wallet_flow():
    user_id = unique_user()

    # --------------------------------------------------------
    # 1. Deposit
    # --------------------------------------------------------

    deposit_response = client.post(
        "/wallet/deposit",
        json={
            "user_id": user_id,
            "amount": "500.00",
            "currency": "USD",
        },
        headers={
            "Idempotency-Key": unique_key("flow-deposit"),
        },
    )

    assert deposit_response.status_code == 200

    assert Decimal(
        deposit_response.json()["available_balance"]
    ) == Decimal("500.00")

    # --------------------------------------------------------
    # 2. Withdraw
    # --------------------------------------------------------

    withdraw_response = client.post(
        "/wallet/withdraw",
        json={
            "user_id": user_id,
            "amount": "125.00",
            "currency": "USD",
        },
        headers={
            "Idempotency-Key": unique_key("flow-withdraw"),
        },
    )

    assert withdraw_response.status_code == 200

    assert Decimal(
        withdraw_response.json()["available_balance"]
    ) == Decimal("375.00")

    # --------------------------------------------------------
    # 3. Credit
    # --------------------------------------------------------

    credit_response = client.post(
        "/wallet/credit",
        json={
            "user_id": user_id,
            "amount": "75.00",
            "currency": "USD",
            "reference_id": f"flow-credit-{uuid.uuid4().hex}",
        },
        headers={
            "Idempotency-Key": unique_key("flow-credit"),
        },
    )

    assert credit_response.status_code == 200

    credit_data = credit_response.json()

    assert Decimal(
        credit_data["amount"]
    ) == Decimal("75.00")

    assert Decimal(
        credit_data["remaining_amount"]
    ) == Decimal("75.00")

    # --------------------------------------------------------
    # 4. Final balance
    # --------------------------------------------------------

    balance_response = client.get(
        f"/wallet/balance/{user_id}",
        params={
            "currency": "USD",
        },
    )

    assert balance_response.status_code == 200

    assert Decimal(
        balance_response.json()["available_balance"]
    ) == Decimal("450.00")

    # --------------------------------------------------------
    # 5. Transaction history
    # --------------------------------------------------------

    transactions_response = client.get(
        f"/wallet/transactions/{user_id}",
    )

    assert transactions_response.status_code == 200

    transactions = transactions_response.json()

    assert len(transactions) >= 3

    transaction_types = {
        transaction["transaction_type"]
        for transaction in transactions
    }

    assert "DEPOSIT" in transaction_types
    assert "WITHDRAW" in transaction_types
    assert "CREDIT" in transaction_types