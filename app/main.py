from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import Response

from app.core.logging import configure_logging, get_logger
from app.core.settings import settings
from app.database.connection import Base, engine
from app.database.db_connection import Base as AnalyticsBase
from app.database.db_connection import engine as analytics_engine

from app.models.notification import Notification  # noqa: F401
from app.models.notification_preference import NotificationPreference  # noqa: F401
from app.models.analytics_metrics import AnalyticsMetric  # noqa: F401

from app.api.notification_routes import router as notification_router
from app.api.preference_routes import router as preference_router
from app.api.analytics_engine_routes import router as analytics_router
from app.api.integration_routes import router as integration_router
from app.api.websocket_routes import router as websocket_router
from app.services.integration.metrics import metrics_output
from app.integration.runtime import start_integration, stop_integration

from app.core.exceptions import (
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler,
)

from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import (
    AnalyticsNotFoundException,
    AnalyticsValidationException,
    AnalyticsDatabaseException,
    analytics_not_found_handler,
    analytics_validation_handler,
    analytics_database_handler,
)

configure_logging()
logger = get_logger("pod_delta.main")

Base.metadata.create_all(bind=engine)
AnalyticsBase.metadata.create_all(bind=analytics_engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup")
    await start_integration()
    yield
    await stop_integration()
    logger.info("shutdown")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="CyBreach Arena Backend",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS,
    )

app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)
app.add_exception_handler(AnalyticsNotFoundException, analytics_not_found_handler)
app.add_exception_handler(AnalyticsValidationException, analytics_validation_handler)
app.add_exception_handler(AnalyticsDatabaseException, analytics_database_handler)

app.include_router(
    notification_router,
    prefix="/api/v1/notifications",
    tags=["Notifications"],
)
app.include_router(
    preference_router,
    prefix="/api/v1/preferences",
    tags=["Preferences"],
)
app.include_router(analytics_router)
app.include_router(integration_router)
app.include_router(websocket_router)


@app.get("/", summary="Root Health Check")
async def home():
    return {
        "application": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "Running",
        "database": "Connected",
    }


@app.get("/api/v1/health", summary="Detailed Health Check")
async def health_check():
    return {
        "status": "healthy",
        "application": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/metrics", summary="Prometheus metrics")
async def prometheus_root() -> Response:
    return Response(content=metrics_output(), media_type="text/plain")
