"""Application settings via pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Union
from pydantic import field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8-sig", case_sensitive=True, extra="ignore")

    APP_NAME: str = "Veklom Sovereign AI Hub"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_FILE_PATH: str = "/app/logs/veklom.log"
    APP_ENV: str = "development"
    PORT: int = 8088
    MAX_WORKERS: int = 4

    # URLs
    FRONTEND_URL: str = "http://localhost:5173"
    API_URL: str = "http://localhost:8088"
    ADMIN_EMAIL: str = "admin@localhost"
    VEKLOM_API_BASE: str = "/api/v1"

    # Security
    SECRET_KEY: str = ""
    AI_CITIZENSHIP_SECRET: str = ""
    ENCRYPTION_KEY: str = ""
    ENABLE_MFA: bool = True
    PASSWORD_MIN_LENGTH: int = 8
    MAX_FAILED_LOGIN_ATTEMPTS: int = 10
    ACCOUNT_LOCKOUT_DURATION_MINUTES: int = 30
    SESSION_TIMEOUT_MINUTES: int = 120

    # Database
    POSTGRES_DB: str = "veklom"
    POSTGRES_USER: str = "veklom"
    POSTGRES_PASSWORD: str = ""
    DATABASE_URL: str = "sqlite+aiosqlite:///./veklom.db"

    # Redis
    REDIS_PASSWORD: str = ""
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # JWT
    JWT_SECRET_KEY: str = "veklom-sovereign-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: Union[str, List[str]] = "*"
    ALLOWED_HOSTS: Union[str, List[str]] = "*"

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""

    # AI Providers
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    HUGGINGFACE_API_KEY: str = ""
    SERPAPI_KEY: str = ""
    DEFAULT_AI_PROVIDER: str = "openai"
    AI_PROVIDER: str = ""
    LLM_PROVIDER: str = ""
    AI_FALLBACK_PROVIDER: str = ""
    GROQ_API_KEY: str = ""
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROQ_MODEL: str = "llama-3.1-8b-instant"
    HF_API_URL: str = "https://router.huggingface.co/v1"
    HF_MODEL: str = "meta-llama/Llama-3.1-8B-Instruct:fastest"
    HF_TOKEN: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GOOGLE_CLOUD_PROJECT: str = ""
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    BEDROCK_MODEL_ID: str = ""
    OLLAMA_BASE_URL: str = ""
    OLLAMA_MODEL: str = "qwen2.5:3b"
    OLLAMA_AUTOSTART: bool = False
    OLLAMA_PULL_ON_BOOT: bool = False
    OLLAMA_STARTUP_TIMEOUT_MS: int = 120000
    VLLM_BASE_URL: str = ""

    # Email (Resend)
    RESEND_API_KEY: str = ""
    RESEND_WORKER_KEY: str = ""
    RESEND_SMTP_KEY: str = ""
    RESEND_VERCEL_KEY: str = ""
    FROM_EMAIL: str = "noreply@yourdomain.com"
    RESEND_WEBHOOK_URL: str = ""
    EMAIL_FROM: str = ""
    SMTP_HOST: str = "smtp.resend.com"
    SMTP_PORT: int = 465
    SMTP_PORT_TLS: int = 2465
    SMTP_USER: str = "resend"
    SMTP_PASSWORD: str = ""

    # Storage (S3/MinIO)
    S3_ENDPOINT_URL: str = ""
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""
    S3_BUCKET_NAME: str = ""
    S3_REGION: str = "us-east-1"
    # Legacy storage vars (for backward compatibility)
    MINIO_ENDPOINT: str = ""
    S3_BUCKET: str = ""

    # License
    LICENSE_PRIVATE_KEY: str = ""
    LICENSE_SERVER_URL: str = ""
    LICENSE_KEY: str = ""
    PACKAGE_GUARD_ENABLED: bool = True

    # Observability (Sentry)
    SENTRY_DSN: str = ""
    SENTRY_ENVIRONMENT: str = "production"
    SENTRY_ORG: str = ""
    SENTRY_PROJECT: str = ""

    # Observability (Grafana Cloud)
    GRAFANA_INSTANCE_ID: str = ""
    GRAFANA_API_TOKEN: str = ""
    PROMETHEUS_API_TOKEN: str = ""
    PROMETHEUS_REMOTE_WRITE_URL: str = ""
    PROMETHEUS_USERNAME: str = ""
    PROMETHEUS_PASSWORD: str = ""
    LOKI_URL: str = ""
    LOKI_USERNAME: str = ""
    LOKI_PASSWORD: str = ""
    ALERTMANAGER_URL: str = ""
    ALERTMANAGER_USERNAME: str = ""
    ALERTMANAGER_PASSWORD: str = ""
    PYROSCOPE_URL: str = ""
    PYROSCOPE_USERNAME: str = ""
    PYROSCOPE_PASSWORD: str = ""
    SIGIL_ENDPOINT: str = ""
    SIGIL_INSTANCE_ID: str = ""
    SIGIL_API_TOKEN: str = ""
    OTEL_SERVICE_NAME: str = "veklom-sovereign-ai-hub"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = ""
    OTEL_EXPORTER_OTLP_HEADERS: str = ""
    ALLOY_REMOTE_WRITE_URL: str = ""

    # Async Jobs (QStash)
    QSTASH_TOKEN: str = ""
    QSTASH_CURRENT_SIGNING_KEY: str = ""
    QSTASH_NEXT_SIGNING_KEY: str = ""

    # Performance Tuning
    MAX_CONCURRENT_REQUESTS: int = 100
    REQUEST_TIMEOUT_SECONDS: int = 30
    CACHE_TTL_SECONDS: int = 3600
    MAX_CONCURRENT_AI_REQUESTS: int = 10
    AI_REQUEST_TIMEOUT_SECONDS: int = 60
    MODEL_CACHE_DIR: str = "/app/models"

    # Server Configuration
    SERVER_IP: str = ""

    # Notifications
    SLACK_WEBHOOK_URL: str = ""

    @field_validator("CORS_ORIGINS", "ALLOWED_HOSTS", mode="before")
    @classmethod
    def parse_list(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v


settings = Settings()
