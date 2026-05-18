"""Application settings via pydantic-settings."""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    APP_NAME: str = "Veklom BYOS Backend"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    APP_ENV: str = "development"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./veklom.db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET_KEY: str = "veklom-sovereign-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    ALLOWED_HOSTS: List[str] = ["*"]

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""

    # AI Providers
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""

    # Email
    RESEND_API_KEY: str = ""

    # Storage
    MINIO_ENDPOINT: str = ""
    S3_BUCKET: str = ""

    # License
    LICENSE_PRIVATE_KEY: str = ""
    LICENSE_SERVER_URL: str = ""

    # Frontend
    FRONTEND_URL: str = "http://localhost:5173"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
