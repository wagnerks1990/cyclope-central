from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized configuration loaded from environment variables and optional .env files."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="CYCLOPE_", extra="ignore")

    project_name: str = "Cyclope Central"
    app_version: str = "0.2.0"
    api_prefix: str = "/api"
    environment: str = "development"
    enable_openapi: bool = True
    log_level: str = "INFO"
    database_url: str = Field(default="postgresql+psycopg://cyclope:cyclope@postgres:5432/cyclope")
    jwt_issuer: str = "cyclope-central"
    jwt_audience: str = "cyclope-central-dashboard"
    jwt_secret_key: str = "change-me-in-production"
    token_hash_pepper: str = "change-me-token-pepper"
    device_offline_after_seconds: int = 300

    alert_device_offline_minutes: int = 15
    alert_low_disk_free_percent: float = 10.0
    alert_high_memory_percent: float = 90.0
    alert_windows_update_stale_days: int = 30
    alert_inventory_stale_hours: int = 24
    current_agent_version: str = "0.3.0"
    agent_job_timeout_minutes: int = 30

    notification_retry_limit: int = 3
    notification_timeout_seconds: float = 5.0
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "cyclope-central@example.local"
    smtp_use_tls: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
