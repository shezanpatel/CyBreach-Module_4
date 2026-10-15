from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def deposit(user_id: str, idempotency_key: str):
    return client.post(
        "/wallet/deposit",
        headers={
            "idempotency-key": idempotency_key,
        },
        json={
            "user_id": user_id,
            "amount": 10,
            "currency": "USD",
        },
    )


def test_concurrent_deposits():
    """
    Verify that concurrent deposits are handled safely.

    20 concurrent deposits × $10 = exactly $200.
    A unique user is used for every test run so previous
    test executions cannot affect the result.
    """

    workers = 20

    # Unique user for every test run.
    user_id = f"stress_user_{uuid4().hex[:8]}"

    # ---------------------------------------------------------
    # STEP 1: Execute 20 deposits concurrently
    # ---------------------------------------------------------
    with ThreadPoolExecutor(max_workers=workers) as executor:
        results = list(
            executor.map(
                lambda i: deposit(
                    user_id=user_id,
                    idempotency_key=f"stress-{uuid4()}",
                ),
                range(workers),
            )
        )

    # ---------------------------------------------------------
    # STEP 2: Every request must succeed
    # ---------------------------------------------------------
    for response in results:
        assert response.status_code == 200, response.text

    # ---------------------------------------------------------
    # STEP 3: Retrieve final wallet balance
    # ---------------------------------------------------------
    response = client.get(
        f"/wallet/balance/{user_id}?currency=USD"
    )

    assert response.status_code == 200

    balance = float(
        response.json()["available_balance"]
    )

    # ---------------------------------------------------------
    # STEP 4: Verify exact expected balance
    # ---------------------------------------------------------
    expected_balance = workers * 10

    assert balance == expected_balance