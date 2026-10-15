from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.main import app
from app.models.wallet_ledger_entry import WalletLedgerEntry


client = TestClient(app)


def unique_user(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}"


def deposit_funds(
    user_id: str,
    amount: str = "500.00",
) -> None:
    response = client.post(
        "/wallet/deposit",
        json={
            "user_id": user_id,
            "amount": amount,
            "currency": "USD",
        },
        headers={
            "Idempotency-Key": f"week12-deposit-{uuid4().hex}",
        },
    )

    assert response.status_code == 200, response.text


def get_balance(user_id: str) -> str:
    response = client.get(
        f"/wallet/balance/{user_id}",
        params={"currency": "USD"},
    )

    assert response.status_code == 200, response.text

    return response.json()["available_balance"]


def get_module_entries(
    user_id: str,
    module_source: str,
):
    db = SessionLocal()

    try:
        return (
            db.query(WalletLedgerEntry)
            .filter(
                WalletLedgerEntry.user_id == user_id,
                WalletLedgerEntry.module_source == module_source,
            )
            .all()
        )
    finally:
        db.close()


def test_module1_real_wallet_debit():
    user_id = unique_user("week12-mod1")

    deposit_funds(user_id)

    idempotency_key = (
        f"mod1:playbookhash:{user_id}:run-{uuid4().hex}"
    )

    response = client.post(
        "/wallet/debit",
        json={
            "user_id": user_id,
            "amount": "100.00",
            "currency": "USD",
        },
        headers={
            "Idempotency-Key": idempotency_key,
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["available_balance"] == "400.00"

    entries = get_module_entries(
        user_id=user_id,
        module_source="mod1",
    )

    assert len(entries) == 2
    assert {entry.entry_type for entry in entries} == {
        "DEBIT",
        "CREDIT",
    }


def test_module2_real_wallet_debit():
    user_id = unique_user("week12-mod2")

    deposit_funds(user_id)

    idempotency_key = (
        f"mod2:rulehash:{user_id}:reval-{uuid4().hex}"
    )

    response = client.post(
        "/wallet/debit",
        json={
            "user_id": user_id,
            "amount": "125.00",
            "currency": "USD",
        },
        headers={
            "Idempotency-Key": idempotency_key,
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["available_balance"] == "375.00"

    entries = get_module_entries(
        user_id=user_id,
        module_source="mod2",
    )

    assert len(entries) == 2
    assert {entry.entry_type for entry in entries} == {
        "DEBIT",
        "CREDIT",
    }


def test_module3_real_wallet_debit():
    user_id = unique_user("week12-mod3")

    deposit_funds(user_id)

    idempotency_key = (
        f"mod3:framework:{user_id}:report-{uuid4().hex}"
    )

    response = client.post(
        "/wallet/debit",
        json={
            "user_id": user_id,
            "amount": "150.00",
            "currency": "USD",
        },
        headers={
            "Idempotency-Key": idempotency_key,
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["available_balance"] == "350.00"

    entries = get_module_entries(
        user_id=user_id,
        module_source="mod3",
    )

    assert len(entries) == 2
    assert {entry.entry_type for entry in entries} == {
        "DEBIT",
        "CREDIT",
    }


def test_cross_module_debit_is_idempotent():
    user_id = unique_user("week12-replay")

    deposit_funds(user_id)

    idempotency_key = (
        f"mod1:playbookhash:{user_id}:run-{uuid4().hex}"
    )

    payload = {
        "user_id": user_id,
        "amount": "75.00",
        "currency": "USD",
    }

    first_response = client.post(
        "/wallet/debit",
        json=payload,
        headers={
            "Idempotency-Key": idempotency_key,
        },
    )

    assert first_response.status_code == 200
    assert first_response.json()["available_balance"] == "425.00"

    second_response = client.post(
        "/wallet/debit",
        json=payload,
        headers={
            "Idempotency-Key": idempotency_key,
        },
    )

    assert second_response.status_code == 200
    assert second_response.json()["available_balance"] == "425.00"

    assert get_balance(user_id) == "425.00"

    entries = get_module_entries(
        user_id=user_id,
        module_source="mod1",
    )

    assert len(entries) == 2


def test_invalid_cross_module_idempotency_key_is_rejected():
    user_id = unique_user("week12-invalid")

    deposit_funds(user_id)

    response = client.post(
        "/wallet/debit",
        json={
            "user_id": user_id,
            "amount": "50.00",
            "currency": "USD",
        },
        headers={
            "Idempotency-Key": f"unknown:{uuid4().hex}",
        },
    )

    assert response.status_code == 400
    assert get_balance(user_id) == "500.00"


def test_cross_module_debit_requires_idempotency_key():
    user_id = unique_user("week12-missing-key")

    deposit_funds(user_id)

    response = client.post(
        "/wallet/debit",
        json={
            "user_id": user_id,
            "amount": "50.00",
            "currency": "USD",
        },
    )

    assert response.status_code == 422
    assert get_balance(user_id) == "500.00"


def test_cross_module_insufficient_balance_does_not_debit():
    user_id = unique_user("week12-insufficient")

    deposit_funds(
        user_id=user_id,
        amount="50.00",
    )

    idempotency_key = (
        f"mod2:rulehash:{user_id}:reval-{uuid4().hex}"
    )

    response = client.post(
        "/wallet/debit",
        json={
            "user_id": user_id,
            "amount": "100.00",
            "currency": "USD",
        },
        headers={
            "Idempotency-Key": idempotency_key,
        },
    )

    assert response.status_code == 400
    assert get_balance(user_id) == "50.00"
