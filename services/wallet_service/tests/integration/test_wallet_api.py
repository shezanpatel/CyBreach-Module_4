from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_wallet_api_flow():
    # Use a unique user for every test run.
    # This prevents previous database data from affecting the test.
    user_id = f"integration_user_{uuid4().hex[:8]}"

    deposit_idempotency_key = f"integration-deposit-{uuid4().hex}"
    withdraw_idempotency_key = f"integration-withdraw-{uuid4().hex}"

    # ---------------------------------------------------------
    # 1. Deposit $500
    # ---------------------------------------------------------
    response = client.post(
        "/wallet/deposit",
        headers={
            "idempotency-key": deposit_idempotency_key,
        },
        json={
            "user_id": user_id,
            "amount": 500,
            "currency": "USD",
        },
    )

    assert response.status_code == 200

    deposit_response = response.json()

    assert deposit_response["user_id"] == user_id
    assert float(deposit_response["available_balance"]) == 500.0

    # ---------------------------------------------------------
    # 2. Check balance
    # ---------------------------------------------------------
    response = client.get(
        f"/wallet/balance/{user_id}?currency=USD"
    )

    assert response.status_code == 200

    balance_response = response.json()

    assert balance_response["user_id"] == user_id
    assert float(balance_response["available_balance"]) == 500.0

    # ---------------------------------------------------------
    # 3. Withdraw $200
    # ---------------------------------------------------------
    response = client.post(
        "/wallet/withdraw",
        headers={
            "idempotency-key": withdraw_idempotency_key,
        },
        json={
            "user_id": user_id,
            "amount": 200,
            "currency": "USD",
        },
    )

    assert response.status_code == 200

    withdraw_response = response.json()

    assert withdraw_response["user_id"] == user_id
    assert float(withdraw_response["available_balance"]) == 300.0

    # ---------------------------------------------------------
    # 4. Check final balance
    # ---------------------------------------------------------
    response = client.get(
        f"/wallet/balance/{user_id}?currency=USD"
    )

    assert response.status_code == 200

    final_balance_response = response.json()

    assert final_balance_response["user_id"] == user_id
    assert float(final_balance_response["available_balance"]) == 300.0