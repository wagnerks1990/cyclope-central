from functools import lru_cache

from pydantic import Field, model_validator
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
    redis_url: str = "redis://redis:6379/0"
    cors_allowed_origins: str = "http://localhost:3000"
    jwt_issuer: str = "cyclope-central"
    jwt_audience: str = "cyclope-central-dashboard"
    jwt_secret_key: str = "change-me-in-production"
    jwt_secret: str = ""
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

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.jwt_secret:
            self.jwt_secret_key = self.jwt_secret
        if self.environment.lower() == "production":
            values = {
                "DATABASE_URL": self.database_url,
                "REDIS_URL": self.redis_url,
                "JWT_SECRET": self.jwt_secret_key,
                "TOKEN_HASH_PEPPER": self.token_hash_pepper,
                "CORS_ALLOWED_ORIGINS": self.cors_allowed_origins,
            }
            missing = [name for name, value in values.items() if not value]
            if missing:
                raise ValueError(f"Missing required production settings: {', '.join(missing)}")
            insecure = [
                name
                for name, value in values.items()
                if _is_placeholder_secret(value) or value in _development_defaults(name)
            ]
            if insecure:
                raise ValueError(
                    "Production settings contain insecure placeholder/default values: "
                    + ", ".join(insecure)
                )
            if len(self.jwt_secret_key) < 32:
                raise ValueError("Production JWT secret must be at least 32 characters")
            if len(self.token_hash_pepper) < 32:
                raise ValueError("Production token hash pepper must be at least 32 characters")
        return self

    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


def _is_placeholder_secret(value: str) -> bool:
    lowered = value.lower()
    return any(
        marker in lowered
        for marker in ("change-me", "replace-with", "replace_with", "example", "placeholder")
    )


def _development_defaults(name: str) -> set[str]:
    return {
        "DATABASE_URL": {"postgresql+psycopg://cyclope:cyclope@postgres:5432/cyclope"},
        "JWT_SECRET": {"change-me-in-production"},
        "TOKEN_HASH_PEPPER": {"change-me-token-pepper"},
        "CORS_ALLOWED_ORIGINS": {"http://localhost:3000"},
    }.get(name, set())


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
