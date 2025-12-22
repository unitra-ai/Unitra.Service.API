"""Application configuration using pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "Unitra API"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = "development"  # development, staging, production

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/unitra"
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Security / JWT
    secret_key: str = "your-secret-key-change-in-production-min-32-chars"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # FastAPI-Users token lifetimes
    jwt_lifetime_seconds: int = 3600  # 1 hour
    password_reset_token_lifetime_seconds: int = 3600  # 1 hour
    verification_token_lifetime_seconds: int = 86400  # 24 hours

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:1420"]

    # External Services
    ml_service_url: str = "http://localhost:8001"
    modal_api_key: str = ""

    # Stripe
    stripe_api_key: str = ""
    stripe_webhook_secret: str = ""

    # OAuth2 (optional, for future social login)
    google_client_id: str = ""
    google_client_secret: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""
    discord_client_id: str = ""
    discord_client_secret: str = ""

    # Email (placeholder for email verification/reset)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = "noreply@unitra.app"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
