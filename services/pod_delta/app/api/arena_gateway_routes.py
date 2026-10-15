"""Authenticated browser gateway for the independently deployed Arena pods."""

from __future__ import annotations

import asyncio
import copy
import ipaddress
import secrets
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from urllib.parse import quote
from uuid import UUID, uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response
from jose import jwt
from pydantic import BaseModel, ConfigDict, Field

from app.core.security import AuthenticatedPrincipal, get_current_principal
from app.core.settings import settings

router = APIRouter(prefix="/api/v1/arena", tags=["Arena Gateway"])
auth_router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])
_demo_account_lock = threading.RLock()


class BenchmarkRequest(BaseModel):
    industry: str = Field(min_length=1, max_length=100)
    region: str = Field(min_length=1, max_length=100)
    size_band: str = Field(min_length=1, max_length=100)


class DemoCredentials(BaseModel):
    account_id: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=200)


class DemoTopUpRequest(BaseModel):
    package_id: Literal["starter", "operator", "enterprise"]
    payment_method: Literal["demo_card", "demo_upi"]
    checkout_id: UUID
    customer_name: str = Field(min_length=2, max_length=120)
    customer_email: str = Field(
        min_length=5,
        max_length=254,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    )
    billing_address: str = Field(min_length=5, max_length=300)

    model_config = ConfigDict(str_strip_whitespace=True)


class DemoEngagementRequest(BaseModel):
    campaign_id: str = Field(min_length=1, max_length=100)
    campaign_title: str = Field(min_length=1, max_length=160)
    credit_cost: int = Field(ge=1, le=10000)


DEMO_PACKAGES = {
    "starter": {"credits": 250, "label": "Starter Pack", "demo_amount": 4.99},
    "operator": {"credits": 750, "label": "Operator Pack", "demo_amount": 9.99},
    "enterprise": {"credits": 2000, "label": "Enterprise Pack", "demo_amount": 19.99},
}


def _base_url(value: str | None, service: str) -> str:
    if not value:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{service} URL is not configured",
        )
    return value.rstrip("/")


async def _proxy(
    *,
    method: str,
    base_url: str,
    path: str,
    authorization: str,
    params: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
) -> Response:
    try:
        async with httpx.AsyncClient(
            timeout=settings.UPSTREAM_TIMEOUT_SECONDS
        ) as client:
            upstream = await client.request(
                method,
                f"{base_url}{path}",
                params=params,
                json=payload,
                headers={"Authorization": authorization},
            )
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="The requested pod did not respond before the gateway timeout",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The requested pod could not be reached",
        ) from exc

    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type", "application/json"),
    )


async def _probe(
    client: httpx.AsyncClient,
    name: str,
    base_url: str | None,
    path: str,
) -> dict[str, str]:
    if not base_url:
        return {"service": name, "status": "not_configured"}
    try:
        response = await client.get(f"{base_url.rstrip('/')}{path}")
    except httpx.TimeoutException:
        return {"service": name, "status": "timeout"}
    except httpx.RequestError:
        return {"service": name, "status": "unreachable"}
    if not response.is_success:
        return {"service": name, "status": "unhealthy"}
    if name == "pod_delta":
        try:
            if response.json().get("status") != "healthy":
                return {"service": name, "status": "degraded"}
        except ValueError:
            return {"service": name, "status": "unhealthy"}
    return {"service": name, "status": "healthy"}


def _is_loopback(host: str | None) -> bool:
    if not host:
        return False
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return host.lower() == "localhost"


def _new_demo_account() -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "balance": settings.DEMO_STARTING_CREDITS,
        "total_visits": 128,
        "engagements": [],
        "receipts": [],
        "checkouts": {},
        "transactions": [
            {
                "id": "demo-seed-1",
                "entry_type": "credit",
                "amount": settings.DEMO_STARTING_CREDITS,
                "currency": "CR",
                "reference_id": "Welcome demo credits",
                "created_at": now.isoformat(),
            }
        ],
        "notifications": [
            {
                "id": "demo-welcome",
                "title": "Demo account ready",
                "message": "Explore the Arena. Wallet, payments, and scan results are simulated.",
                "channel": "in-app",
                "status": "delivered",
                "created_at": now.isoformat(),
            }
        ],
    }


_demo_account = _new_demo_account()


def _require_local_demo(
    request: Request,
    principal: AuthenticatedPrincipal,
) -> None:
    if (
        principal.raw_claims.get("role") != "demo"
        or settings.ENVIRONMENT.lower() != "development"
        or not settings.DEV_DEMO_AUTH_ENABLED
        or not _is_loopback(request.client.host if request.client else None)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This simulated feature is available only to the local demo account",
        )


def _demo_snapshot() -> dict[str, Any]:
    with _demo_account_lock:
        account = copy.deepcopy(_demo_account)
    return {
        "wallet": {
            "available_balance": account["balance"],
            "currency": "CR",
        },
        "transactions": {
            "entries": account["transactions"],
            "total": len(account["transactions"]),
        },
        "receipts": {
            "entries": account["receipts"],
            "total": len(account["receipts"]),
        },
        "notifications": {
            "notifications": account["notifications"],
            "total": len(account["notifications"]),
        },
        "preferences": {
            "email_enabled": False,
            "in_app_enabled": True,
            "frequency": "immediate",
        },
        "analytics": {
            "tenant_name": "Arena Demo Organization",
            "resilience_score": min(
                98,
                82 + len(account["engagements"]) * 2,
            ),
            "active_users": 1,
            "total_users": 1,
            "total_visits": account["total_visits"],
            "uptime_percentage": 99.9,
            "error_count": 0,
            "total_engagements": len(account["engagements"]),
            "source": "simulated_demo",
        },
        "engagements": account["engagements"],
    }


def _wallet_authorization(principal: AuthenticatedPrincipal) -> str:
    if not settings.WALLET_SERVICE_JWT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Wallet service delegation secret is not configured",
        )
    now = datetime.now(timezone.utc)
    delegated_token = jwt.encode(
        {
            "sub": principal.subject,
            "tenant_id": principal.subject,
            "role": principal.raw_claims.get("role"),
            "iat": now,
            "exp": now + timedelta(minutes=2),
        },
        settings.WALLET_SERVICE_JWT_SECRET,
        algorithm=settings.WALLET_SERVICE_JWT_ALGORITHM,
    )
    return f"Bearer {delegated_token}"


@auth_router.post("/demo")
def create_local_demo_token(
    payload: DemoCredentials,
    request: Request,
) -> dict[str, Any]:
    if (
        settings.ENVIRONMENT.lower() != "development"
        or not settings.DEV_DEMO_AUTH_ENABLED
        or not _is_loopback(request.client.host if request.client else None)
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Development demo authentication is unavailable",
        )
    if (
        not secrets.compare_digest(
            payload.account_id.strip().casefold(),
            settings.DEMO_ACCOUNT_ID.strip().casefold(),
        )
        or not secrets.compare_digest(
            payload.password,
            settings.DEMO_ACCOUNT_PASSWORD,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid demo account ID or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = jwt.encode(
        {
            "sub": "1",
            "tenant_id": "demo-tenant",
            "role": "demo",
            "name": "Arena Demo Manager",
            "iat": now,
            "exp": expires,
        },
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "tenant_id": "demo-tenant",
        "subject": "1",
        "mode": "development_demo",
        "display_name": "Arena Demo Manager",
    }


@router.get("/connections")
async def get_connections(
    _principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> dict[str, Any]:
    probes = (
        ("pod_delta", settings.POD_DELTA_INTERNAL_URL, "/api/v1/integration/health"),
        ("pod_beta_campaigns", settings.POD_BETA_CAMPAIGN_URL, "/campaigns?limit=1"),
        ("pod_beta_engagements", settings.POD_BETA_ENGAGEMENT_URL, "/openapi.json"),
        ("pod_gamma", settings.POD_GAMMA_URL, "/health"),
        ("wallet_service", settings.WALLET_SERVICE_URL, "/"),
    )
    async with httpx.AsyncClient(timeout=settings.UPSTREAM_TIMEOUT_SECONDS) as client:
        results = await asyncio.gather(
            *(_probe(client, name, url, path) for name, url, path in probes)
        )
    return {
        "pod_delta": results[0],
        "upstreams": results[1:],
        "mode": "development_demo"
        if settings.ENVIRONMENT.lower() == "development"
        else "authenticated",
    }


@router.get("/demo/state")
def get_demo_state(
    request: Request,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> dict[str, Any]:
    _require_local_demo(request, principal)
    return _demo_snapshot()


@router.post("/demo/top-up")
def demo_top_up(
    payload: DemoTopUpRequest,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> dict[str, Any]:
    _require_local_demo(request, principal)
    package = DEMO_PACKAGES[payload.package_id]
    now = datetime.now(timezone.utc).isoformat()
    checkout_key = str(payload.checkout_id)
    with _demo_account_lock:
        existing_receipt = _demo_account["checkouts"].get(checkout_key)
        if existing_receipt:
            return {
                "payment": {
                    **existing_receipt["payment"],
                    "message": "This demo checkout was already completed.",
                },
                "receipt": copy.deepcopy(existing_receipt),
                "state": _demo_snapshot(),
            }

        receipt_number = f"DEMO-{uuid4().hex[:12].upper()}"
        amount = round(package["demo_amount"], 2)
        method_label = (
            "Demo card · ending 4242"
            if payload.payment_method == "demo_card"
            else "Demo UPI · demo@arena.test"
        )
        receipt = {
            "id": receipt_number,
            "receipt_number": receipt_number,
            "status": "simulated_success",
            "issued_at": now,
            "customer": {
                "name": payload.customer_name,
                "email": payload.customer_email,
                "billing_address": payload.billing_address,
            },
            "payment": {
                "method": payload.payment_method,
                "method_label": method_label,
                "reference": receipt_number,
                "amount": amount,
                "currency": "USD",
            },
            "line_items": [
                {
                    "description": package["label"],
                    "quantity": 1,
                    "credits": package["credits"],
                    "amount": amount,
                }
            ],
            "subtotal": amount,
            "tax": 0.0,
            "total": amount,
            "currency": "USD",
            "credits_added": package["credits"],
            "notice": "Simulated demo purchase. No money was charged.",
        }
        _demo_account["balance"] += package["credits"]
        _demo_account["transactions"].insert(
            0,
            {
                "id": receipt_number,
                "entry_type": "credit",
                "amount": package["credits"],
                "currency": "CR",
                "reference_id": f"{package['label']} · {receipt_number}",
                "created_at": now,
            },
        )
        _demo_account["receipts"].insert(0, receipt)
        _demo_account["checkouts"][checkout_key] = receipt
        _demo_account["notifications"].insert(
            0,
            {
                "id": f"demo-notification-{len(_demo_account['notifications']) + 1}",
                "title": "Demo top-up successful",
                "message": f"{package['credits']} demo credits were added. No payment was processed.",
                "channel": "in-app",
                "status": "delivered",
                "created_at": now,
            },
        )
        _demo_account["total_visits"] += 1
    return {
        "payment": {
            "status": "simulated_success",
            "amount": amount,
            "currency": "USD",
            "method": payload.payment_method,
            "message": "Demo payment approved. No money was charged.",
        },
        "receipt": receipt,
        "state": _demo_snapshot(),
    }


@router.post("/demo/engagements")
def run_demo_engagement(
    payload: DemoEngagementRequest,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> dict[str, Any]:
    _require_local_demo(request, principal)
    now = datetime.now(timezone.utc).isoformat()
    finding_count = (sum(ord(char) for char in payload.campaign_id) % 4) + 1
    engagement_id = f"demo-run-{int(datetime.now(timezone.utc).timestamp() * 1000)}"
    results = [
        {
            "id": f"{engagement_id}-finding-{index + 1}",
            "severity": ("medium", "low", "high", "low")[index % 4],
            "title": title,
            "status": "simulated",
        }
        for index, title in enumerate(
            (
                "Unpatched service detected",
                "Sample credential exposure",
                "Missing endpoint protection",
                "Outdated TLS configuration",
            )[:finding_count]
        )
    ]
    with _demo_account_lock:
        if _demo_account["balance"] < payload.credit_cost:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Not enough demo credits. Use the simulated top-up to add more.",
            )
        _demo_account["balance"] -= payload.credit_cost
        _demo_account["total_visits"] += 1
        engagement = {
            "id": engagement_id,
            "campaign_id": payload.campaign_id,
            "campaign_title": payload.campaign_title,
            "status": "simulated_completed",
            "credit_cost": payload.credit_cost,
            "finding_count": finding_count,
            "results": results,
            "completed_at": now,
            "notice": "Simulation only. No targets were contacted or security scans executed.",
        }
        _demo_account["engagements"].insert(0, engagement)
        _demo_account["transactions"].insert(
            0,
            {
                "id": f"{engagement_id}-debit",
                "entry_type": "debit",
                "amount": payload.credit_cost,
                "currency": "CR",
                "reference_id": payload.campaign_title,
                "created_at": now,
            },
        )
        _demo_account["notifications"].insert(
            0,
            {
                "id": f"{engagement_id}-notification",
                "title": "Demo simulation completed",
                "message": f"{payload.campaign_title}: {finding_count} simulated findings.",
                "channel": "in-app",
                "status": "delivered",
                "created_at": now,
            },
        )
    return {"engagement": engagement, "state": _demo_snapshot()}


@router.post("/demo/reset")
def reset_demo_account(
    request: Request,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> dict[str, Any]:
    global _demo_account
    _require_local_demo(request, principal)
    with _demo_account_lock:
        _demo_account = _new_demo_account()
    return _demo_snapshot()


@router.get("/engagement/recommendations")
async def get_engagement_recommendations(
    request: Request,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> Response:
    tenant_id = quote(principal.tenant_id, safe="")
    return await _proxy(
        method="GET",
        base_url=_base_url(settings.POD_BETA_ENGAGEMENT_URL, "Pod Beta engagement API"),
        path=f"/engagement/recommendations/{tenant_id}",
        authorization=request.headers["authorization"],
    )


@router.get("/campaigns")
async def get_campaigns(
    request: Request,
    _principal: AuthenticatedPrincipal = Depends(get_current_principal),
    tier: str | None = None,
    region: str | None = None,
    technique: str | None = None,
    regulation: str | None = None,
    asset_criticality: str | None = None,
    search: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Response:
    params = {
        key: value
        for key, value in {
            "tier": tier,
            "region": region,
            "technique": technique,
            "regulation": regulation,
            "asset_criticality": asset_criticality,
            "search": search,
            "limit": limit,
            "offset": offset,
        }.items()
        if value is not None
    }
    return await _proxy(
        method="GET",
        base_url=_base_url(settings.POD_BETA_CAMPAIGN_URL, "Pod Beta campaign API"),
        path="/campaigns",
        authorization=request.headers["authorization"],
        params=params,
    )


@router.get("/leaderboard")
async def get_leaderboard(
    request: Request,
    _principal: AuthenticatedPrincipal = Depends(get_current_principal),
    limit: int = Query(10, ge=1, le=100),
) -> Response:
    return await _proxy(
        method="GET",
        base_url=_base_url(settings.POD_GAMMA_URL, "Pod Gamma API"),
        path="/leaderboard",
        authorization=request.headers["authorization"],
        params={"limit": limit},
    )


@router.get("/benchmark/cohorts")
async def get_benchmark_cohorts(
    request: Request,
    _principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> Response:
    return await _proxy(
        method="GET",
        base_url=_base_url(settings.POD_GAMMA_URL, "Pod Gamma API"),
        path="/benchmark/cohorts",
        authorization=request.headers["authorization"],
    )


@router.post("/benchmark")
async def get_benchmark(
    request: Request,
    payload: BenchmarkRequest,
    _principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> Response:
    return await _proxy(
        method="POST",
        base_url=_base_url(settings.POD_GAMMA_URL, "Pod Gamma API"),
        path="/benchmark",
        authorization=request.headers["authorization"],
        payload=payload.model_dump(),
    )


@router.get("/wallet/balance")
async def get_wallet_balance(
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> Response:
    if principal.raw_claims.get("role") == "demo":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Wallet data is unavailable to the development demo identity",
        )
    user_id = quote(principal.subject, safe="")
    return await _proxy(
        method="GET",
        base_url=_base_url(settings.WALLET_SERVICE_URL, "Wallet service"),
        path=f"/wallet/balance/{user_id}",
        authorization=_wallet_authorization(principal),
    )


@router.get("/wallet/history")
async def get_wallet_history(
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> Response:
    if principal.raw_claims.get("role") == "demo":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Wallet history is unavailable to the development demo identity",
        )
    user_id = quote(principal.subject, safe="")
    return await _proxy(
        method="GET",
        base_url=_base_url(settings.WALLET_SERVICE_URL, "Wallet service"),
        path=f"/wallet/history/{user_id}",
        authorization=_wallet_authorization(principal),
        params={"limit": limit, "offset": offset},
    )


@router.get("/analytics/dashboard")
async def get_tenant_analytics(
    request: Request,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> Response:
    tenant_id = quote(principal.tenant_id, safe="")
    return await _proxy(
        method="GET",
        base_url=_base_url(settings.POD_DELTA_INTERNAL_URL, "Pod Delta API"),
        path=f"/api/v1/analytics/dashboard/{tenant_id}",
        authorization=request.headers["authorization"],
    )


@router.get("/notifications")
async def get_tenant_notifications(
    request: Request,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    limit: int = Query(100, ge=1, le=1000),
) -> Response:
    if principal.raw_claims.get("role") == "demo":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Notifications are unavailable to the development demo identity",
        )
    try:
        user_id = int(principal.subject)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pod Delta notifications require a numeric user ID in the authenticated subject",
        ) from exc
    return await _proxy(
        method="GET",
        base_url=_base_url(settings.POD_DELTA_INTERNAL_URL, "Pod Delta API"),
        path=f"/api/v1/notifications/user/{user_id}",
        authorization=request.headers["authorization"],
        params={"limit": limit},
    )


@router.get("/preferences")
async def get_tenant_preferences(
    request: Request,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> Response:
    if principal.raw_claims.get("role") == "demo":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Preferences are unavailable to the development demo identity",
        )
    try:
        user_id = int(principal.subject)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pod Delta preferences require a numeric user ID in the authenticated subject",
        ) from exc
    return await _proxy(
        method="GET",
        base_url=_base_url(settings.POD_DELTA_INTERNAL_URL, "Pod Delta API"),
        path=f"/api/v1/preferences/{user_id}",
        authorization=request.headers["authorization"],
    )
