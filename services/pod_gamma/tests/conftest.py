"""Pytest fixtures for leaderboard integration tests."""

from __future__ import annotations

from collections.abc import Generator

import fakeredis
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.db.redis_client import reset_redis_client
from app.main import create_app
from app.services.leaderboard_service import LeaderboardService, get_leaderboard_service


@pytest.fixture()
def fake_redis() -> fakeredis.FakeStrictRedis:
    """Provide an isolated in-memory Redis instance."""
    return fakeredis.FakeStrictRedis(decode_responses=True)


@pytest.fixture()
def test_settings() -> Settings:
    """Test-specific settings with a dedicated leaderboard key."""
    return Settings(
        redis_leaderboard_key="leaderboard:test",
        app_env="test",
        log_level="WARNING",
    )


@pytest.fixture()
def service(fake_redis: fakeredis.FakeStrictRedis, test_settings: Settings) -> LeaderboardService:
    """Leaderboard service wired to fakeredis."""
    reset_redis_client(client=fake_redis)
    return LeaderboardService(redis_client=fake_redis, settings=test_settings)


@pytest.fixture()
def client(
    fake_redis: fakeredis.FakeStrictRedis,
    test_settings: Settings,
    service: LeaderboardService,
) -> Generator[TestClient, None, None]:
    """FastAPI test client with dependency overrides."""
    app = create_app()

    def _override_service() -> LeaderboardService:
        return service

    app.dependency_overrides[get_leaderboard_service] = _override_service
    reset_redis_client(client=fake_redis)

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    reset_redis_client(client=None, pool=None)
