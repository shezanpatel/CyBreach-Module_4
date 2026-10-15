"""PG-20 improvement-view engine.

Calculates:
    Delta Score = Current Score - Snapshot Score

and stores tenant improvement rankings in Redis sorted sets.
"""

from __future__ import annotations

from typing import Any

from app.db.redis_client import get_redis
from app.tenant_contract import (
    improvement_global_key,
    improvement_industry_key,
    improvement_region_key,
    improvement_size_key,
)


class ImprovementService:
    """Build and maintain tenant improvement rankings."""

    def __init__(self) -> None:
        self.redis = get_redis()

    @staticmethod
    def calculate_delta(
        current_score: float,
        snapshot_score: float,
    ) -> float:
        """Calculate improvement from the historical snapshot."""
        return float(current_score) - float(snapshot_score)

    def store_improvement(
        self,
        tenant_id: str,
        current_score: float,
        snapshot_score: float,
        industry: str,
        region: str,
        size: str,
    ) -> float:
        """Calculate and store a tenant's improvement score."""

        delta_score = self.calculate_delta(
            current_score=current_score,
            snapshot_score=snapshot_score,
        )

        # Redis ZSETs use the delta as the ranking score.
        self.redis.zadd(
            improvement_global_key(),
            {tenant_id: delta_score},
        )

        self.redis.zadd(
            improvement_industry_key(industry),
            {tenant_id: delta_score},
        )

        self.redis.zadd(
            improvement_region_key(region),
            {tenant_id: delta_score},
        )

        self.redis.zadd(
            improvement_size_key(size),
            {tenant_id: delta_score},
        )

        return delta_score

    def get_improvement(
        self,
        dimension: str = "global",
        value: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Return tenants ranked by improvement.

        Higher delta scores rank first because improvement represents
        positive progress.
        """

        if dimension == "global":
            key = improvement_global_key()
        elif dimension == "industry":
            if value is None:
                raise ValueError("industry value is required")
            key = improvement_industry_key(value)
        elif dimension == "region":
            if value is None:
                raise ValueError("region value is required")
            key = improvement_region_key(value)
        elif dimension == "size":
            if value is None:
                raise ValueError("size value is required")
            key = improvement_size_key(value)
        else:
            raise ValueError(
                "dimension must be one of: global, industry, region, size"
            )

        entries = self.redis.zrevrange(
            key,
            0,
            max(limit - 1, 0),
            withscores=True,
        )

        return [
            {
                "rank": index + 1,
                "tenant_id": tenant_id,
                "delta_score": float(delta_score),
            }
            for index, (tenant_id, delta_score) in enumerate(entries)
        ]