from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "CyBreach Arena"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"

    DATABASE_URL: str = "sqlite:///./cybreach.db"
    POSTGRES_DSN: Optional[str] = None

    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
    ]

    ALLOWED_HOSTS: List[str] = ["*"]
    SECRET_KEY: str = "your-secret-key-here"
    JWT_ALGORITHM: str = "HS256"
    JWT_AUDIENCE: Optional[str] = None
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    LOG_LEVEL: str = "INFO"

    ANALYTICS_RETENTION_DAYS: int = 365
    CACHE_TTL_SECONDS: int = 300

    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_WS_CHANNEL_PREFIX: str = "ws:tenant"

    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:19092"
    KAFKA_CLIENT_ID: str = "pod-delta-integration"
    KAFKA_CONSUMER_GROUP: str = "pod-delta-integration"
    KAFKA_ENABLE: bool = True
    KAFKA_AUTO_OFFSET_RESET: str = "earliest"
    KAFKA_DLT_SUFFIX: str = ".dlt"

    CLICKHOUSE_URL: str = "http://localhost:8123"
    CLICKHOUSE_DATABASE: str = "cybreach"
    CLICKHOUSE_USER: str = "default"
    CLICKHOUSE_PASSWORD: str = ""

    RATE_LIMIT_WINDOW_SECONDS: int = 60
    RATE_LIMIT_MAX_EVENTS: int = 20
    SCORE_CACHE_TTL_SECONDS: int = 3600
    IDEMPOTENCY_TTL_SECONDS: int = 86400

    WS_HEARTBEAT_SECONDS: int = 30
    WS_SESSION_TTL_SECONDS: int = 90

    ANALYTICS_FLUSH_INTERVAL_SECONDS: int = 86400

    PROMETHEUS_ENABLED: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
