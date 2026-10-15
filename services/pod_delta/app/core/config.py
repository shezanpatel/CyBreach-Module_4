"""Re-exports application settings for existing modules."""

from app.core.settings import settings

PROJECT_NAME = settings.PROJECT_NAME
VERSION = settings.VERSION
ENVIRONMENT = settings.ENVIRONMENT
DATABASE_URL = settings.DATABASE_URL
CORS_ORIGINS = settings.CORS_ORIGINS
SECRET_KEY = settings.SECRET_KEY
ANALYTICS_RETENTION_DAYS = settings.ANALYTICS_RETENTION_DAYS
CACHE_TTL_SECONDS = settings.CACHE_TTL_SECONDS
ALLOWED_HOSTS = settings.ALLOWED_HOSTS
LOG_LEVEL = settings.LOG_LEVEL
