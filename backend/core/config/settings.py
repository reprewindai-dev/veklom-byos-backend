"""Application settings via pydantic-settings, aligned to BYOS AI User Manual and Remote Production."""

import os
import json
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Union
from pydantic import field_validator

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8-sig", case_sensitive=False, extra="ignore")

    # Required — App
    SECRET_KEY: str = "change-me-in-production"
    ENCRYPTION_KEY: str = "change-me-in-production-aes-256"
    DATABASE_URL: str = "postgresql+asyncpg://byos:password@localhost:5432/byos_ai"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Core (Veklom Production)
    APP_NAME: str = "Veklom BYOS AI"
    VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    PORT: int = 8088
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_FILE_PATH: str = "/app/logs/veklom.log"
    CORS_ORIGINS: Union[str, List[str]] = "[]"
    ALLOWED_HOSTS: Union[str, List[str]] = "veklom.com,www.veklom.com,api.veklom.com,localhost,127.0.0.1,0.0.0.0,testserver"
    MAX_WORKERS: int = 4
    FRONTEND_URL: str = "http://localhost:3000"
    API_URL: str = "http://localhost:8088"
    API_BASE_URL: str = "http://localhost:8088"
    ADMIN_EMAIL: str = "founder@veklom.com"
    VEKLOM_API_BASE: str = "/api/v1"
    AI_CITIZENSHIP_SECRET: str = ""
    ENABLE_MFA: bool = True
    PASSWORD_MIN_LENGTH: int = 8
    MAX_FAILED_LOGIN_ATTEMPTS: int = 10
    ACCOUNT_LOCKOUT_DURATION_MINUTES: int = 30
    SESSION_TIMEOUT_MINUTES: int = 120

    # Redis
    REDIS_PASSWORD: str = ""
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

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
    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    SERPAPI_KEY: str = ""
    DEFAULT_AI_PROVIDER: str = "ollama"
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
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:3b"
    OLLAMA_AUTOSTART: bool = True
    OLLAMA_PULL_ON_BOOT: bool = True
    OLLAMA_STARTUP_TIMEOUT_MS: int = 120000
    VLLM_BASE_URL: str = ""
    FOUNDER_WORKSPACE_ID: str = ""
    PROVIDER_ENCRYPTION_KEY: str = ""

    # Local-First Escalation Router Settings
    DEFAULT_PROVIDER: str = "ollama"
    ENABLE_ESCALATION: bool = True
    OPENAI_MONTHLY_BUDGET_USD: float = 20.0
    OPENAI_DAILY_SOFT_LIMIT_USD: float = 0.75
    OPENAI_HARD_STOP_USD: float = 20.0
    OPENAI_MAX_CALLS_PER_REQUEST: int = 1

    # Circuit Breaker
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 3
    CIRCUIT_BREAKER_COOLDOWN_SECONDS: int = 60

    # Conversation Memory
    MEMORY_TTL_SECONDS: int = 86400
    MEMORY_MAX_MESSAGES: int = 20

    # Security / Token Expiry
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    MAX_FAILED_LOGIN_ATTEMPTS: int = 10
    ACCOUNT_LOCKOUT_MINUTES: int = 30
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_AUD_ENFORCEMENT: str = "warn"
    JWT_EXPECTED_AUDIENCE: str = "veklom-api"

    # Content Safety
    CONTENT_FILTERING_ENABLED: bool = True
    AGE_VERIFICATION_REQUIRED: bool = False

    # GitHub Auth Settings
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GITHUB_REDIRECT_URI: str = ""
    SMOKE_TEST_ENABLED: bool = False
    SMOKE_TEST_SECRET: str = ""

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

    # Billing (Stripe)
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # Storage (S3/MinIO)
    S3_ENDPOINT_URL: str = "http://minio:9000"
    S3_ACCESS_KEY_ID: str = "minioadmin"
    S3_SECRET_ACCESS_KEY: str = ""
    S3_BUCKET_NAME: str = "byos-ai"
    S3_REGION: str = "us-east-1"

    # License
    LICENSE_KEY: str = "YOUR_LICENSE_KEY"
    LICENSE_SERVER_URL: str = "https://license.veklom.com"
    PACKAGE_GUARD_ENABLED: bool = True

    # Observability
    SENTRY_DSN: str = ""
    SENTRY_ENVIRONMENT: str = "development"
    SENTRY_ORG: str = "veklom-sovereign-ai-hub-p0"
    SENTRY_PROJECT: str = "veklom"
    METRICS_ENABLED: bool = True
    GRAFANA_USER: str = "admin"
    GRAFANA_PASSWORD: str = ""

    # PostHog Analytics
    POSTHOG_API_KEY: str = ""
    POSTHOG_HOST: str = "https://app.posthog.com"
    POSTHOG_ENABLED: bool = True

    # Payment Webhook & Relayer
    WEBHOOK_SECRET: str = ""
    RELAYER_URL: str = ""
    CHAIN_ID: int = 1
    USDC_ADDRESS: str = ""

    # Performance Tuning
    MAX_CONCURRENT_REQUESTS: int = 100
    REQUEST_TIMEOUT_SECONDS: int = 30
    CACHE_TTL_SECONDS: int = 3600
    MAX_CONCURRENT_AI_REQUESTS: int = 10
    AI_REQUEST_TIMEOUT_SECONDS: int = 60
    MODEL_CACHE_DIR: str = "/app/models"

    # Server Configuration
    SERVER_IP: str = "YOUR_SERVER_IP"

    # Notifications
    SLACK_WEBHOOK_URL: str = "YOUR_SLACK_WEBHOOK_URL"

    # Base Builder Code (ERC-8021 onchain attribution)
    BASE_BUILDER_CODE: str = ""
    BASE_DEV_API_KEY: str = ""

    # x402 paid gateway secret
    UPSTREAM_GATEWAY_SECRET: str = ""
    RAPIDAPI_PROXY_SECRET: str = ""

    # UACP V2 Compiler (uacpgemini)
    UACPGEMINI_MODE: str = "mock"  # 'http' or 'mock'
    UACPGEMINI_BASE_URL: str = "http://uacpgemini:8000"
    UACPGEMINI_TIMEOUT_MS: int = 10000

    # UACP V3 Contextual Brain (uacpv3)
    UACPV3_MODE: str = "mock"  # 'http' or 'mock'
    UACPV3_BASE_URL: str = "http://uacpv3:8001"
    UACPV3_TIMEOUT_MS: int = 15000

    # UACP V4 Decision Kernel (govern)
    UACPV4_MODE: str = "mock"  # 'http' or 'mock'
    UACPV4_BASE_URL: str = "http://uacpv4:8002"
    UACPV4_TIMEOUT_MS: int = 15000

    # Keeping old JWT variables mapped to new ones for backward compatibility during refactor
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
