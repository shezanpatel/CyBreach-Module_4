import pytest

from app.core.settings import settings


@pytest.fixture(autouse=True)
def disable_kafka(monkeypatch):
    monkeypatch.setattr(settings, "KAFKA_ENABLE", False)
    monkeypatch.setattr(settings, "ANALYTICS_FLUSH_INTERVAL_SECONDS", 86_400)
