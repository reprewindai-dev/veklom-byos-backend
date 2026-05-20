# Coolify Environment Variables Configuration

This file lists all environment variables that must be configured in Coolify for the Veklom BYOS Backend deployment.

## Required Variables (Must Set)

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
ALLOWED_HOSTS=veklom.com,www.veklom.com,app.veklom.com
MAX_WORKERS=4
FRONTEND_URL=https://veklom.com
API_URL=https://veklom.com
ADMIN_EMAIL=founder@veklom.com
VEKLOM_API_BASE=/api/v1
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

### Database
```
POSTGRES_DB=veklom_production
POSTGRES_USER=veklom_user
POSTGRES_PASSWORD=YOUR_SECURE_DB_PASSWORD
DATABASE_URL=postgresql+asyncpg://veklom_user:YOUR_SECURE_DB_PASSWORD@postgres:5432/veklom_production
```

### Redis
```
REDIS_PASSWORD=YOUR_REDIS_PASSWORD
REDIS_URL=redis://:YOUR_REDIS_PASSWORD@redis:6379/0
CELERY_BROKER_URL=redis://:YOUR_REDIS_PASSWORD@redis:6379/0
CELERY_RESULT_BACKEND=redis://:YOUR_REDIS_PASSWORD@redis:6379/1
```

### JWT
```
JWT_SECRET_KEY=YOUR_JWT_SECRET_KEY
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30
```

### AI Providers
```
DEFAULT_AI_PROVIDER=openai
OPENAI_API_KEY=YOUR_OPENAI_API_KEY
ANTHROPIC_API_KEY=YOUR_ANTHROPIC_API_KEY
HUGGINGFACE_API_KEY=YOUR_HUGGINGFACE_API_KEY
SERPAPI_KEY=YOUR_SERPAPI_KEY
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
EMAIL_FROM=Veklom <noreply@veklom.com>
RESEND_WEBHOOK_URL=https://veklom.com/api/v1/webhooks/resend
SMTP_HOST=smtp.resend.com
SMTP_PORT=465
SMTP_PORT_TLS=2465
SMTP_USER=resend
SMTP_PASSWORD=YOUR_SMTP_PASSWORD
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
GRAFANA_INSTANCE_ID=YOUR_GRAFANA_INSTANCE_ID
GRAFANA_API_TOKEN=YOUR_GRAFANA_API_TOKEN
PROMETHEUS_API_TOKEN=YOUR_PROMETHEUS_API_TOKEN
PROMETHEUS_REMOTE_WRITE_URL=https://prometheus-prod-32-prod-ca-east-0.grafana.net/api/prom/push
PROMETHEUS_USERNAME=YOUR_PROMETHEUS_USERNAME
PROMETHEUS_PASSWORD=YOUR_PROMETHEUS_PASSWORD
LOKI_URL=https://logs-prod-018.grafana.net
LOKI_USERNAME=YOUR_LOKI_USERNAME
LOKI_PASSWORD=YOUR_LOKI_PASSWORD
ALERTMANAGER_URL=https://alertmanager-prod-ca-east-0.grafana.net
ALERTMANAGER_USERNAME=YOUR_ALERTMANAGER_USERNAME
ALERTMANAGER_PASSWORD=YOUR_ALERTMANAGER_PASSWORD
PYROSCOPE_URL=https://profiles-prod-006.grafana.net
PYROSCOPE_USERNAME=YOUR_PYROSCOPE_USERNAME
PYROSCOPE_PASSWORD=YOUR_PYROSCOPE_PASSWORD
SIGIL_ENDPOINT=https://sigil-prod-ca-east-0.grafana.net
SIGIL_INSTANCE_ID=YOUR_SIGIL_INSTANCE_ID
SIGIL_API_TOKEN=YOUR_SIGIL_API_TOKEN
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
SLACK_WEBHOOK_URL=YOUR_SLACK_WEBHOOK_URL
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

The application exposes a health check endpoint at `/api/v1/health` that Coolify will use for container health monitoring.

## Important Notes

- Never commit real secrets to the repository
- Use Coolify's environment variable management for secrets
- The application runs as non-root user `veklom` for security
- Health check endpoint: `/api/v1/health`
- Main entry point: `backend.apps.api.main:app`
