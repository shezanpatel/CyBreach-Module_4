from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_benchmark_cohorts_only_lists_groups_meeting_minimum():
    response = client.get("/benchmark/cohorts")

    assert response.status_code == 200
    body = response.json()
    assert body["minimum_peer_count"] == 10
    assert len(body["cohorts"]) == 7
    assert all(
        cohort["peer_count"] >= body["minimum_peer_count"]
        for cohort in body["cohorts"]
    )
    assert not any(cohort["size_band"] == "Small" for cohort in body["cohorts"])


def test_benchmark_returns_exact_seeded_values_with_demo_notice():
    response = client.post(
        "/benchmark",
        json={
            "industry": "Technology",
            "region": "West",
            "size_band": "Large",
        },
    )

    assert response.status_code == 200
    assert response.json()["peer_count"] == 20
    assert response.json()["percentile"] == 50.0
    assert response.json()["peer_25th"] == 65.2
    assert response.json()["peer_median"] == 76.4
    assert response.json()["peer_75th"] == 88.1
    assert "synthetic demo" in response.json()["label"]
    assert "no real/private peer data" in response.json()["label"]


def test_benchmark_quantiles_are_ordered_for_all_supported_cohorts():
    cohorts = client.get("/benchmark/cohorts").json()["cohorts"]

    for cohort in cohorts:
        response = client.post(
            "/benchmark",
            json={
                "industry": cohort["industry"],
                "region": cohort["region"],
                "size_band": cohort["size_band"],
            },
        )

        assert response.status_code == 200
        result = response.json()
        assert 0 <= result["peer_25th"] <= result["peer_median"] <= result["peer_75th"] <= 100
        assert result["percentile"] == 50.0


def test_benchmark_compare_insufficient_peers():
    response = client.post(
        "/benchmark/compare",
        json={
            "industry": "Finance",
            "region": "West",
            "size_band": "Small",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "insufficient peers"


def test_benchmark_compare_valid_cohort():
    response = client.post(
        "/benchmark/compare",
        json={
            "industry": "Technology",
            "region": "West",
            "size_band": "Large",
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["regional_peer_count"] == 20
    assert result["regional_median"] == 76.4
    assert result["global_peer_count"] == 100
    assert result["global_median"] == 72.0
    assert result["median_difference"] == 4.4
    assert "synthetic demo" in result["label"]


def test_benchmark_trend_is_labeled_as_seeded_demo_data():
    response = client.get("/benchmark/trend/TENANT-001")

    assert response.status_code == 200
    result = response.json()
    assert [item["days_ago"] for item in result["trend"]] == [30, 60, 90]
    assert "synthetic demo" in result["label"]


def test_benchmark_compare_unknown_cohort_returns_not_found():
    response = client.post(
        "/benchmark/compare",
        json={
            "industry": "Unknown",
            "region": "Unknown",
            "size_band": "Unknown",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "regional benchmark cohort not found"
