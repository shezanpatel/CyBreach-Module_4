"""FastAPI route handlers for leaderboard operations."""
from __future__ import annotations
from app.services import improvement_service
from app.services.improvement_service import ImprovementService
from typing import Annotated
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from app.db.redis_client import get_redis_metrics, is_redis_healthy
from app.exceptions import RedisUnavailableError
from app.models.schemas import (
    OptInRequest,
    OptOutRequest,
    ConsentResponse,
    DeleteUserResponse,
    HealthResponse,
    IncrementRequest,
    IncrementResponse,
    LeaderboardResponse,
    MetricsResponse,
    RankResponse,
    ResetLeaderboardResponse,
    ScoreRequest,
    ScoreResponse,
    ImprovementResponse,
)
from app.services.leaderboard_service import (
    LeaderboardService,
    get_leaderboard_service,
)
router = APIRouter(tags=["Leaderboard"])
ServiceDep = Annotated[LeaderboardService, Depends(get_leaderboard_service)]
@router.post(
    "/score",
    response_model=ScoreResponse,
    status_code=status.HTTP_200_OK,
    summary="Create or update a player score",
)
def set_score(
    payload: ScoreRequest,
    service: ServiceDep,
) -> ScoreResponse:
    """Create or overwrite a player's score."""
    if payload.tenant_id is not None:
        if not all([
            payload.industry,
            payload.region,
            payload.size,
        ]):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "industry, region, and size are required "
                    "when tenant_id is provided"
                ),
            )
        # Tenant-aware path: writes membership + all four absolute
        # leaderboards through one Redis pipeline.
        service.set_tenant_score(
            username=payload.username,
            score=payload.score,
            tenant_id=payload.tenant_id,
            industry=payload.industry,
            region=payload.region,
            size=payload.size,
        )
        score = payload.score
    else:
        # Existing API behavior remains unchanged.
        score = service.set_score(
            payload.username,
            payload.score,
        )
    return ScoreResponse(
        username=payload.username,
        score=score,
    )
@router.post(
    "/increment",
    response_model=IncrementResponse,
    status_code=status.HTTP_200_OK,
    summary="Atomically increment a player score",
)
def increment_score(
    payload: IncrementRequest,
    service: ServiceDep,
) -> IncrementResponse:
    """Increment a player's score atomically."""
    new_score = service.increment_score(
        payload.username,
        payload.increment,
    )
    return IncrementResponse(
        username=payload.username,
        score=new_score,
        increment=payload.increment,
    )
@router.get(
    "/leaderboard",
    response_model=LeaderboardResponse,
    summary="Get top N players",
)
def get_leaderboard(
    service: ServiceDep,
    limit: int = Query(default=10, ge=1, le=1000, description="Number of top players"),
) -> LeaderboardResponse:
    """Return the highest-scoring players ranked by score."""
    entries, total = service.get_top_players(limit)
    return LeaderboardResponse(
        total_players=total,
        limit=limit,
        entries=entries,
    )
@router.get(
    "/rank/{username}",
    response_model=RankResponse,
    summary="Get player rank and score",
)
def get_rank(username: str, service: ServiceDep) -> RankResponse:
    """Look up a player's current score and rank."""
    score, rank = service.get_rank(username.strip())
    return RankResponse(username=username.strip(), score=score, rank=rank)
@router.delete(
    "/user/{username}",
    response_model=DeleteUserResponse,
    summary="Remove a player",
)
def delete_user(
    username: str,
    service: ServiceDep,
) -> DeleteUserResponse:
    """Delete a player."""
    service.delete_user(username.strip())
    return DeleteUserResponse(username=username.strip())
@router.delete(
    "/leaderboard",
    response_model=ResetLeaderboardResponse,
    summary="Reset leaderboard",
)
def reset_leaderboard(
    service: ServiceDep,
) -> ResetLeaderboardResponse:
    """Reset the leaderboard."""
    service.reset_leaderboard()
    return ResetLeaderboardResponse()
@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health check",
)
def health_check() -> HealthResponse:
    """Return application and Redis health status."""
    redis_ok = is_redis_healthy()
    return HealthResponse(
        status="healthy" if redis_ok else "degraded",
        redis="connected" if redis_ok else "disconnected",
        app="running",
    )
@router.post(
    "/opt-in",
    response_model=ConsentResponse,
    status_code=status.HTTP_200_OK,
    summary="Opt a tenant into leaderboard participation",
)
def opt_in(
    payload: OptInRequest,
    service: ServiceDep,
) -> ConsentResponse:
    """Register a tenant for leaderboard participation."""
    service.opt_in_tenant(
        tenant_id=payload.tenant_id,
        industry=payload.industry,
        region=payload.region,
        size=payload.size,
    )
    return ConsentResponse(
        tenant_id=payload.tenant_id,
        action="opt-in",
        message="Tenant opted into leaderboard participation",
    )
@router.post(
    "/opt-out",
    response_model=ConsentResponse,
    status_code=status.HTTP_200_OK,
    summary="Opt a tenant out of leaderboard participation",
)
def opt_out(
    payload: OptOutRequest,
    service: ServiceDep,
) -> ConsentResponse:
    """Remove all leaderboard data associated with a tenant."""
    service.opt_out_tenant(payload.tenant_id)
    return ConsentResponse(
        tenant_id=payload.tenant_id,
        action="opt-out",
        message="Tenant opted out and leaderboard data was purged",
    )
@router.get(
    "/improvement",
    response_model=ImprovementResponse,
    summary="Get tenant improvement rankings",
)
def get_improvement(
    dimension: str = Query(
        default="global",
        description="global, industry, region, or size",
    ),
    value: str | None = Query(
        default=None,
        description="Dimension value for industry, region, or size",
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=1000,
        description="Number of tenants to return",
    ),
) -> ImprovementResponse:
    """Return tenants ranked by improvement."""
    improvement_service = ImprovementService()
    try:
        entries = improvement_service.get_improvement(
            dimension=dimension,
            value=value,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return ImprovementResponse(
        total_tenants=len(entries),
        limit=limit,
        entries=entries,
    )
@router.get(
    "/metrics",
    response_model=MetricsResponse,
    summary="Redis server metrics",
)
def metrics() -> MetricsResponse:
    """Expose Redis INFO metrics for observability."""
    if not is_redis_healthy():
        raise RedisUnavailableError("Redis is not available for metrics collection")
    return MetricsResponse(metrics=get_redis_metrics())


@router.get("/leaderboard/{dimension}", response_model=LeaderboardResponse)
def get_dimension_leaderboard(
    dimension: str,
    view: str = Query("absolute", pattern="^(absolute|improvement)$"),
    region: str = Query(None),
    industry: str = Query(None),
    size_band: str = Query(None),
    limit: int = Query(10, ge=1, le=100),
    service: ServiceDep = None,
):
    valid_dims = {"global", "industry", "region", "size"}
    if dimension not in valid_dims:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid dimension {dimension}. Allowed: {sorted(valid_dims)}",
        )
    entries, total = service.get_top_players(limit=limit)
    return LeaderboardResponse(
        dimension=dimension,
        view=view,
        total_players=total,
        limit=limit,
        entries=entries,
    )
