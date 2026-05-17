# ENVIRONMENT.md — All Environment Variables

Copy `.env.example` to `.env` (dev) or `.env.production.example` to `.env.production` (prod).

Never commit real secrets to any repository.

---

## Required — Core

| Variable | Description | Example |
|----------|-------------|----------|
| `APP_ENV` | Runtime environment | `production` or `development` |
| `DATABASE_URL` | PostgreSQL async connection string | `postgresql+asyncpg://user:pass@host:5432/veklom` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `JWT_SECRET_KEY` | Secret for signing JWT tokens — generate with `openssl rand -hex 32` | _(secret)_ |
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime | `30` |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime | `30` |
| `CORS_ORIGINS` | Comma-separated allowed origins | `https://app.yourdomain.com` |

---

## Required — AI Providers

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key for completions |
| `ANTHROPIC_API_KEY` | Anthropic Claude API key (optional) |
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
| `FROM_EMAIL` | Sender email address | `noreply@yourdomain.com` |

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
| `PACKAGE_GUARD_ENABLED` | Enable/disable package guard check | `true` |

---

## Optional — Async Jobs (QStash)

| Variable | Description |
|----------|-------------|
| `QSTASH_TOKEN` | Upstash QStash token for job queue |
| `QSTASH_CURRENT_SIGNING_KEY` | QStash webhook signing key |
| `QSTASH_NEXT_SIGNING_KEY` | QStash webhook rotation key |

---

## Optional — Advanced

| Variable | Description |
|----------|-------------|
| `LOG_LEVEL` | Logging level | `INFO` |
| `SENTRY_DSN` | Sentry error tracking DSN |
| `MAX_WORKERS` | Uvicorn worker count | `4` |
| `PORT` | Server port | `8000` |
