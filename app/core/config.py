"""
Application configuration.

All settings are loaded from environment variables (with .env fallback).
Settings are validated by pydantic — the app will refuse to start if a
required variable is missing or malformed.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly typed application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App ---
    APP_NAME: str = "Mallah API"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    APP_DEBUG: bool = False
    APP_VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"

    # --- Server ---
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4

    # --- Security ---
    JWT_SECRET_KEY: str = Field(..., min_length=32)
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30

    # --- Database ---
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL_SECONDS: int = 300

    # --- Firebase ---
    FIREBASE_CREDENTIALS_PATH: str = ""
    FIREBASE_CREDENTIALS_JSON: str = ""
    FIREBASE_PROJECT_ID: str = ""

    # --- Email ---
    SENDGRID_API_KEY: str = ""
    EMAIL_FROM_ADDRESS: str = "noreply@mallah.app"
    EMAIL_FROM_NAME: str = "Mallah"

    # --- CORS ---
    CORS_ALLOW_ORIGINS: str = "http://localhost:3000"

    # --- Rate Limit ---
    RATE_LIMIT_PER_IP_PER_MINUTE: int = 60
    RATE_LIMIT_PER_USER_PER_MINUTE: int = 300

    # --- Sentry ---
    SENTRY_DSN: str = ""
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1

    # --- Ingest ---
    INGEST_API_KEY: str = Field(..., min_length=16)

    # --- Bootstrap ---
    BOOTSTRAP_ADMIN_EMAIL: str = ""
    BOOTSTRAP_ADMIN_PASSWORD: str = ""

    @field_validator("CORS_ALLOW_ORIGINS")
    @classmethod
    def split_cors(cls, v: str) -> str:
        # Stored as comma-separated; consumers split on read
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ALLOW_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def firebase_enabled(self) -> bool:
        return bool(
            self.FIREBASE_PROJECT_ID
            and (self.FIREBASE_CREDENTIALS_PATH or self.FIREBASE_CREDENTIALS_JSON)
        )

    @property
    def email_enabled(self) -> bool:
        return bool(self.SENDGRID_API_KEY)


@lru_cache
def get_settings() -> Settings:
    """Singleton accessor — settings are loaded once per process."""
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
