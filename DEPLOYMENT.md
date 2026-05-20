# DEPLOYMENT.md — Production Deployment Guide

## Supported Deployment Targets

| Method | Recommended For |
|--------|----------------|
| Docker + Coolify | Self-hosted VPS (Hetzner, Contabo, your server) |
| Docker Compose | Single-machine production |
| Render.com | Managed cloud — quickest path to live |
| Hetzner Cloud | Cost-effective EU/global VPS |
| Any Docker host | Universal — runs anywhere Docker runs |

---

## Docker Deploy (Recommended)

### Build

```bash
docker build -t veklom-byos-backend .
```

### Run

```bash
docker run -d \
  --name veklom-api \
  -p 8000:8000 \
  --env-file .env.production \
  veklom-byos-backend
```

### With Docker Compose

```bash
cp .env.production.example .env.production
# Fill in all production secrets
docker compose -f docker-compose.yml up -d
```

---

## Coolify Deploy (Self-Hosted)

### Runtime Configuration

Coolify will use the Dockerfile at the root of this repository. The runtime is configured as:

- **Base Image**: `python:3.11-slim`
- **Port**: `8000` (exposed for Coolify's reverse proxy)
- **Health Check**: `/api/v1/health` endpoint
- **Command**: `uvicorn backend.apps.api.main:app --host 0.0.0.0 --port 8000`
- **Worker User**: Non-root user `veklom` (UID 1000) for security

### Deployment Steps

1. In Coolify, create a new **Application** from Git source
2. Point to this repo
3. Set build pack: **Dockerfile**
4. Configure environment variables from `.env.production.example`:
   - Required: `APP_ENV`, `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET_KEY`, `CORS_ORIGINS`
   - AI Providers: `OPENAI_API_KEY`, `DEFAULT_AI_PROVIDER`
   - Billing: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PUBLISHABLE_KEY`
   - Storage: `S3_ENDPOINT_URL`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_BUCKET_NAME`
5. Set domain and enable HTTPS
6. Configure resource limits (recommended):
   - CPU: 1-2 cores minimum
   - RAM: 2GB minimum, 4GB recommended
   - Disk: 20GB minimum
7. Deploy

### Coolify-Specific Notes

- Coolify automatically handles Let's Encrypt SSL, reverse proxy, and restart policies
- The health check endpoint is `/api/v1/health` - Coolify will use this for container health monitoring
- For database and Redis, either:
  - Use Coolify's managed services (PostgreSQL + Redis)
  - Or use external services and update `DATABASE_URL` and `REDIS_URL` accordingly
- The application runs as a non-root user for security compliance

---

## Render.com Deploy

1. New Web Service → Connect this repo
2. Runtime: **Docker**
3. Add environment variables from `.env.production.example`
4. Health check path: `/api/v1/health`
5. Deploy

---

## Post-Deploy Steps

```bash
# Run migrations against production DB
alembic upgrade head

# Verify health
curl https://your-domain.com/api/v1/health

# Verify status
curl https://your-domain.com/api/v1/status

# Activate license
curl -X POST https://your-domain.com/api/v1/license/activate \
  -H 'Content-Type: application/json' \
  -d '{"license_key": "YOUR-LICENSE-KEY"}'
```

---

## Cloudflare Tunnel (BYOS Recommended)

For buyers running on private servers without exposing a port:

```bash
# Install cloudflared
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 \
  -o /usr/local/bin/cloudflared
chmod +x /usr/local/bin/cloudflared

# Authenticate
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create veklom-api

# Route
cloudflared tunnel route dns veklom-api api.yourdomain.com

# Run
cloudflared tunnel run --url http://localhost:8088 veklom-api
```

This gives your backend a public HTTPS URL without opening firewall ports.

---

## Health Check URL

```
GET /api/v1/health
```

Expected response:
```json
{"status": "ok", "version": "...", "timestamp": "..."}
```
