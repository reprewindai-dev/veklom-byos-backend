"""Application settings via pydantic-settings, aligned to BYOS AI User Manual."""

import os
import json
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Union
from pydantic import field_validator

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8-sig", case_sensitive=True, extra="ignore")

    # Required — App
    SECRET_KEY: str = "change-me-in-production"
    ENCRYPTION_KEY: str = "change-me-in-production-aes-256"
    DATABASE_URL: str = "postgresql+asyncpg://byos:password@localhost:5432/byos_ai"
    REDIS_URL: str = "redis://localhost:6379/0"

    # LLM Engine
    LLM_BASE_URL: str = "http://host.docker.internal:11434"
    LLM_MODEL_DEFAULT: str = "qwen2.5:3b"
    LLM_FALLBACK: str = "groq"
    LLM_TIMEOUT_SECONDS: int = 60
    LLM_MAX_TOKENS: int = 2048

    # External AI Providers (Optional)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL_CHAT: str = "gpt-4o-mini"
    OPENAI_MODEL_WHISPER: str = "whisper-1"
    HUGGINGFACE_API_KEY: str = ""
    HUGGINGFACE_MODEL_CHAT: str = "mistralai/Mistral-7B-Instruct-v0.1"
    HUGGINGFACE_MODEL_EMBED: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Circuit Breaker
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-8b-instant"
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 3
    CIRCUIT_BREAKER_COOLDOWN_SECONDS: int = 60

    # Conversation Memory
    MEMORY_TTL_SECONDS: int = 86400
    MEMORY_MAX_MESSAGES: int = 20

    # Security
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    MAX_FAILED_LOGIN_ATTEMPTS: int = 10
    ACCOUNT_LOCKOUT_MINUTES: int = 30

    # Content Safety
    CONTENT_FILTERING_ENABLED: bool = True
    AGE_VERIFICATION_REQUIRED: bool = False

    # Billing (Stripe)
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # Infrastructure
    S3_ENDPOINT_URL: str = "http://minio:9000"
    S3_ACCESS_KEY_ID: str = "minioadmin"
    S3_SECRET_ACCESS_KEY: str = ""
    S3_BUCKET_NAME: str = "byos-ai"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CORS_ORIGINS: Union[str, List[str]] = "[]"

    # Observability
    SENTRY_DSN: str = ""
    LOG_FORMAT: str = "json"
    METRICS_ENABLED: bool = True
    GRAFANA_USER: str = "admin"
    GRAFANA_PASSWORD: str = ""
    
    # Internal variables kept to prevent app crash
    APP_NAME: str = "Veklom BYOS AI"
    VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    ALLOWED_HOSTS: Union[str, List[str]] = "*"
    
    # Keeping old JWT variables temporarily mapped to new ones for backward compatibility during refactor
    @property
    def JWT_SECRET_KEY(self) -> str:
        return self.SECRET_KEY
    
    @property
    def JWT_ALGORITHM(self) -> str:
        return self.ALGORITHM

    @field_validator("CORS_ORIGINS", "ALLOWED_HOSTS", mode="before")
    @classmethod
    def parse_list(cls, v):
        if isinstance(v, str):
            try:
                # Try parsing as JSON array (per manual)
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                # Fallback to comma separated
                return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


settings = Settings()
