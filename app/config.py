"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---------------------------------------------------------------------
    # Application
    # ---------------------------------------------------------------------

    app_name: str = Field(default="Redis Leaderboard Engine", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # ---------------------------------------------------------------------
    # Redis
    # ---------------------------------------------------------------------

    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_db: int = Field(default=0, alias="REDIS_DB")

    redis_password: str | None = Field(
        default=None,
        alias="REDIS_PASSWORD",
    )

    redis_socket_timeout: float = Field(
        default=5.0,
        alias="REDIS_SOCKET_TIMEOUT",
    )

    redis_socket_connect_timeout: float = Field(
        default=5.0,
        alias="REDIS_SOCKET_CONNECT_TIMEOUT",
    )

    redis_max_connections: int = Field(
        default=50,
        alias="REDIS_MAX_CONNECTIONS",
    )

    redis_leaderboard_key: str = Field(
        default="leaderboard:global",
        alias="REDIS_LEADERBOARD_KEY",
    )

    # ---------------------------------------------------------------------
    # Security
    # ---------------------------------------------------------------------

    api_key: str = Field(default="test-api-key", alias="API_KEY")

    cors_origins: str = Field(
        default="http://localhost:3000",
        alias="CORS_ORIGINS",
    )

    rate_limit_per_minute: int = Field(
        default=20,
        alias="RATE_LIMIT_PER_MINUTE",
    )

    # ---------------------------------------------------------------------
    # Validators
    # ---------------------------------------------------------------------

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("API_KEY cannot be empty")
        return value

    # ---------------------------------------------------------------------
    # Helper Properties
    # ---------------------------------------------------------------------

    @property
    def allowed_origins(self) -> list[str]:
        """Return CORS origins as a list."""

        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

    @property
    def is_production(self) -> bool:
        """True if running in production."""

        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance."""

    return Settings()