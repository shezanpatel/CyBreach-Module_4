"""Tests for PG-20 improvement-view engine."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db.redis_client import get_redis
from app.services.improvement_service import ImprovementService


@pytest.fixture(autouse=True)
def clear_improvement_rankings() -> None:
    """Keep PG-20 tests isolated from previous Redis state."""

    redis = get_redis()

    for key in redis.scan_iter(match="lb:*:improvement"):
        redis.delete(key)


class TestImprovementCalculation:
    """Tests for delta score calculation."""

    def test_delta_score_calculation(self) -> None:
        service = ImprovementService()

        delta = service.calculate_delta(
            current_score=1700,
            snapshot_score=1500,
        )

        assert delta == 200

    def test_zero_improvement(self) -> None:
        service = ImprovementService()

        delta = service.calculate_delta(
            current_score=1500,
            snapshot_score=1500,
        )

        assert delta == 0

    def test_negative_improvement(self) -> None:
        service = ImprovementService()

        delta = service.calculate_delta(
            current_score=1400,
            snapshot_score=1500,
        )

        assert delta == -100


class TestImprovementRedis:
    """Tests for Redis improvement rankings."""

    def test_store_improvement(self,) -> None:
        service = ImprovementService()
        delta = service.store_improvement(
            tenant_id="CORP-001",
            current_score=1700,
            snapshot_score=1500,
            industry="technology",
            region="apac",
            size="51-500",
        )

        assert delta == 200

        assert service.redis.zscore(
            "lb:global:improvement",
            "CORP-001",
        ) == 200

        assert service.redis.zscore(
            "lb:industry:technology:improvement",
            "CORP-001",
        ) == 200

        assert service.redis.zscore(
            "lb:region:apac:improvement",
            "CORP-001",
        ) == 200

        assert service.redis.zscore(
            "lb:size:51-500:improvement",
            "CORP-001",
        ) == 200

    def test_improvement_ranking(self) -> None:
        service = ImprovementService()

        service.store_improvement(
            tenant_id="CORP-001",
            current_score=1700,
            snapshot_score=1500,
            industry="technology",
            region="apac",
            size="51-500",
        )

        service.store_improvement(
            tenant_id="CORP-002",
            current_score=1900,
            snapshot_score=1500,
            industry="technology",
            region="apac",
            size="501-5000",
        )

        service.store_improvement(
            tenant_id="CORP-003",
            current_score=1550,
            snapshot_score=1500,
            industry="technology",
            region="europe",
            size="1-50",
        )

        entries = service.get_improvement(
            dimension="global",
            limit=10,
        )

        assert len(entries) == 3

        assert entries[0]["tenant_id"] == "CORP-002"
        assert entries[0]["delta_score"] == 400
        assert entries[0]["rank"] == 1

        assert entries[1]["tenant_id"] == "CORP-001"
        assert entries[1]["delta_score"] == 200
        assert entries[1]["rank"] == 2

        assert entries[2]["tenant_id"] == "CORP-003"
        assert entries[2]["delta_score"] == 50
        assert entries[2]["rank"] == 3

    def test_industry_filter(self) -> None:
        service = ImprovementService()

        service.store_improvement(
            tenant_id="CORP-001",
            current_score=1700,
            snapshot_score=1500,
            industry="technology",
            region="apac",
            size="51-500",
        )

        service.store_improvement(
            tenant_id="CORP-002",
            current_score=1900,
            snapshot_score=1500,
            industry="finance",
            region="europe",
            size="501-5000",
        )

        entries = service.get_improvement(
            dimension="industry",
            value="technology",
            limit=10,
        )

        assert len(entries) == 1
        assert entries[0]["tenant_id"] == "CORP-001"
        assert entries[0]["delta_score"] == 200


class TestImprovementAPI:
    """Tests for GET /improvement."""

    def test_global_improvement_endpoint(
        self,
        client: TestClient,
    ) -> None:
        service = ImprovementService()

        service.store_improvement(
            tenant_id="CORP-001",
            current_score=1700,
            snapshot_score=1500,
            industry="technology",
            region="apac",
            size="51-500",
        )

        response = client.get(
            "/improvement",
            params={
                "dimension": "global",
                "limit": 10,
            },
        )

        assert response.status_code == 200

        data = response.json()

        assert data["success"] is True
        assert data["total_tenants"] == 1
        assert data["entries"][0]["tenant_id"] == "CORP-001"
        assert data["entries"][0]["delta_score"] == 200
        assert data["entries"][0]["rank"] == 1

    def test_dimension_improvement_endpoint(
        self,
        client: TestClient,
    ) -> None:
        service = ImprovementService()

        service.store_improvement(
            tenant_id="CORP-001",
            current_score=1700,
            snapshot_score=1500,
            industry="technology",
            region="apac",
            size="51-500",
        )

        response = client.get(
            "/improvement",
            params={
                "dimension": "industry",
                "value": "technology",
                "limit": 10,
            },
        )

        assert response.status_code == 200

        data = response.json()

        assert data["success"] is True
        assert data["total_tenants"] == 1
        assert data["entries"][0]["tenant_id"] == "CORP-001"
        assert data["entries"][0]["delta_score"] == 200

    def test_invalid_dimension(
        self,
        client: TestClient,
    ) -> None:
        response = client.get(
            "/improvement",
            params={
                "dimension": "invalid",
                "limit": 10,
            },
        )

        assert response.status_code == 400

    def test_limit_validation(
        self,
        client: TestClient,
    ) -> None:
        response = client.get(
            "/improvement",
            params={
                "dimension": "global",
                "limit": 0,
            },
        )

        assert response.status_code == 422

        response = client.get(
            "/improvement",
            params={
                "dimension": "global",
                "limit": 1001,
            },
        )

        assert response.status_code == 422