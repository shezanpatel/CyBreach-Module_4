from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str
    APP_VERSION: str

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int

    DATABASE_URL: str
    KAFKA_BOOTSTRAP_SERVERS: str

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    SERVICE_API_KEY: str

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
