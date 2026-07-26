# Coolify Environment Variables Configuration

This file lists all environment variables that must be configured in Coolify for the Veklom BYOS Backend deployment.

## CRITICAL: Port Configuration

The application runs on port 80 internally. Coolify MUST be configured to:
1. Forward traffic from port 80 (HTTP) and 443 (HTTPS) to the container's port 80
2. Expose port 80 in the container configuration

**Current issue:** API routes are not accessible because Coolify is not forwarding traffic to port 80.

## CRITICAL: Database and Redis Configuration

The auth endpoints are currently returning 500 errors because the database connection is failing. You MUST configure these environment variables in Coolify:

### Database (REQUIRED for auth to work)
```
DATABASE_URL=postgresql+asyncpg://veklom_user:YOUR_SECURE_DB_PASSWORD@YOUR_EXTERNAL_DB_HOST:5432/veklom_production
POSTGRES_DB=veklom_production
POSTGRES_USER=veklom_user
POSTGRES_PASSWORD=YOUR_SECURE_DB_PASSWORD
```

### Redis (REQUIRED for session management)
```
REDIS_URL=redis://:YOUR_REDIS_PASSWORD@YOUR_EXTERNAL_REDIS_HOST:6379/0
REDIS_PASSWORD=YOUR_REDIS_PASSWORD
CELERY_BROKER_URL=redis://:YOUR_REDIS_PASSWORD@YOUR_EXTERNAL_REDIS_HOST:6379/0
CELERY_RESULT_BACKEND=redis://:YOUR_REDIS_PASSWORD@YOUR_EXTERNAL_REDIS_HOST:6379/1
```

**IMPORTANT**: Do NOT use Docker service names like `postgres:5432` or `redis:6379` in Coolify. Use the external IP `5.78.135.11` instead.

## Other Required Variables

### Core Application
```
APP_NAME=Veklom Sovereign AI Hub
VERSION=1.0.0
APP_ENV=production
PORT=8088
DEBUG=false
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE_PATH=/app/logs/veklom.log
CORS_ORIGINS=https://veklom.com,https://www.veklom.com,https://app.veklom.com
ALLOWED_HOSTS=veklom.com,www.veklom.com,app.veklom.com,localhost,127.0.0.1
MAX_WORKERS=4
FRONTEND_URL=https://veklom.com
API_URL=https://veklom.com
ADMIN_EMAIL=founder@veklom.com
VEKLOM_API_BASE=/api/v1
CAPI_BACKEND_URL=https://capi.veklom.com
CAPI_REGISTRY_TOKEN=YOUR_CAPI_REGISTRY_TOKEN
CAPPO_BACKEND_URL=https://cappo.veklom.com
PGL_LEDGER_URL=https://pgl.veklom.com
LOCKERPHYCER_URL=
```

### Security
```
SECRET_KEY=YOUR_SECURE_SECRET_KEY
AI_CITIZENSHIP_SECRET=YOUR_AI_CITIZENSHIP_SECRET
ENCRYPTION_KEY=YOUR_ENCRYPTION_KEY
ENABLE_MFA=true
PASSWORD_MIN_LENGTH=8
MAX_FAILED_LOGIN_ATTEMPTS=10
ACCOUNT_LOCKOUT_DURATION_MINUTES=30
SESSION_TIMEOUT_MINUTES=120
```

### Database (CRITICAL - Must use external database, not Docker service names)
```
POSTGRES_DB=veklom_production
POSTGRES_USER=veklom_user
POSTGRES_PASSWORD=YOUR_SECURE_DB_PASSWORD
DATABASE_URL=postgresql+asyncpg://veklom_user:YOUR_SECURE_DB_PASSWORD@YOUR_EXTERNAL_DB_HOST:5432/veklom_production
```

**IMPORTANT**: Replace `YOUR_EXTERNAL_DB_HOST` with your actual PostgreSQL server IP or hostname (e.g., `5.78.135.11`). Do NOT use `postgres:5432` as that's a Docker Compose service name and won't work in Coolify.

### Redis (CRITICAL - Must use external Redis, not Docker service names)
```
REDIS_PASSWORD=YOUR_REDIS_PASSWORD
REDIS_URL=redis://:YOUR_REDIS_PASSWORD@YOUR_EXTERNAL_REDIS_HOST:6379/0
CELERY_BROKER_URL=redis://:YOUR_REDIS_PASSWORD@YOUR_EXTERNAL_REDIS_HOST:6379/0
CELERY_RESULT_BACKEND=redis://:YOUR_REDIS_PASSWORD@YOUR_EXTERNAL_REDIS_HOST:6379/1
```

### JWT
```
JWT_SECRET_KEY=YOUR_JWT_SECRET_KEY
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30
```

### GitHub OAuth (PRODUCTION - Already Configured)
```
GITHUB_CLIENT_ID=YOUR_GITHUB_CLIENT_ID
GITHUB_CLIENT_SECRET=<NEW_SECRET>
GITHUB_REDIRECT_URI=https://api.veklom.com/api/v1/auth/github/callback
```

**Note:** These credentials are already configured on the production server. Do not change them unless rotating credentials.

### AI Providers
```
DEFAULT_AI_PROVIDER=ollama
OPENAI_API_KEY=YOUR_OPENAI_API_KEY
OPENAI_MODEL_CHAT=gpt-4o-mini
OPENAI_MODEL_WHISPER=whisper-1
ANTHROPIC_API_KEY=sk-ant-YOUR_ANTHROPIC_KEY_HERE
GROQ_API_KEY=gsk_YOUR_GROQ_KEY_HERE
GROQ_MODEL=llama-3.1-8b-instant
HUGGINGFACE_API_KEY=hf_YOUR_HUGGINGFACE_KEY_HERE
HUGGINGFACE_MODEL_CHAT=mistralai/Mistral-7B-Instruct-v0.1
HUGGINGFACE_MODEL_EMBED=sentence-transformers/all-MiniLM-L6-v2
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
SERPAPI_KEY=YOUR_SERPAPI_KEY
# Same host as the app container:
OLLAMA_BASE_URL=http://host.docker.internal:11434

# Separate Ollama server:
# OLLAMA_BASE_URL=http://YOUR_OLLAMA_SERVER_PRIVATE_IP:11434
OLLAMA_MODEL=qwen2.5:3b
```

**Important:** inside a Coolify/Docker container, `localhost` is the app
container itself. Do not use `OLLAMA_BASE_URL=http://localhost:11434` unless
Ollama is running in the same container, which is not the production topology.
If Ollama runs on its own Hetzner server, use that server's private WireGuard,
Tailscale, or firewall-restricted IP/hostname.

For CAPPO governed execution, set the same target using either:

```
OLLAMA_BASE_URL=http://YOUR_OLLAMA_SERVER_PRIVATE_IP:11434
```

or the explicit OpenAI-compatible CAPPO setting:

```
LLM_PROVIDER_NAME=ollama
LLM_BASE_URL=http://YOUR_OLLAMA_SERVER_PRIVATE_IP:11434/v1
LLM_MODEL=qwen2.5:3b
EXECUTOR_MODE=provider
```

### Stripe (Billing)
```
STRIPE_SECRET_KEY=YOUR_STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET=YOUR_STRIPE_WEBHOOK_SECRET
STRIPE_PUBLISHABLE_KEY=YOUR_STRIPE_PUBLISHABLE_KEY
```

### Email (Resend)
```
RESEND_API_KEY=YOUR_RESEND_API_KEY
RESEND_WORKER_KEY=YOUR_RESEND_WORKER_KEY
RESEND_SMTP_KEY=YOUR_RESEND_SMTP_KEY
RESEND_VERCEL_KEY=YOUR_RESEND_VERCEL_KEY
EMAIL_FROM=Veklom <hello@mail.veklom.com>
RESEND_WEBHOOK_URL=https://api.veklom.com/api/v1/webhooks/resend
SMTP_HOST=smtp.resend.com
SMTP_PORT=465
SMTP_PORT_TLS=2465
SMTP_USER=resend
SMTP_PASSWORD=YOUR_RESEND_SMTP_KEY
```

### Storage (S3/MinIO)
```
S3_ENDPOINT_URL=YOUR_S3_ENDPOINT_URL
S3_ACCESS_KEY_ID=YOUR_S3_ACCESS_KEY_ID
S3_SECRET_ACCESS_KEY=YOUR_S3_SECRET_ACCESS_KEY
S3_BUCKET_NAME=YOUR_S3_BUCKET_NAME
S3_REGION=us-east-1
```

### License
```
LICENSE_KEY=YOUR_LICENSE_KEY
LICENSE_SERVER_URL=https://license.veklom.com
PACKAGE_GUARD_ENABLED=true
```

### Observability (Sentry)
```
SENTRY_DSN=YOUR_SENTRY_DSN
SENTRY_ENVIRONMENT=production
SENTRY_ORG=veklom-sovereign-ai-hub-p0
SENTRY_PROJECT=veklom
```

### Observability (Grafana Cloud)
```
GRAFANA_INSTANCE_ID=1652772
GRAFANA_API_TOKEN=YOUR_GRAFANA_API_TOKEN
PROMETHEUS_API_TOKEN=YOUR_GRAFANA_API_TOKEN
PROMETHEUS_REMOTE_WRITE_URL=https://prometheus-prod-32-prod-ca-east-0.grafana.net/api/prom/push
PROMETHEUS_USERNAME=3229768
PROMETHEUS_PASSWORD=YOUR_GRAFANA_API_TOKEN
LOKI_URL=https://logs-prod-018.grafana.net
LOKI_USERNAME=1610559
LOKI_PASSWORD=YOUR_GRAFANA_API_TOKEN
ALERTMANAGER_URL=https://alertmanager-prod-ca-east-0.grafana.net
ALERTMANAGER_USERNAME=1612824
ALERTMANAGER_PASSWORD=YOUR_GRAFANA_API_TOKEN
PYROSCOPE_URL=https://profiles-prod-006.grafana.net
PYROSCOPE_USERNAME=1652772
PYROSCOPE_PASSWORD=YOUR_GRAFANA_API_TOKEN
SIGIL_ENDPOINT=https://sigil-prod-ca-east-0.grafana.net
SIGIL_INSTANCE_ID=1652772
SIGIL_API_TOKEN=YOUR_GRAFANA_API_TOKEN
OTEL_SERVICE_NAME=veklom-sovereign-ai-hub
OTEL_EXPORTER_OTLP_ENDPOINT=https://otlp-gateway-prod-ca-east-0.grafana.net/otlp
OTEL_EXPORTER_OTLP_HEADERS=YOUR_OTEL_HEADERS
ALLOY_REMOTE_WRITE_URL=https://prometheus-prod-32-prod-ca-east-0.grafana.net/api/prom/push
```

### Performance Tuning
```
MAX_CONCURRENT_REQUESTS=100
REQUEST_TIMEOUT_SECONDS=30
CACHE_TTL_SECONDS=3600
MAX_CONCURRENT_AI_REQUESTS=10
AI_REQUEST_TIMEOUT_SECONDS=60
MODEL_CACHE_DIR=/app/models
```

### Server Configuration
```
SERVER_IP=YOUR_SERVER_IP
```

### Notifications
```
SLACK_WEBHOOK_URL=https://veklom.slack.com
```

## Coolify Services Configuration

### Database Service
- Use Coolify's managed PostgreSQL or external PostgreSQL
- Update `DATABASE_URL` accordingly
- Update `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` if using external

### Redis Service
- Use Coolify's managed Redis or external Redis
- Update `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` accordingly
- Update `REDIS_PASSWORD` if using external

## Deployment Steps in Coolify

1. Create new Application from Git source
2. Point to this repository
3. Set build pack: Dockerfile
4. Add all environment variables from above
5. Set domain and enable HTTPS
6. Configure resource limits:
   - CPU: 1-2 cores minimum
   - RAM: 2GB minimum, 4GB recommended
   - Disk: 20GB minimum
7. Deploy

## Health Check

The application exposes a health check endpoint at `/health` that Coolify will use for container health monitoring.

## Important Notes

- Never commit real secrets to the repository
- Use Coolify's environment variable management for secrets
- The application runs as non-root user `veklom` for security
- Health check endpoint: `/health`
- Main entry point: `backend.apps.api.main:app`
