import httpx
import pytest
from jose import jwt
from uuid import uuid4

from app.api import arena_gateway_routes
from app.core.security import AuthenticatedPrincipal
from app.core.settings import settings
from app.main import app


@pytest.fixture
async def api_client():
    transport = httpx.ASGITransport(
        app=app,
        client=("127.0.0.1", 12345),
    )
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        yield client


@pytest.fixture(autouse=True)
def reset_demo_state():
    with arena_gateway_routes._demo_account_lock:
        arena_gateway_routes._demo_account = arena_gateway_routes._new_demo_account()
    yield


def _token(role: str = "user") -> str:
    return jwt.encode(
        {
            "sub": "1",
            "tenant_id": "demo-tenant",
            "role": role,
            "exp": 4_102_444_800,
        },
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def _demo_checkout(**overrides):
    return {
        "package_id": "operator",
        "payment_method": "demo_upi",
        "checkout_id": str(uuid4()),
        "customer_name": "Demo Manager",
        "customer_email": "manager@example.test",
        "billing_address": "100 Demo Street, Example City",
        **overrides,
    }


async def test_demo_auth_requires_configured_demo_credentials(api_client):
    response = await api_client.post(
        "/api/v1/auth/demo",
        json={
            "account_id": settings.DEMO_ACCOUNT_ID,
            "password": settings.DEMO_ACCOUNT_PASSWORD,
        },
    )

    assert response.status_code == 200
    session = response.json()
    claims = jwt.decode(
        session["access_token"],
        settings.SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )
    assert session["mode"] == "development_demo"
    assert claims["sub"] == "1"
    assert claims["tenant_id"] == "demo-tenant"
    assert claims["role"] == "demo"


async def test_demo_auth_rejects_invalid_password(api_client):
    response = await api_client.post(
        "/api/v1/auth/demo",
        json={
            "account_id": settings.DEMO_ACCOUNT_ID,
            "password": "incorrect",
        },
    )

    assert response.status_code == 401


async def test_demo_auth_rejects_non_loopback_clients(monkeypatch):
    transport = httpx.ASGITransport(
        app=app,
        client=("192.0.2.10", 12345),
    )
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/api/v1/auth/demo",
            json={
                "account_id": settings.DEMO_ACCOUNT_ID,
                "password": settings.DEMO_ACCOUNT_PASSWORD,
            },
        )

    assert response.status_code == 404


async def test_demo_state_requires_demo_identity(api_client):
    response = await api_client.get(
        "/api/v1/arena/demo/state",
        headers={"Authorization": f"Bearer {_token()}"},
    )

    assert response.status_code == 403


async def test_demo_state_is_seeded_and_separate_from_live_wallet(api_client):
    response = await api_client.get(
        "/api/v1/arena/demo/state",
        headers={"Authorization": f"Bearer {_token('demo')}"},
    )

    assert response.status_code == 200
    state = response.json()
    assert state["wallet"] == {
        "available_balance": settings.DEMO_STARTING_CREDITS,
        "currency": "CR",
    }
    assert state["transactions"]["entries"][0]["reference_id"] == "Welcome demo credits"
    assert state["notifications"]["total"] == 1
    assert state["analytics"]["source"] == "simulated_demo"


async def test_demo_top_up_simulates_payment_and_updates_ledger(api_client):
    response = await api_client.post(
        "/api/v1/arena/demo/top-up",
        headers={"Authorization": f"Bearer {_token('demo')}"},
        json=_demo_checkout(),
    )

    assert response.status_code == 200
    result = response.json()
    assert result["payment"]["status"] == "simulated_success"
    assert result["payment"]["message"] == "Demo payment approved. No money was charged."
    assert result["receipt"]["status"] == "simulated_success"
    assert result["receipt"]["customer"]["name"] == "Demo Manager"
    assert result["receipt"]["customer"]["email"] == "manager@example.test"
    assert result["receipt"]["payment"]["method_label"] == "Demo UPI · demo@arena.test"
    assert result["receipt"]["subtotal"] == 9.99
    assert result["receipt"]["tax"] == 0
    assert result["receipt"]["total"] == 9.99
    assert result["receipt"]["credits_added"] == 750
    assert result["state"]["wallet"]["available_balance"] == settings.DEMO_STARTING_CREDITS + 750
    assert result["state"]["transactions"]["entries"][0]["entry_type"] == "credit"
    assert result["state"]["receipts"]["total"] == 1
    assert result["state"]["notifications"]["total"] == 2


async def test_demo_checkout_replay_does_not_credit_wallet_twice(api_client):
    checkout = _demo_checkout()
    headers = {"Authorization": f"Bearer {_token('demo')}"}
    first = await api_client.post(
        "/api/v1/arena/demo/top-up",
        headers=headers,
        json=checkout,
    )
    replay = await api_client.post(
        "/api/v1/arena/demo/top-up",
        headers=headers,
        json=checkout,
    )

    assert first.status_code == replay.status_code == 200
    assert replay.json()["receipt"]["receipt_number"] == first.json()["receipt"]["receipt_number"]
    assert replay.json()["state"]["wallet"]["available_balance"] == settings.DEMO_STARTING_CREDITS + 750
    assert replay.json()["state"]["receipts"]["total"] == 1


async def test_demo_checkout_rejects_invalid_billing_details(api_client):
    response = await api_client.post(
        "/api/v1/arena/demo/top-up",
        headers={"Authorization": f"Bearer {_token('demo')}"},
        json=_demo_checkout(customer_email="not-an-email"),
    )

    assert response.status_code == 422
    assert arena_gateway_routes._demo_snapshot()["wallet"]["available_balance"] == settings.DEMO_STARTING_CREDITS


async def test_demo_engagement_debits_demo_credits_and_returns_fake_findings(api_client):
    response = await api_client.post(
        "/api/v1/arena/demo/engagements",
        headers={"Authorization": f"Bearer {_token('demo')}"},
        json={
            "campaign_id": "vulnerability-scan",
            "campaign_title": "Vulnerability Scan",
            "credit_cost": 100,
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["engagement"]["status"] == "simulated_completed"
    assert result["engagement"]["finding_count"] > 0
    assert "No targets were contacted" in result["engagement"]["notice"]
    assert result["state"]["wallet"]["available_balance"] == settings.DEMO_STARTING_CREDITS - 100
    assert result["state"]["transactions"]["entries"][0]["entry_type"] == "debit"
    assert result["state"]["analytics"]["total_engagements"] == 1
    assert result["state"]["notifications"]["total"] == 2


async def test_demo_engagement_rejects_insufficient_balance(api_client):
    response = await api_client.post(
        "/api/v1/arena/demo/engagements",
        headers={"Authorization": f"Bearer {_token('demo')}"},
        json={
            "campaign_id": "big-scan",
            "campaign_title": "Large scan",
            "credit_cost": settings.DEMO_STARTING_CREDITS + 1,
        },
    )

    assert response.status_code == 402
    assert arena_gateway_routes._demo_snapshot()["wallet"]["available_balance"] == settings.DEMO_STARTING_CREDITS


async def test_demo_reset_restores_starting_state(api_client):
    await api_client.post(
        "/api/v1/arena/demo/top-up",
        headers={"Authorization": f"Bearer {_token('demo')}"},
        json=_demo_checkout(
            package_id="starter",
            payment_method="demo_card",
        ),
    )
    response = await api_client.post(
        "/api/v1/arena/demo/reset",
        headers={"Authorization": f"Bearer {_token('demo')}"},
    )

    assert response.status_code == 200
    assert response.json()["wallet"]["available_balance"] == settings.DEMO_STARTING_CREDITS
    assert response.json()["transactions"]["total"] == 1
    assert response.json()["receipts"]["total"] == 0


async def test_pod_proxy_requires_bearer_token(api_client):
    response = await api_client.get("/api/v1/arena/campaigns")
    assert response.status_code == 401


async def test_campaign_proxy_reports_missing_configuration(api_client, monkeypatch):
    monkeypatch.setattr(settings, "POD_BETA_CAMPAIGN_URL", None)

    response = await api_client.get(
        "/api/v1/arena/campaigns",
        headers={"Authorization": f"Bearer {_token()}"},
    )

    assert response.status_code == 503
    assert response.json()["error"]["message"] == "Pod Beta campaign API URL is not configured"


async def test_benchmark_cohort_proxy_forwards_authorization(api_client, monkeypatch):
    captured = {}

    async def fake_proxy(**kwargs):
        captured.update(kwargs)
        return arena_gateway_routes.Response(
            content=b'{"minimum_peer_count":10,"cohorts":[]}',
            media_type="application/json",
        )

    monkeypatch.setattr(settings, "POD_GAMMA_URL", "http://pod-gamma.test")
    monkeypatch.setattr(arena_gateway_routes, "_proxy", fake_proxy)

    response = await api_client.get(
        "/api/v1/arena/benchmark/cohorts",
        headers={"Authorization": f"Bearer {_token()}"},
    )

    assert response.status_code == 200
    assert response.json()["minimum_peer_count"] == 10
    assert captured["method"] == "GET"
    assert captured["base_url"] == "http://pod-gamma.test"
    assert captured["path"] == "/benchmark/cohorts"
    assert captured["authorization"] == f"Bearer {_token()}"


async def test_wallet_proxy_requires_server_side_delegation_secret(api_client, monkeypatch):
    monkeypatch.setattr(settings, "WALLET_SERVICE_JWT_SECRET", None)

    response = await api_client.get(
        "/api/v1/arena/wallet/balance",
        headers={"Authorization": f"Bearer {_token()}"},
    )

    assert response.status_code == 503
    assert response.json()["error"]["message"] == "Wallet service delegation secret is not configured"


def test_wallet_delegation_scopes_token_to_subject_wallet(monkeypatch):
    monkeypatch.setattr(
        settings,
        "WALLET_SERVICE_JWT_SECRET",
        "wallet-delegation-test-secret",
    )
    principal = AuthenticatedPrincipal(
        subject="1",
        tenant_id="tenant-a",
        raw_claims={"role": "user"},
    )

    authorization = arena_gateway_routes._wallet_authorization(principal)
    delegated_token = authorization.removeprefix("Bearer ")
    claims = jwt.decode(
        delegated_token,
        "wallet-delegation-test-secret",
        algorithms=[settings.WALLET_SERVICE_JWT_ALGORITHM],
    )
    assert claims["sub"] == "1"
    assert claims["tenant_id"] == "1"


async def test_demo_identity_cannot_read_live_wallet_data(api_client):
    response = await api_client.get(
        "/api/v1/arena/wallet/balance",
        headers={"Authorization": f"Bearer {_token('demo')}"},
    )

    assert response.status_code == 403
