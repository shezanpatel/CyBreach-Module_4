"""Comprehensive tests for the Redis Leaderboard Engine."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from app.exceptions import InvalidTenantMetadataError, NegativeScoreError, UserNotFoundError
from app.services.leaderboard_service import LeaderboardService
from app.exceptions import InvalidScoreError, NegativeScoreError, UserNotFoundError
from app.tenant_contract import (
    industry_key,
    region_key,
    size_key,
    improvement_global_key,
    improvement_industry_key,
    improvement_region_key,
    improvement_size_key,
    tenant_members_key,
    tenant_metadata_key,
)

class TestSetScore:
    """Tests for POST /score."""

    def test_add_score(self, client: TestClient) -> None:
        response = client.post("/score", json={"username": "alice", "score": 1000})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["username"] == "alice"
        assert data["score"] == 1000

    def test_update_score(self, client: TestClient) -> None:
        client.post("/score", json={"username": "bob", "score": 500})
        response = client.post("/score", json={"username": "bob", "score": 1500})
        assert response.status_code == 200
        assert response.json()["score"] == 1500

    def test_duplicate_user_overwrites(self, client: TestClient, service: LeaderboardService) -> None:
        client.post("/score", json={"username": "dup_user", "score": 100})
        client.post("/score", json={"username": "dup_user", "score": 200})
        score, _ = service.get_rank("dup_user")
        assert score == 200

    def test_negative_score_rejected(self, client: TestClient) -> None:
        response = client.post("/score", json={"username": "bad", "score": -10})
        assert response.status_code == 422

    def test_empty_username_rejected(self, client: TestClient) -> None:
        response = client.post("/score", json={"username": "   ", "score": 100})
        assert response.status_code == 422

    def test_zero_score_allowed(self, client: TestClient) -> None:
        response = client.post("/score", json={"username": "zero", "score": 0})
        assert response.status_code == 200
        assert response.json()["score"] == 0

    def test_invalid_tenant_metadata_returns_422(
        self,
        client: TestClient,
    ) -> None:
        response = client.post(
            "/score",
            json={
                "username": "invalid_tenant_user",
                "score": 100,
                "tenant_id": "INVALID",
                "industry": "technology",
                "region": "europe",
                "size": "1-50",
            },
        )
        assert response.status_code == 422


class TestIncrementScore:
    """Tests for POST /increment."""

    def test_increment_existing_user(self, client: TestClient) -> None:
        client.post("/score", json={"username": "inc_user", "score": 100})
        response = client.post("/increment", json={"username": "inc_user", "increment": 50})
        assert response.status_code == 200
        data = response.json()
        assert data["score"] == 150
        assert data["increment"] == 50

    def test_increment_new_user(self, client: TestClient) -> None:
        response = client.post("/increment", json={"username": "new_inc", "increment": 75})
        assert response.status_code == 200
        assert response.json()["score"] == 75

    def test_zero_increment_rejected(self, client: TestClient) -> None:
        response = client.post("/increment", json={"username": "user", "increment": 0})
        assert response.status_code == 422

    def test_negative_increment_rejected(self, client: TestClient) -> None:
        response = client.post("/increment", json={"username": "user", "increment": -5})
        assert response.status_code == 422

    def test_negative_score_rejected_at_service(
        self,
        service: LeaderboardService,
    ) -> None:
        with pytest.raises(NegativeScoreError):
            service.set_score("bad_score", -100)


class TestLeaderboard:
    """Tests for GET /leaderboard."""

    def test_top_leaderboard(self, client: TestClient) -> None:
        client.post("/score", json={"username": "first", "score": 3000})
        client.post("/score", json={"username": "second", "score": 2000})
        client.post("/score", json={"username": "third", "score": 1000})

        response = client.get("/leaderboard?limit=2")
        assert response.status_code == 200
        data = response.json()
        assert data["total_players"] == 3
        assert data["limit"] == 2
        assert len(data["entries"]) == 2
        assert data["entries"][0]["username"] == "first"
        assert data["entries"][0]["rank"] == 1
        assert data["entries"][1]["username"] == "second"

    def test_empty_leaderboard(self, client: TestClient) -> None:
        response = client.get("/leaderboard")
        assert response.status_code == 200
        data = response.json()
        assert data["total_players"] == 0
        assert data["entries"] == []

    def test_limit_validation(self, client: TestClient) -> None:
        response = client.get("/leaderboard?limit=0")
        assert response.status_code == 422

        response = client.get("/leaderboard?limit=1001")
        assert response.status_code == 422


class TestRankLookup:
    """Tests for GET /rank/{username}."""

    def test_rank_lookup(self, client: TestClient) -> None:
        client.post("/score", json={"username": "rank_a", "score": 5000})
        client.post("/score", json={"username": "rank_b", "score": 3000})
        client.post("/score", json={"username": "rank_c", "score": 1000})

        response = client.get("/rank/rank_b")
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "rank_b"
        assert data["score"] == 3000
        assert data["rank"] == 2

    def test_missing_user(self, client: TestClient) -> None:
        response = client.get("/rank/nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False


class TestDeleteUser:
    """Tests for DELETE /user/{username}."""

    def test_delete_user(self, client: TestClient) -> None:
        client.post("/score", json={"username": "to_delete", "score": 100})
        response = client.delete("/user/to_delete")
        assert response.status_code == 200
        assert response.json()["success"] is True

        response = client.get("/rank/to_delete")
        assert response.status_code == 404

    def test_delete_nonexistent_user(self, client: TestClient) -> None:
        response = client.delete("/user/ghost")
        assert response.status_code == 404


class TestResetLeaderboard:
    """Tests for DELETE /leaderboard."""

    def test_reset_leaderboard(
        self,
        client: TestClient,
        service: LeaderboardService,
    ) -> None:
        client.post("/score", json={"username": "p1", "score": 100})
        client.post("/score", json={"username": "p2", "score": 200})
        client.post(
            "/opt-in",
            json={
                "tenant_id": "CORP-001",
                "industry": "technology",
                "region": "europe",
                "size": "1-50",
            },
        )
        client.post(
            "/score",
            json={
                "username": "tenant_reset",
                "score": 300,
                "tenant_id": "CORP-001",
                "industry": "technology",
                "region": "europe",
                "size": "1-50",
            },
        )
        service.redis.zadd(improvement_global_key(), {"CORP-001": 25})
        service.redis.zadd(
            improvement_industry_key("technology"),
            {"CORP-001": 25},
        )

        response = client.delete("/leaderboard")
        assert response.status_code == 200

        leaderboard = client.get("/leaderboard").json()
        assert leaderboard["total_players"] == 0
        assert client.get("/leaderboard/industry?industry=technology").json()[
            "total_players"
        ] == 0
        assert client.get("/leaderboard/region?region=europe").json()[
            "total_players"
        ] == 0
        assert client.get("/leaderboard/size?size_band=1-50").json()[
            "total_players"
        ] == 0
        assert service.redis.zscore(improvement_global_key(), "CORP-001") is None
        assert service.redis.zscore(
            improvement_industry_key("technology"), "CORP-001"
        ) is None


class TestHealthAndMetrics:
    """Tests for GET /health and GET /metrics."""

    def test_health_check(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["app"] == "running"
        assert data["redis"] == "connected"
        assert data["status"] == "healthy"

    def test_metrics(self, client: TestClient) -> None:
        response = client.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "metrics" in data


class TestConcurrentUpdates:
    """Tests for concurrent score updates."""

    def test_concurrent_increments(self, service: LeaderboardService) -> None:
        service.set_score("concurrent_user", 0)
        increments = 100
        per_thread = 10

        def _increment_batch() -> None:
            for _ in range(per_thread):
                service.increment_score("concurrent_user", 1)

        with ThreadPoolExecutor(max_workers=increments // per_thread) as executor:
            futures = [executor.submit(_increment_batch) for _ in range(increments // per_thread)]
            for future in futures:
                future.result()

        score, _ = service.get_rank("concurrent_user")
        assert score == increments

    def test_concurrent_set_scores(self, service: LeaderboardService) -> None:
        def _set_score(index: int) -> None:
            service.set_score(f"player_{index}", float(index))

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(_set_score, i) for i in range(100)]
            for future in futures:
                future.result()

        entries, total = service.get_top_players(100)
        assert total == 100
        assert entries[0].username == "player_99"
        assert entries[0].score == 99.0


class TestServiceEdgeCases:
    """Direct service-layer edge case tests."""

    def test_get_rank_not_found(self, service: LeaderboardService) -> None:
        with pytest.raises(UserNotFoundError):
            service.get_rank("nobody")

    def test_delete_user_not_found(self, service: LeaderboardService) -> None:
        with pytest.raises(UserNotFoundError):
            service.delete_user("nobody")

    def test_tie_scores_ranking(self, service: LeaderboardService) -> None:
        service.set_score("tie_a", 1000)
        service.set_score("tie_b", 1000)
        service.set_score("tie_c", 2000)

        _, rank_a = service.get_rank("tie_a")
        _, rank_b = service.get_rank("tie_b")
        _, rank_c = service.get_rank("tie_c")

        assert rank_c == 1
        assert rank_a in (2, 3)
        assert rank_b in (2, 3)

    def test_username_stripping(self, client: TestClient) -> None:
        client.post("/score", json={"username": "  spaced  ", "score": 500})
        response = client.get("/rank/spaced")
        assert response.status_code == 200
class TestTenantScore:
    """Tests for tenant-aware leaderboard updates."""

    @staticmethod
    def _opt_in(service: LeaderboardService) -> None:
        service.opt_in_tenant(
            tenant_id="CORP-001",
            industry="technology",
            region="europe",
            size="1-50",
        )

    def test_updates_all_absolute_leaderboards(
        self,
        service: LeaderboardService,
    ) -> None:
        self._opt_in(service)
        service.set_tenant_score(
            username="tenant_user",
            score=1500,
            tenant_id="CORP-001",
            industry="technology",
            region="europe",
            size="1-50",
        )

        assert service.redis.zscore(service.key, "tenant_user") == 1500
        assert service.redis.zscore(
            industry_key("technology"), "tenant_user"
        ) == 1500
        assert service.redis.zscore(
            region_key("europe"), "tenant_user"
        ) == 1500
        assert service.redis.zscore(
            size_key("1-50"), "tenant_user"
        ) == 1500

    def test_records_tenant_membership(
        self,
        service: LeaderboardService,
    ) -> None:
        self._opt_in(service)
        service.set_tenant_score(
            username="tenant_user",
            score=1500,
            tenant_id="CORP-001",
            industry="technology",
            region="europe",
            size="1-50",
        )

        assert service.redis.sismember(
            tenant_members_key("CORP-001"), "tenant_user"
        )

    def test_opt_in_records_validated_tenant_metadata(
        self,
        client: TestClient,
        service: LeaderboardService,
    ) -> None:
        response = client.post(
            "/opt-in",
            json={
                "tenant_id": "CORP-001",
                "industry": "Technology",
                "region": "Europe",
                "size": "1-50",
            },
        )

        assert response.status_code == 200
        assert service.redis.hgetall(tenant_metadata_key("CORP-001")) == {
            "industry": "technology",
            "region": "europe",
            "size": "1-50",
        }

    def test_opt_out_purges_tenant_from_all_rankings(
        self,
        client: TestClient,
        service: LeaderboardService,
    ) -> None:
        self._opt_in(service)
        service.set_tenant_score(
            username="opt_out_user",
            score=1500,
            tenant_id="CORP-001",
            industry="technology",
            region="europe",
            size="1-50",
        )
        service.redis.zadd(improvement_global_key(), {"CORP-001": 25})
        service.redis.zadd(
            improvement_industry_key("technology"),
            {"CORP-001": 25},
        )
        service.redis.zadd(
            improvement_region_key("europe"),
            {"CORP-001": 25},
        )
        service.redis.zadd(
            improvement_size_key("1-50"),
            {"CORP-001": 25},
        )

        response = client.post("/opt-out", json={"tenant_id": "CORP-001"})

        assert response.status_code == 200
        assert service.redis.zscore(service.key, "opt_out_user") is None
        assert service.redis.zscore(
            industry_key("technology"), "opt_out_user"
        ) is None
        assert service.redis.zscore(region_key("europe"), "opt_out_user") is None
        assert service.redis.zscore(size_key("1-50"), "opt_out_user") is None
        assert not service.redis.exists(tenant_members_key("CORP-001"))
        assert not service.redis.exists(tenant_metadata_key("CORP-001"))
        assert service.redis.zscore(improvement_global_key(), "CORP-001") is None
        assert service.redis.zscore(
            improvement_industry_key("technology"), "CORP-001"
        ) is None
        assert service.redis.zscore(
            improvement_region_key("europe"), "CORP-001"
        ) is None
        assert service.redis.zscore(
            improvement_size_key("1-50"), "CORP-001"
        ) is None
        with pytest.raises(InvalidTenantMetadataError, match="must opt in"):
            service.set_tenant_score(
                username="opt_out_user",
                score=1700,
                tenant_id="CORP-001",
                industry="technology",
                region="europe",
                size="1-50",
            )

    def test_delete_user_cleans_tenant_dimension_indexes(
        self,
        service: LeaderboardService,
    ) -> None:
        self._opt_in(service)
        service.set_tenant_score(
            username="tenant_delete",
            score=1500,
            tenant_id="CORP-001",
            industry="technology",
            region="europe",
            size="1-50",
        )

        assert service.delete_user("tenant_delete")
        assert service.redis.zscore(
            industry_key("technology"), "tenant_delete"
        ) is None
        assert service.redis.zscore(region_key("europe"), "tenant_delete") is None
        assert service.redis.zscore(size_key("1-50"), "tenant_delete") is None
        assert not service.redis.sismember(
            tenant_members_key("CORP-001"), "tenant_delete"
        )

    def test_updates_existing_tenant_score(
        self,
        service: LeaderboardService,
    ) -> None:
        self._opt_in(service)
        service.set_tenant_score(
            username="tenant_user",
            score=1000,
            tenant_id="CORP-001",
            industry="technology",
            region="europe",
            size="1-50",
        )

        service.set_tenant_score(
            username="tenant_user",
            score=2000,
            tenant_id="CORP-001",
            industry="technology",
            region="europe",
            size="1-50",
        )

        assert service.redis.zscore(service.key, "tenant_user") == 2000
        assert service.redis.zscore(
            industry_key("technology"), "tenant_user"
        ) == 2000

    def test_global_mutations_cannot_desynchronize_tenant_rankings(
        self,
        service: LeaderboardService,
    ) -> None:
        self._opt_in(service)
        service.set_tenant_score(
            username="protected_user",
            score=1500,
            tenant_id="CORP-001",
            industry="technology",
            region="europe",
            size="1-50",
        )

        with pytest.raises(InvalidTenantMetadataError, match="must be updated"):
            service.set_score("protected_user", 1800)
        with pytest.raises(InvalidTenantMetadataError, match="must be updated"):
            service.increment_score("protected_user", 100)
        with pytest.raises(InvalidTenantMetadataError, match="must be updated"):
            service.set_scores_bulk({"protected_user": 2000})

        assert service.redis.zscore(service.key, "protected_user") == 1500
        assert service.redis.zscore(
            industry_key("technology"), "protected_user"
        ) == 1500
        assert service.redis.zscore(
            region_key("europe"), "protected_user"
        ) == 1500
        assert service.redis.zscore(
            size_key("1-50"), "protected_user"
        ) == 1500

    def test_username_cannot_be_associated_with_multiple_tenants(
        self,
        service: LeaderboardService,
    ) -> None:
        self._opt_in(service)
        service.opt_in_tenant(
            tenant_id="CORP-002",
            industry="finance",
            region="europe",
            size="1-50",
        )
        service.set_tenant_score(
            username="single_tenant_user",
            score=1500,
            tenant_id="CORP-001",
            industry="technology",
            region="europe",
            size="1-50",
        )

        with pytest.raises(InvalidTenantMetadataError, match="another tenant"):
            service.set_tenant_score(
                username="single_tenant_user",
                score=1600,
                tenant_id="CORP-002",
                industry="finance",
                region="europe",
                size="1-50",
            )

    def test_opt_in_rejects_metadata_change_with_active_members(
        self,
        service: LeaderboardService,
    ) -> None:
        self._opt_in(service)
        service.set_tenant_score(
            username="metadata_user",
            score=1500,
            tenant_id="CORP-001",
            industry="technology",
            region="europe",
            size="1-50",
        )

        with pytest.raises(InvalidTenantMetadataError, match="cannot change"):
            service.opt_in_tenant(
                tenant_id="CORP-001",
                industry="finance",
                region="europe",
                size="1-50",
            )

    def test_opt_in_rejects_metadata_change_with_improvement_scores(
        self,
        service: LeaderboardService,
    ) -> None:
        self._opt_in(service)
        service.redis.zadd(improvement_global_key(), {"CORP-001": 25})

        with pytest.raises(InvalidTenantMetadataError, match="cannot change"):
            service.opt_in_tenant(
                tenant_id="CORP-001",
                industry="finance",
                region="europe",
                size="1-50",
            )

    def test_tenant_score_requires_opt_in_and_matching_metadata(
        self,
        client: TestClient,
    ) -> None:
        payload = {
            "username": "consent_user",
            "score": 100,
            "tenant_id": "CORP-001",
            "industry": "technology",
            "region": "europe",
            "size": "1-50",
        }
        response = client.post("/score", json=payload)
        assert response.status_code == 422
        assert response.json()["error"] == "Tenant must opt in before submitting scores"

        client.post(
            "/opt-in",
            json={
                "tenant_id": "CORP-001",
                "industry": "technology",
                "region": "europe",
                "size": "1-50",
            },
        )
        payload["industry"] = "finance"
        response = client.post("/score", json=payload)
        assert response.status_code == 422
        assert response.json()["error"] == (
            "Score metadata must match the tenant's opted-in metadata"
        )

    def test_rejects_invalid_tenant_id(
        self,
        service: LeaderboardService,
    ) -> None:
        with pytest.raises(InvalidTenantMetadataError):
            service.set_tenant_score(
                username="tenant_user",
                score=1500,
                tenant_id="INVALID",
                industry="technology",
                region="europe",
                size="1-50",
            )

    def test_dimension_routes_read_the_requested_metadata_index(
        self,
        client: TestClient,
    ) -> None:
        client.post(
            "/opt-in",
            json={
                "tenant_id": "CORP-001",
                "industry": "technology",
                "region": "europe",
                "size": "1-50",
            },
        )
        client.post(
            "/score",
            json={
                "username": "tenant_user",
                "score": 1500,
                "tenant_id": "CORP-001",
                "industry": "technology",
                "region": "europe",
                "size": "1-50",
            },
        )
        client.post("/score", json={"username": "global_only", "score": 2000})

        cases = (
            ("/leaderboard/industry?industry=technology", "industry"),
            ("/leaderboard/region?region=europe", "region"),
            ("/leaderboard/size?size_band=1-50", "size"),
        )
        for path, dimension in cases:
            response = client.get(path)
            assert response.status_code == 200
            result = response.json()
            assert result["dimension"] == dimension
            assert result["total_players"] == 1
            assert [entry["username"] for entry in result["entries"]] == ["tenant_user"]

    def test_dimension_route_requires_its_filter_value(
        self,
        client: TestClient,
    ) -> None:
        response = client.get("/leaderboard/industry")

        assert response.status_code == 400
        assert response.json()["detail"] == "industry value is required"

    def test_dimension_route_rejects_invalid_metadata_filter(
        self,
        client: TestClient,
    ) -> None:
        response = client.get("/leaderboard/industry?industry=unknown")

        assert response.status_code == 400
        assert "industry must be one of" in response.json()["detail"]

    def test_dimension_route_directs_improvement_view_to_its_endpoint(
        self,
        client: TestClient,
    ) -> None:
        response = client.get("/leaderboard/global?view=improvement")

        assert response.status_code == 400
        assert response.json()["detail"] == (
            "Use /improvement?dimension=... for improvement rankings"
        )
