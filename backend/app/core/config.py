"""Application configuration — all settings from environment variables."""
from __future__ import annotations
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./finance.db",
        validation_alias="DATABASE_URL",
    )

    # AI
    gemini_api_key: str = Field(default="", validation_alias="GEMINI_API_KEY")
    gemini_model: str = Field(
        default="gemini-3.6-flash", validation_alias="GEMINI_MODEL"
    )

    # App
    app_env: str = Field(default="development", validation_alias="APP_ENV")
    secret_key: str = Field(
        default="change-me-in-production", validation_alias="SECRET_KEY"
    )

    # Market data
    market_data_source: str = Field(
        default="DEMO", validation_alias="MARKET_DATA_SOURCE"
    )

    # CSV
    csv_max_size_bytes: int = Field(
        default=5_242_880, validation_alias="CSV_MAX_SIZE_BYTES"
    )

    # Angel One SmartAPI Integration
    angel_api_key: str = Field(default="", validation_alias="ANGEL_API_KEY")
    angel_client_id: str = Field(default="", validation_alias="ANGEL_CLIENT_ID")
    angel_password: str = Field(default="", validation_alias="ANGEL_PASSWORD")
    angel_totp_secret: str = Field(default="", validation_alias="ANGEL_TOTP_SECRET")
    # Auto-sync interval in seconds (default 30 min)
    angel_sync_interval_seconds: int = Field(
        default=1800, validation_alias="ANGEL_SYNC_INTERVAL_SECONDS"
    )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
