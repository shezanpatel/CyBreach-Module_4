import json
from contextlib import asynccontextmanager
from secrets import compare_digest

from fastapi import Depends, FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.api.v1.budget_alert import router as budget_alert_router
from app.api.v1.currency import router as currency_router
from app.api.v1.reconciliation import router as reconciliation_router
from app.api.v1.subscription import router as subscription_router
from app.api.v1.wallet import router as wallet_router
from app.api.v1.wallet_integration import router as wallet_integration_router
from app.core.config import settings
from app.core.database import Base, engine
from app.core.exceptions import (
    InsufficientBalance,
    WalletNotFound,
    WalletPaused,
)
from app.core.security import (
    authenticate_middleware_request,
    authenticate_request,
    authorize_tenant,
    require_admin,
)
from app.events.kafka_producer import start_producer, stop_producer
from app.tasks.scheduler import start_scheduler, stop_scheduler

from app.models.budget_alert import BudgetAlert
from app.models.currency_rate import CurrencyRate
from app.models.idempotency_key import IdempotencyKey
from app.models.wallet_balance import WalletBalance
from app.models.wallet_credit import WalletCredit
from app.models.wallet_ledger import WalletLedger
from app.models.wallet_ledger_entry import WalletLedgerEntry


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)

    await start_producer()
    print("✅ Kafka producer started")

    start_scheduler()
    print("✅ Wallet reconciliation scheduler started")

    try:
        yield
    finally:
        stop_scheduler()
        print("🛑 Wallet reconciliation scheduler stopped")

        await stop_producer()
        print("🛑 Kafka producer stopped")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)


PUBLIC_PATHS = {
    "/",
    "/docs",
    "/redoc",
    "/openapi.json",
}


SERVICE_KEY_OPERATIONS = {
    ("POST", "/wallet/debit"),
    ("POST", "/wallet/credit"),
}


ADMIN_ONLY_OPERATIONS = {
    ("GET", "/reconciliation/run"),
    ("POST", "/currency/rates"),
}


def _json_error(
    status_code: int,
    detail: str,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail},
    )


@app.middleware("http")
async def wallet_security_boundary(
    request: Request,
    call_next,
):
    path = request.url.path
    method = request.method.upper()

    if path in PUBLIC_PATHS:
        return await call_next(request)

    try:
        principal = authenticate_middleware_request(request)
    except Exception as exc:
        status_code = getattr(
            exc,
            "status_code",
            status.HTTP_401_UNAUTHORIZED,
        )
        detail = getattr(
            exc,
            "detail",
            "Authentication failed",
        )
        return _json_error(status_code, detail)

    operation = (method, path)

    if operation in SERVICE_KEY_OPERATIONS:
        supplied_key = request.headers.get("X-Service-API-Key")

        if (
            not supplied_key
            or not compare_digest(
                supplied_key,
                settings.SERVICE_API_KEY,
            )
        ):
            return _json_error(
                status.HTTP_403_FORBIDDEN,
                "Valid service API key is required",
            )

    if operation in ADMIN_ONLY_OPERATIONS:
        try:
            require_admin(request)
        except Exception as exc:
            return _json_error(
                getattr(
                    exc,
                    "status_code",
                    status.HTTP_403_FORBIDDEN,
                ),
                getattr(
                    exc,
                    "detail",
                    "Administrator role is required",
                ),
            )

        return await call_next(request)

    path_tenant_id = None

    if path.startswith("/wallet/balance/"):
        path_tenant_id = path.removeprefix(
            "/wallet/balance/"
        ).split("/")[0]

    elif path.startswith("/wallet/history/"):
        path_tenant_id = path.removeprefix(
            "/wallet/history/"
        ).split("/")[0]

    elif path.startswith("/wallet/transactions/"):
        path_tenant_id = path.removeprefix(
            "/wallet/transactions/"
        ).split("/")[0]

    elif path.startswith("/budget-alert/"):
        remainder = path.removeprefix("/budget-alert/")
        candidate = remainder.split("/")[0]

        if candidate:
            path_tenant_id = candidate

    elif path.startswith("/reconciliation/tenant/"):
        path_tenant_id = path.removeprefix(
            "/reconciliation/tenant/"
        ).split("/")[0]

    elif path.startswith("/reconciliation/unpause/"):
        path_tenant_id = path.removeprefix(
            "/reconciliation/unpause/"
        ).split("/")[0]

    if path_tenant_id:
        try:
            authorize_tenant(
                request,
                path_tenant_id,
            )
        except Exception as exc:
            return _json_error(
                getattr(
                    exc,
                    "status_code",
                    status.HTTP_403_FORBIDDEN,
                ),
                getattr(
                    exc,
                    "detail",
                    "Cross-tenant access is forbidden",
                ),
            )

    body_tenant_paths = {
        "/wallet/deposit",
        "/wallet/withdraw",
        "/wallet/credit",
        "/wallet/debit",
        "/subscription/signup",
        "/subscription/renew",
        "/subscription/cancel",
        "/subscription/change-tier",
        "/budget-alert",
    }

    if (
        method in {"POST", "PUT", "PATCH"}
        and path in body_tenant_paths
    ):
        raw_body = await request.body()

        if raw_body:
            try:
                payload = json.loads(raw_body)
            except json.JSONDecodeError:
                payload = None

            if isinstance(payload, dict):
                requested_user_id = payload.get("user_id")

                if isinstance(requested_user_id, str):
                    try:
                        authorize_tenant(
                            request,
                            requested_user_id,
                        )
                    except Exception as exc:
                        return _json_error(
                            getattr(
                                exc,
                                "status_code",
                                status.HTTP_403_FORBIDDEN,
                            ),
                            getattr(
                                exc,
                                "detail",
                                "Cross-tenant access is forbidden",
                            ),
                        )

    return await call_next(request)


@app.exception_handler(WalletNotFound)
async def wallet_not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "detail": "Wallet does not exist",
        },
    )


@app.exception_handler(InsufficientBalance)
async def insufficient_balance_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={
            "detail": "Insufficient balance",
        },
    )


@app.exception_handler(WalletPaused)
async def wallet_paused_handler(request, exc):
    return JSONResponse(
        status_code=423,
        content={
            "detail": str(exc),
        },
    )


authenticated_dependencies = [
    Depends(authenticate_request),
]


app.include_router(
    wallet_router,
    dependencies=authenticated_dependencies,
)

app.include_router(
    wallet_integration_router,
    dependencies=authenticated_dependencies,
)

app.include_router(
    reconciliation_router,
    dependencies=authenticated_dependencies,
)

app.include_router(
    subscription_router,
    dependencies=authenticated_dependencies,
)

app.include_router(
    currency_router,
    dependencies=authenticated_dependencies,
)

app.include_router(
    budget_alert_router,
    dependencies=authenticated_dependencies,
)


@app.get("/")
def health_check():
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
    }
