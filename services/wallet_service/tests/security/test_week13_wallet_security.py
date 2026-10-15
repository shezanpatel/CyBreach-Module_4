from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from tests.conftest import ORIGINAL_TESTCLIENT_INIT


def make_raw_client() -> TestClient:
    current_init = TestClient.__init__

    try:
        TestClient.__init__ = ORIGINAL_TESTCLIENT_INIT
        return TestClient(app)
    finally:
        TestClient.__init__ = current_init


def make_token(
    tenant_id: str,
    role: str = "tenant",
    expires_in_minutes: int = 15,
) -> str:
    now = datetime.now(timezone.utc)

    return jwt.encode(
        {
            "sub": f"{tenant_id}-subject",
            "tenant_id": tenant_id,
            "role": role,
            "iat": now,
            "exp": now + timedelta(
                minutes=expires_in_minutes,
            ),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


client = make_raw_client()


def test_health_endpoint_remains_public():
    response = client.get("/")

    assert response.status_code == 200


def test_missing_jwt_is_rejected():
    response = client.get(
        "/wallet/balance/week13-security-a"
    )

    assert response.status_code == 401


def test_invalid_jwt_is_rejected():
    response = client.get(
        "/wallet/balance/week13-security-a",
        headers={
            "Authorization": "Bearer invalid-token",
        },
    )

    assert response.status_code == 401


def test_expired_jwt_is_rejected():
    token = make_token(
        "week13-security-a",
        expires_in_minutes=-1,
    )

    response = client.get(
        "/wallet/balance/week13-security-a",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 401


def test_same_tenant_request_passes_authorization():
    token = make_token("week13-security-a")

    response = client.get(
        "/wallet/balance/week13-security-a",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code != 401
    assert response.status_code != 403


def test_cross_tenant_path_request_is_forbidden():
    token = make_token("week13-security-a")

    response = client.get(
        "/wallet/balance/week13-security-b",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 403


def test_cross_tenant_debit_is_forbidden():
    token = make_token("week13-security-a")

    response = client.post(
        "/wallet/debit",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Service-API-Key":
                settings.SERVICE_API_KEY,
            "Idempotency-Key":
                "mod1:week13hash:week13-security-b:run001",
        },
        json={
            "user_id": "week13-security-b",
            "amount": "5.00",
            "currency": "USD",
        },
    )

    assert response.status_code == 403


def test_debit_without_service_api_key_is_forbidden():
    token = make_token("week13-security-a")

    response = client.post(
        "/wallet/debit",
        headers={
            "Authorization": f"Bearer {token}",
            "Idempotency-Key":
                "mod1:week13hash:week13-security-a:run002",
        },
        json={
            "user_id": "week13-security-a",
            "amount": "5.00",
            "currency": "USD",
        },
    )

    assert response.status_code == 403


def test_debit_with_invalid_service_api_key_is_forbidden():
    token = make_token("week13-security-a")

    response = client.post(
        "/wallet/debit",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Service-API-Key": "invalid-service-key",
            "Idempotency-Key":
                "mod1:week13hash:week13-security-a:run003",
        },
        json={
            "user_id": "week13-security-a",
            "amount": "5.00",
            "currency": "USD",
        },
    )

    assert response.status_code == 403


def test_credit_without_service_api_key_is_forbidden():
    token = make_token("week13-security-a")

    response = client.post(
        "/wallet/credit",
        headers={
            "Authorization": f"Bearer {token}",
            "Idempotency-Key":
                "week13-security-credit-no-key",
        },
        json={
            "user_id": "week13-security-a",
            "amount": "5.00",
            "currency": "USD",
            "reference_id": "week13-security",
        },
    )

    assert response.status_code == 403


def test_tenant_cannot_run_global_reconciliation():
    token = make_token("week13-security-a")

    response = client.get(
        "/reconciliation/run",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 403


def test_admin_can_cross_tenant_boundary():
    token = make_token(
        "week13-admin",
        role="admin",
    )

    response = client.get(
        "/wallet/balance/week13-security-b",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code != 401
    assert response.status_code != 403


def test_swagger_and_openapi_remain_public():
    docs = client.get("/docs")
    openapi = client.get("/openapi.json")

    assert docs.status_code == 200
    assert openapi.status_code == 200
