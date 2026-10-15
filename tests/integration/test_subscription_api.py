from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _get_balance(user_id: str) -> float:
    response = client.get(
        f"/wallet/balance/{user_id}?currency=USD"
    )

    assert response.status_code == 200

    return float(
        response.json()["available_balance"]
    )


def test_subscription_signup_renew_cancel_flow():
    """
    Week 8 end-to-end lifecycle:

    STARTER signup:
        50 credits

    Renewal:
        +50 credits

    Cancellation:
        existing 100 credits remain available
    """

    user_id = (
        f"subscription_integration_{uuid4().hex[:12]}"
    )

    # ---------------------------------------------------------
    # 1. Subscribe to STARTER
    # ---------------------------------------------------------

    response = client.post(
        "/subscription/signup",
        json={
            "user_id": user_id,
            "tier": "STARTER",
        },
    )

    assert response.status_code == 200

    signup = response.json()

    assert signup["user_id"] == user_id
    assert signup["tier"] == "STARTER"
    assert signup["status"] == "ACTIVE"
    assert float(signup["credits_per_period"]) == 50.0

    # ---------------------------------------------------------
    # 2. Verify signup allocation reached the wallet
    # ---------------------------------------------------------

    assert _get_balance(user_id) == 50.0

    # ---------------------------------------------------------
    # 3. Renew subscription
    # ---------------------------------------------------------

    response = client.post(
        "/subscription/renew",
        json={
            "user_id": user_id,
        },
    )

    assert response.status_code == 200

    renewal = response.json()

    assert renewal["tier"] == "STARTER"
    assert renewal["status"] == "ACTIVE"
    assert float(renewal["credits_per_period"]) == 50.0

    # ---------------------------------------------------------
    # 4. Renewal adds another allocation
    # ---------------------------------------------------------

    assert _get_balance(user_id) == 100.0

    # ---------------------------------------------------------
    # 5. Cancel subscription
    # ---------------------------------------------------------

    response = client.post(
        "/subscription/cancel",
        json={
            "user_id": user_id,
        },
    )

    assert response.status_code == 200

    cancelled = response.json()

    assert cancelled["status"] == "CANCELLED"
    assert cancelled["cancelled_at"] is not None

    # ---------------------------------------------------------
    # 6. Cancellation must NOT remove unused credits
    # ---------------------------------------------------------

    assert _get_balance(user_id) == 100.0


def test_subscription_upgrade_affects_future_renewal():
    """
    Tier change itself does not create an invented prorated
    allocation.

    STARTER signup:
        50 credits

    Upgrade to PROFESSIONAL:
        wallet remains 50

    Next renewal:
        +200 credits

    Final:
        250 credits
    """

    user_id = (
        f"subscription_upgrade_{uuid4().hex[:12]}"
    )

    response = client.post(
        "/subscription/signup",
        json={
            "user_id": user_id,
            "tier": "STARTER",
        },
    )

    assert response.status_code == 200
    assert _get_balance(user_id) == 50.0

    response = client.post(
        "/subscription/change-tier",
        json={
            "user_id": user_id,
            "tier": "PROFESSIONAL",
        },
    )

    assert response.status_code == 200

    changed = response.json()

    assert changed["tier"] == "PROFESSIONAL"
    assert float(changed["credits_per_period"]) == 200.0

    # No unspecified immediate/prorated allocation.
    assert _get_balance(user_id) == 50.0

    response = client.post(
        "/subscription/renew",
        json={
            "user_id": user_id,
        },
    )

    assert response.status_code == 200

    renewed = response.json()

    assert renewed["tier"] == "PROFESSIONAL"
    assert float(renewed["credits_per_period"]) == 200.0

    assert _get_balance(user_id) == 250.0


def test_subscription_downgrade_affects_future_renewal():
    """
    PROFESSIONAL signup:
        200 credits

    Downgrade to STARTER:
        wallet remains 200

    Next renewal:
        +50 credits

    Final:
        250 credits
    """

    user_id = (
        f"subscription_downgrade_{uuid4().hex[:12]}"
    )

    response = client.post(
        "/subscription/signup",
        json={
            "user_id": user_id,
            "tier": "PROFESSIONAL",
        },
    )

    assert response.status_code == 200
    assert _get_balance(user_id) == 200.0

    response = client.post(
        "/subscription/change-tier",
        json={
            "user_id": user_id,
            "tier": "STARTER",
        },
    )

    assert response.status_code == 200

    changed = response.json()

    assert changed["tier"] == "STARTER"
    assert float(changed["credits_per_period"]) == 50.0

    # Existing credits remain unchanged.
    assert _get_balance(user_id) == 200.0

    response = client.post(
        "/subscription/renew",
        json={
            "user_id": user_id,
        },
    )

    assert response.status_code == 200

    assert _get_balance(user_id) == 250.0
