from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


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