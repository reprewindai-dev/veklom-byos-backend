# Veklom Security & Operational Audit Report
Date: 2026-05-25

---

## P0 — CRITICAL (Fix Immediately)

### P0.1 Database Schema Completely Missing
- **Finding**: PostgreSQL database `byos_ai` contains 118 tables from a legacy project but ZERO Veklom tables.
- **Impact**: `users`, `exec_logs`, `workspaces`, `audit_logs`, `agents`, `pipelines`, `deployments`, etc. do not exist.
- **Symptoms**:
  - `POST /api/v1/auth/eval-session` → **500** (`relation "users" does not exist`)
  - `GET /api/v1/workspace/overview/live` → **500** (`relation "exec_logs" does not exist`)
  - Any authenticated endpoint that touches DB crashes with `UndefinedTableError`.
- **Root Cause**: `Base.metadata.create_all` in `main.py` lifespan either never ran or failed silently on first deployment. The old tables suggest the DB was reused from a previous app without schema migration.
- **Fix**: Run a proper schema initialization that imports ALL models and calls `Base.metadata.create_all`. Verify via psql afterwards.

### P0.2 OpenAPI / Docs Endpoint Missing
- **Finding**: `GET /api/v1/openapi.json` → **404**
- **Impact**: Swagger UI (`/docs`) cannot load the API schema. The docs page exists but shows no endpoints.
- **Root Cause**: FastAPI's auto-generated OpenAPI spec is likely disabled or the docs route is not configured.
- **Fix**: Ensure `docs_url` and `openapi_url` are set correctly in the FastAPI constructor.

### P0.3 robots.txt and sitemap.xml Missing
- **Finding**: Both return **200** but serve the homepage HTML (SPA fallback).
- **Impact**: Search engines may not crawl correctly. The 200 status is misleading.
- **Fix**: Create actual `/robots.txt` and `/sitemap.xml` static files or dedicated routes.

### P0.4 Feedback Endpoint Missing
- **Finding**: `GET /api/v1/feedback/` → **404**
- **Impact**: Feedback form on the homepage cannot submit.
- **Fix**: Add a `/feedback` POST route that stores feedback in the database or sends to a configured email/webhook.

### P0.5 Auth Endpoint Mismatch
- **Finding**: Frontend expects `/auth/signin` and `/auth/signup`; backend only has `/auth/login` and `/auth/register`.
- **Impact**: Users cannot authenticate through the standard login/signup flows.
- **Fix**: Add `/auth/signin` and `/auth/signup` aliases that proxy to `/auth/login` and `/auth/register`, OR update frontend references.

### P0.6 Missing Health / System Endpoints
- **Finding**:
  - `/api/v1/sys/health` → **404**
  - `/api/v1/sys/gpu` → **404**
  - `/api/v1/copilot/registry` → **404**
- **Impact**: Workspace health panel and copilot features are broken.
- **Fix**: Add stub or real implementations for these endpoints.

---

## P1 — HIGH (Fix This Week)

### P1.1 Server Header Leaks Information
- **Finding**: `server: uvicorn` header returned on all responses.
- **Impact**: Reveals server technology stack to attackers.
- **Fix**: Add middleware to override or remove the `server` header.

### P1.2 CSP Allows Unsafe Inline Scripts
- **Finding**: `content-security-policy` includes `script-src 'self' 'unsafe-inline' 'unsafe-eval'`.
- **Impact**: XSS mitigations weakened.
- **Fix**: Generate nonce-based CSP or remove `unsafe-inline`/`unsafe-eval` if the bundled SPA allows it. At minimum, add a `report-uri`.

### P1.3 External Service Unavailable
- **Finding**: `https://lockerphycer.veklom.com` → **503**
- **Impact**: "LockerSphere Security" link on homepage goes to dead service.
- **Fix**: Either restore the service or remove the CTA / update the link.

### P1.4 Grafana OTLP Tracing Failing
- **Finding**: Logs show repeated `StatusCode.UNAVAILABLE` for `otlp-gateway-prod-ca-east-0.grafana.net`.
- **Impact**: No observability traces being collected.
- **Fix**: Verify OTEL endpoint and credentials, or disable OTEL if not configured.

---

## P2 — MEDIUM (Fix Next Sprint)

### P2.1 Missing CORS Headers on Some Responses
- **Finding**: API responses don't include `access-control-allow-origin`.
- **Impact**: Cross-origin API calls may fail depending on browser behavior.
- **Fix**: Review CORS middleware configuration.

### P2.2 No Rate Limiting Observed
- **Finding**: No `X-RateLimit-*` headers or 429 responses on any endpoint.
- **Impact**: Susceptible to brute-force and abuse.
- **Fix**: Add rate limiting middleware (e.g., slowapi) on auth and public endpoints.

---

## P3 — LOW (Nice to Have)

### P3.1 405 on HEAD Requests for Static Pages
- **Finding**: `HEAD` on `/legal/terms`, `/terminal`, etc. returns **405**.
- **Impact**: Minor — some monitoring tools use HEAD.
- **Fix**: Configure Uvicorn/Starlette to allow HEAD for static file routes.

### P3.2 No Cache Headers on Static Assets
- **Finding**: Static files lack long-term cache headers.
- **Impact**: Repeat visitors re-download assets.
- **Fix**: Add `Cache-Control: max-age=31536000, immutable` to fingerprinted assets.

---

## P4 — INFO

### P4.1 Security Headers Present
- `strict-transport-security: max-age=31536000; includeSubDomains` ✓
- `x-frame-options: DENY` ✓
- `x-content-type-options: nosniff` ✓
- `x-xss-protection: 1; mode=block` ✓
- `referrer-policy: strict-origin-when-cross-origin` ✓
- `permissions-policy` restrictive ✓

### P4.2 Valid Static Pages
- Homepage, `/workspace`, `/command-center`, `/irongrid`, `/terminal`, `/docs`, `/uptime`, legal pages all return **200** with proper content.

### P4.3 `/api/v1/platform/pulse` Operational
- Returns **200** with JSON payload.

---

## Fix Plan (Ordered by Priority)

1. **P0.1** — Initialize database schema on the server by running a complete `create_all` script.
2. **P0.2** — Fix OpenAPI/docs configuration in `main.py`.
3. **P0.3** — Add `/robots.txt` and `/sitemap.xml` routes.
4. **P0.4** — Add `/api/v1/feedback` POST route.
5. **P0.5** — Add `/auth/signin` and `/auth/signup` aliases.
6. **P0.6** — Add stub `/sys/health`, `/sys/gpu`, `/copilot/registry` routes.
7. **P1.1** — Remove/override `server: uvicorn` header.
8. **P1.3** — Fix or remove `lockerphycer.veklom.com` link.
9. **P1.4** — Fix or disable Grafana OTLP exporter.
10. **P2.1** — Verify CORS middleware covers all API routes.
11. **P2.2** — Add rate limiting middleware.

---
*End of Report*
