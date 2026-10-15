"""FastAPI application entry point with lifespan management."""
# ==========================================================
# SECURITY FEATURE (TEMPORARILY DISABLED)
#
# Reason:
# API authentication and rate limiting will be enabled after
# the API module is merged by the teammate.
#
# To enable:
# 1. Uncomment the import.
# 2. Uncomment the dependency/decorator.
# ==========================================================
from __future__ import annotations

from datetime import datetime
from typing import List, AsyncIterator
from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from app.award_repository import find_award, find_awards, save_award
from app.db import SessionLocal
from app.models import UserProfile
from app.streak import update_streak
from app.user_repository import find_user, save_user

async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session

class ScoreInputItem(BaseModel):
    client_id: str = Field(min_length=3, max_length=50)
    security_score: float = Field(ge=0.0, le=100.0)


class StreamAnalyticsPayload(BaseModel):
    metrics: List[ScoreInputItem] = Field(default_factory=list)


class AchievementCheckPayload(BaseModel):
    type: str
    key: str
    tenant_id: str
    evidence_ref: str | None = None

    @field_validator("evidence_ref")
    @classmethod
    def validate_evidence_ref(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        parts = value.split(":")

        valid_mod2 = (
            len(parts) == 4
            and parts[0] == "mod2"
            and all(parts[1:])
        )

        valid_mod2_verdict = (
            len(parts) == 3
            and parts[0] == "mod2"
            and parts[1] == "verdict"
            and parts[2]
        )

        valid_mod3 = (
            len(parts) == 4
            and parts[0] == "mod3"
            and all(parts[1:])
        )

        if not (
            valid_mod2
            or valid_mod2_verdict
            or valid_mod3
        ):
            raise ValueError(
                "evidence_ref must use a valid mod2 or mod3 format"
            )

        return value


class StreakVerificationPayload(BaseModel):
    previous_login_timestamp: str
    current_login_timestamp: str
    active_streak: int = Field(ge=0)
    user_id: str = "api-user"
    tenant_id: str = "default"


def seed_corporate_profiles() -> List[dict]:
    return [
        {
            "client_id": f"CORP-{index:03d}",
            "company_name": f"Synthetic Corporation {index:03d}",
            "security_score": float(50 + (index * 7) % 51),
        }
        for index in range(1, 51)
    ]


SYNTHETIC_PROFILES = seed_corporate_profiles()




import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

#import app
from app.api.leaderboard import router as leaderboard_router
from app.api.benchmark import router as benchmark_router
from app.config import get_settings
from app.db.redis_client import close_redis, init_redis
from app.exceptions import (
    InvalidScoreError,
    InvalidTenantMetadataError,
    LeaderboardError,
    NegativeScoreError,
    RedisTimeoutError,
    RedisUnavailableError,
    UserNotFoundError,
)
#from slowapi.errors import RateLimitExceeded
#from slowapi.middleware import SlowAPIMiddleware

#from app.rate_limit import limiter

from app.models.schemas import ErrorResponse
from app.utils.logger import get_logger, setup_logging

settings = get_settings()
logger = get_logger("main")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Manage startup and graceful shutdown lifecycle."""
    setup_logging(settings.log_level)  # type: ignore[arg-type]
    logger.info("Starting %s | env=%s", settings.app_name, settings.app_env)

    try:
        init_redis(settings)
    except RedisUnavailableError as exc:
        logger.error("Startup Redis connection failed: %s", exc.message)

    yield

    logger.info("Shutting down %s", settings.app_name)
    close_redis()
    logger.info("Graceful shutdown complete")


def create_app() -> FastAPI:
    """Application factory for production and test usage."""
    app = FastAPI(
        title=settings.app_name,
        description=(
            "High-performance leaderboard microservice powered by Redis Sorted Sets. "
            "Supports real-time score updates and O(log N) rank lookups."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    #app.state.limiter = limiter
    #app.add_middleware(SlowAPIMiddleware)

    app.add_middleware(
        CORSMiddleware,
        #allow_origins=settings.allowed_origins,
        #allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
# =====================================================
# SECURITY MIDDLEWARE (Disabled for teammate integration)
# Uncomment after API authentication is merged.
# =====================================================
    # @app.middleware("http")
    # async def security_headers(request, call_next):
    #     response = await call_next(request)

    #     response.headers["X-Content-Type-Options"] = "nosniff"
    #     response.headers["X-Frame-Options"] = "DENY"
    #     response.headers["Referrer-Policy"] = "strict-origin"
    #     response.headers["Permissions-Policy"] = "geolocation=()"
    #     response.headers["Content-Security-Policy"] = "default-src 'self'"

    #     return response

    _register_exception_handlers(app)
    app.include_router(leaderboard_router)
    app.include_router(benchmark_router)


    @app.post("/api/v1/analytics")
    async def analytics(payload: StreamAnalyticsPayload):
        metrics = payload.metrics

        if not metrics:
            metrics = [
                ScoreInputItem(
                    client_id=profile["client_id"],
                    security_score=profile["security_score"],
                )
                for profile in SYNTHETIC_PROFILES
            ]

        average_score = sum(
            item.security_score for item in metrics
        ) / len(metrics)

        return {
            "status": "processed",
            "records_processed": len(metrics),
            "average_security_score": round(average_score, 2),
            "metrics": [item.model_dump() for item in metrics],
        }


    @app.post("/achievement/check")
    async def check_achievement(
        payload: AchievementCheckPayload,
        session: AsyncSession = Depends(get_session),
    ):
        badge_id = payload.key

        existing_award = await find_award(
            session,
            badge_id,
            payload.tenant_id,
        )

        if existing_award is not None:
            return {
                "status": "already_awarded",
                "award_id": existing_award.award_id,
                "badge_id": existing_award.badge_id,
                "tenant_id": existing_award.tenant_id,
                "awarded_at": existing_award.awarded_at,
                "evidence_ref": existing_award.evidence_ref,
            }

        award = await save_award(
            session,
            badge_id,
            payload.tenant_id,
            payload.evidence_ref,
        )

        return {
            "status": "awarded",
            "award_id": award.award_id,
            "badge_id": award.badge_id,
            "tenant_id": award.tenant_id,
            "awarded_at": award.awarded_at,
            "evidence_ref": award.evidence_ref,
        }


    @app.post("/api/v1/streaks")
    async def verify_streak(
        payload: StreakVerificationPayload,
        session: AsyncSession = Depends(get_session),
    ):
        try:
            previous_login = datetime.fromisoformat(
                payload.previous_login_timestamp.replace("Z", "+00:00")
            )

            current_login = datetime.fromisoformat(
                payload.current_login_timestamp.replace("Z", "+00:00")
            )

        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid timestamp format",
            )

        persisted_user = await find_user(
            session,
            payload.user_id,
            payload.tenant_id,
        )

        if persisted_user is None:
            user = UserProfile(
                user_id=payload.user_id,
                tenant_id=payload.tenant_id,
                current_streak=payload.active_streak,
                last_completion_time=previous_login,
                verified_activity_time=previous_login,
            )

        else:
            user = UserProfile(
                user_id=persisted_user.user_id,
                tenant_id=persisted_user.tenant_id,
                current_streak=persisted_user.current_streak,
                last_completion_time=persisted_user.last_completion_time,
                verified_activity_time=persisted_user.verified_activity_time,
            )

        updated_user = update_streak(
            user,
            current_login,
        )

        await save_user(
            session,
            user_id=updated_user.user_id,
            tenant_id=updated_user.tenant_id,
            current_streak=updated_user.current_streak,
            last_completion_time=updated_user.last_completion_time,
            verified_activity_time=updated_user.verified_activity_time,
        )

        return {
            "status": "processed",
            "previous_active_streak": payload.active_streak,
            "verified_streak": updated_user.current_streak,
            "last_completion_time": updated_user.last_completion_time,
            "verified_activity_time": updated_user.verified_activity_time,
        }


    @app.get("/user/{user_id}/streak")
    async def get_user_streak(
        user_id: str,
        tenant_id: str = "default",
        session: AsyncSession = Depends(get_session),
    ):
        user = await find_user(
            session,
            user_id,
            tenant_id,
        )

        if user is None:
            raise HTTPException(
                status_code=404,
                detail="User not found",
            )

        return {
            "user_id": user.user_id,
            "tenant_id": user.tenant_id,
            "current_streak": user.current_streak,
            "last_completion_time": user.last_completion_time,
            "verified_activity_time": user.verified_activity_time,
        }


    @app.get("/user/{user_id}/badges")
    async def get_user_badges(
        user_id: str,
        tenant_id: str = "default",
        session: AsyncSession = Depends(get_session),
    ):
        awards = await find_awards(
            session,
            tenant_id,
        )

        return {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "badges": [
                {
                    "award_id": award.award_id,
                    "badge_id": award.badge_id,
                    "awarded_at": award.awarded_at,
                    "evidence_ref": award.evidence_ref,
                }
                for award in awards
            ],
        }

    return app


def _register_exception_handlers(app: FastAPI) -> None:
    """Map domain exceptions to structured JSON error responses."""

    def _build_response(status_code: int, exc: LeaderboardError) -> JSONResponse:
        body = ErrorResponse(error=exc.message, detail=str(exc.details) if exc.details else None)
        logger.error("Request failed | error=%s status=%s", exc.message, status_code)
        return JSONResponse(status_code=status_code, content=body.model_dump())

    @app.exception_handler(UserNotFoundError)
    async def user_not_found_handler(_request: Request, exc: UserNotFoundError) -> JSONResponse:
        return _build_response(status.HTTP_404_NOT_FOUND, exc)

    @app.exception_handler(InvalidScoreError)
    async def invalid_score_handler(_request: Request, exc: InvalidScoreError) -> JSONResponse:
        return _build_response(status.HTTP_400_BAD_REQUEST, exc)

    @app.exception_handler(NegativeScoreError)
    async def negative_score_handler(_request: Request, exc: NegativeScoreError) -> JSONResponse:
        return _build_response(status.HTTP_400_BAD_REQUEST, exc)

    @app.exception_handler(RedisTimeoutError)
    async def timeout_handler(_request: Request, exc: RedisTimeoutError) -> JSONResponse:
        return _build_response(status.HTTP_504_GATEWAY_TIMEOUT, exc)

    @app.exception_handler(RedisUnavailableError)
    async def redis_unavailable_handler(
        _request: Request,
        exc: RedisUnavailableError,
    ) -> JSONResponse:
        return _build_response(status.HTTP_503_SERVICE_UNAVAILABLE, exc)

    @app.exception_handler(LeaderboardError)
    async def generic_leaderboard_handler(
        _request: Request,
        exc: LeaderboardError,
    ) -> JSONResponse:
        return _build_response(status.HTTP_500_INTERNAL_SERVER_ERROR, exc)

    @app.exception_handler(InvalidTenantMetadataError)
    async def invalid_tenant_metadata_handler(
        _request: Request,
        exc: InvalidTenantMetadataError,
    ) -> JSONResponse:
        return _build_response(status.HTTP_422_UNPROCESSABLE_ENTITY, exc)


app = create_app()
