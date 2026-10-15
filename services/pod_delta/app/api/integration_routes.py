"""Integration REST helpers: cached score and health."""

import json

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

from app.core.security import AuthenticatedPrincipal, get_current_principal
from app.integration.redis_client import get_redis
from app.integration.runtime import get_consumer, get_producer, get_websocket_manager
from app.services.integration.metrics import metrics_output

router = APIRouter(prefix="/api/v1/integration", tags=["Integration"])


@router.get("/health")
async def integration_health() -> dict:
    redis_ok = False
    try:
        redis_ok = bool(await (await get_redis()).ping())
    except Exception:
        redis_ok = False
    kafka_producer = False
    kafka_consumer = False
    ws_connections = 0
    try:
        kafka_producer = get_producer().ready
    except RuntimeError:
        pass
    try:
        kafka_consumer = get_consumer().ready
    except RuntimeError:
        pass
    try:
        ws_connections = get_websocket_manager().local_connection_count()
    except RuntimeError:
        pass

    status_value = "healthy" if redis_ok else "degraded"
    if not kafka_producer or not kafka_consumer:
        status_value = "degraded"

    return {
        "status": status_value,
        "redis": redis_ok,
        "kafka_producer": kafka_producer,
        "kafka_consumer": kafka_consumer,
        "websocket_local_connections": ws_connections,
    }


@router.get("/score/{tenant_id}")
async def get_cached_score(
    tenant_id: str,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> dict:
    if principal.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant scope mismatch",
        )
    redis = await get_redis()
    raw = await redis.get(f"score:{tenant_id}")
    cached = json.loads(raw) if raw else None
    if cached is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Score not cached for tenant",
        )
    return cached


@router.post("/analytics/flush/{tenant_id}")
async def flush_analytics(
    tenant_id: str,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> dict:
    if principal.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant scope mismatch",
        )
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Analytics reports are emitted from consumed integration events",
    )


@router.get("/metrics")
async def prometheus_metrics() -> Response:
    return Response(content=metrics_output(), media_type="text/plain")
