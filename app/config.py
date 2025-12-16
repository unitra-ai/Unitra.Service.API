from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    app_name: str = "Unitra API"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/unitra"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # ML Service
    ml_service_url: str = "http://localhost:8001"

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    # Auth
    jwt_secret: str = "change-me-in-production"

    class Config:
        env_file = ".env"


settings = Settings()
