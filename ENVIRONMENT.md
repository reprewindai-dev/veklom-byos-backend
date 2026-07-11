# ENVIRONMENT.md — All Environment Variables

Copy `.env.example` to `.env` (dev) or `.env.production.example` to `.env.production` (prod).

Never commit real secrets to any repository.

---

## Required — Core

| Variable | Description | Example |
|----------|-------------|----------|
| `APP_NAME` | Application name | `Veklom Sovereign AI Hub` |
| `VERSION` | Application version | `1.0.0` |
| `APP_ENV` | Runtime environment | `production` or `development` |
| `PORT` | Server port | `80` |
| `DEBUG` | Debug mode | `false` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `LOG_FORMAT` | Log format | `json` |
| `LOG_FILE_PATH` | Log file path | `/app/logs/veklom.log` |
| `CORS_ORIGINS` | Comma-separated allowed origins | `https://veklom.com,https://www.veklom.com,https://app.veklom.com` |
| `ALLOWED_HOSTS` | Comma-separated allowed host headers | `veklom.com,www.veklom.com,app.veklom.com,localhost,127.0.0.1` |
| `MAX_WORKERS` | Uvicorn worker count | `4` |
| `FRONTEND_URL` | Frontend URL | `https://veklom.com` |
| `API_URL` | API URL | `https://veklom.com` |
| `ADMIN_EMAIL` | Admin email address | `founder@veklom.com` |

---

## Required — Security

| Variable | Description | Example |
|----------|-------------|----------|
| `SECRET_KEY` | Application secret key | _(secret)_ |
| `AI_CITIZENSHIP_SECRET` | AI citizenship verification secret | _(secret)_ |
| `ENCRYPTION_KEY` | Encryption key for sensitive data | _(secret)_ |
| `ENABLE_MFA` | Enable multi-factor authentication | `true` |
| `PASSWORD_MIN_LENGTH` | Minimum password length | `8` |
| `MAX_FAILED_LOGIN_ATTEMPTS` | Max failed login attempts before lockout | `10` |
| `ACCOUNT_LOCKOUT_DURATION_MINUTES` | Account lockout duration in minutes | `30` |
| `SESSION_TIMEOUT_MINUTES` | Session timeout in minutes | `120` |

---

## Required — Database

| Variable | Description | Example |
|----------|-------------|----------|
| `POSTGRES_DB` | PostgreSQL database name | `veklom_production` |
| `POSTGRES_USER` | PostgreSQL username | `veklom_user` |
| `POSTGRES_PASSWORD` | PostgreSQL password | _(secret)_ |
| `DATABASE_URL` | PostgreSQL async connection string | `postgresql+asyncpg://user:pass@host:5432/veklom` |

---

## Required — Redis

| Variable | Description | Example |
|----------|-------------|----------|
| `REDIS_PASSWORD` | Redis password | _(secret)_ |
| `REDIS_URL` | Redis connection string | `redis://:password@host:6379/0` |
| `CELERY_BROKER_URL` | Celery broker URL | `redis://:password@host:6379/0` |
| `CELERY_RESULT_BACKEND` | Celery result backend | `redis://:password@host:6379/1` |

---

## Required — JWT

| Variable | Description | Example |
|----------|-------------|----------|
| `JWT_SECRET_KEY` | Secret for signing JWT tokens — generate with `openssl rand -hex 32` | _(secret)_ |
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime | `30` |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime | `30` |

---

## Required — AI Providers

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key for completions |
| `ANTHROPIC_API_KEY` | Anthropic Claude API key (optional) |
| `HUGGINGFACE_API_KEY` | HuggingFace API key (optional) |
| `SERPAPI_KEY` | SerpAPI key for search (optional) |
| `OLLAMA_BASE_URL` | Ollama endpoint for private model runtime (optional) |
| `VLLM_BASE_URL` | vLLM endpoint for private GPU runtime (optional) |
| `DEFAULT_AI_PROVIDER` | Default provider: `openai`, `anthropic`, `ollama`, `vllm` |

---

## Required — Billing (Stripe)

| Variable | Description |
|----------|-------------|
| `STRIPE_SECRET_KEY` | Stripe secret key (`sk_live_...` or `sk_test_...`) |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret (`whsec_...`) |
| `STRIPE_PUBLISHABLE_KEY` | Stripe publishable key (for frontend) |

---

## Required — Email (Resend)

| Variable | Description |
|----------|-------------|
| `RESEND_API_KEY` | Resend API key for transactional email |
| `RESEND_WORKER_KEY` | Resend worker key |
| `RESEND_SMTP_KEY` | Resend SMTP key |
| `RESEND_VERCEL_KEY` | Resend Vercel integration key |
| `FROM_EMAIL` | Sender email address |
| `RESEND_WEBHOOK_URL` | Resend webhook URL |
| `SMTP_HOST` | SMTP host |
| `SMTP_PORT` | SMTP port |
| `SMTP_PORT_TLS` | SMTP TLS port |
| `SMTP_USER` | SMTP username |
| `SMTP_PASSWORD` | SMTP password |

---

## Required — Storage (S3/MinIO)

| Variable | Description |
|----------|-------------|
| `S3_ENDPOINT_URL` | MinIO or S3 endpoint URL |
| `S3_ACCESS_KEY_ID` | Access key |
| `S3_SECRET_ACCESS_KEY` | Secret key |
| `S3_BUCKET_NAME` | Storage bucket name |
| `S3_REGION` | Region (use `us-east-1` for MinIO) |

---

## Optional — License

| Variable | Description |
|----------|-------------|
| `LICENSE_PRIVATE_KEY` | RSA private key for signing buyer licenses |
| `LICENSE_SERVER_URL` | Your license validation endpoint |
| `LICENSE_KEY` | License key |
| `PACKAGE_GUARD_ENABLED` | Enable/disable package guard check | `true` |

---

## Optional — Observability (Sentry)

| Variable | Description |
|----------|-------------|
| `SENTRY_DSN` | Sentry error tracking DSN |
| `SENTRY_ENVIRONMENT` | Sentry environment name |
| `SENTRY_ORG` | Sentry organization slug |
| `SENTRY_PROJECT` | Sentry project slug |

---

## Optional — Observability (Grafana Cloud)

| Variable | Description |
|----------|-------------|
| `GRAFANA_INSTANCE_ID` | Grafana Cloud instance ID |
| `GRAFANA_API_TOKEN` | Grafana API token |
| `PROMETHEUS_API_TOKEN` | Prometheus API token |
| `PROMETHEUS_REMOTE_WRITE_URL` | Prometheus remote write URL |
| `PROMETHEUS_USERNAME` | Prometheus username |
| `PROMETHEUS_PASSWORD` | Prometheus password |
| `LOKI_URL` | Loki logs URL |
| `LOKI_USERNAME` | Loki username |
| `LOKI_PASSWORD` | Loki password |
| `ALERTMANAGER_URL` | Alertmanager URL |
| `ALERTMANAGER_USERNAME` | Alertmanager username |
| `ALERTMANAGER_PASSWORD` | Alertmanager password |
| `PYROSCOPE_URL` | Pyroscope profiling URL |
| `PYROSCOPE_USERNAME` | Pyroscope username |
| `PYROSCOPE_PASSWORD` | Pyroscope password |
| `SIGIL_ENDPOINT` | Sigil endpoint |
| `SIGIL_INSTANCE_ID` | Sigil instance ID |
| `SIGIL_API_TOKEN` | Sigil API token |
| `OTEL_SERVICE_NAME` | OpenTelemetry service name |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OpenTelemetry OTLP endpoint |
| `OTEL_EXPORTER_OTLP_HEADERS` | OpenTelemetry OTLP headers |
| `ALLOY_REMOTE_WRITE_URL` | Alloy remote write URL |

---

## Optional — Async Jobs (QStash)

| Variable | Description |
|----------|-------------|
| `QSTASH_TOKEN` | Upstash QStash token for job queue |
| `QSTASH_CURRENT_SIGNING_KEY` | QStash webhook signing key |
| `QSTASH_NEXT_SIGNING_KEY` | QStash webhook rotation key |

---

## Optional — Performance Tuning

| Variable | Description |
|----------|-------------|
| `MAX_CONCURRENT_REQUESTS` | Maximum concurrent requests |
| `REQUEST_TIMEOUT_SECONDS` | Request timeout in seconds |
| `CACHE_TTL_SECONDS` | Cache TTL in seconds |
| `MAX_CONCURRENT_AI_REQUESTS` | Maximum concurrent AI requests |
| `AI_REQUEST_TIMEOUT_SECONDS` | AI request timeout in seconds |
| `MODEL_CACHE_DIR` | Model cache directory |

---

## Optional — Server Configuration

| Variable | Description |
|----------|-------------|
| `SERVER_IP` | Server IP address |

---

## Optional — Notifications

| Variable | Description |
|----------|-------------|
| `SLACK_WEBHOOK_URL` | Slack webhook URL for notifications |
