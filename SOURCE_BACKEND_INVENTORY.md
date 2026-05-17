# SOURCE_BACKEND_INVENTORY.md

> Source repo: `reprewindai-dev/byosbackened`  
> Source path: `backend/`  
> Source commit: `8241cb7d45f718a46decc0b5e825bb223973c3f3`  
> Inventory generated: 2026-05-17

---

## Copied Folders

| Folder | Reason Copied |
|--------|---------------|
| `backend/apps/api/` | Core FastAPI application — 43 routers, main.py, middleware |
| `backend/core/` | Config, auth, database engine, security utilities |
| `backend/db/` | SQLAlchemy models, migrations (Alembic) |
| `backend/license/` | License server, package guard, buyer activation |
| `backend/scripts/` | Deploy helpers, health check, license validation scripts |
| `backend/tests/` | Backend test suite (pytest) |

---

## Rejected Folders

| Folder | Reason Rejected |
|--------|----------------|
| `frontend/` | React/TypeScript SPA workspace — not part of backend product |
| `backend/landing/` | Cloudflare Pages static marketing site — not backend product |
| `backend/landing-dev/` | Dev/staging variant of landing site |
| `workspace-assets/` | Pre-built JS/CSS bundles for frontend workspace app |
| `.cascade_refs/` | AI assistant IDE reference files — internal tooling only |
| `dist/` | Generated build artifacts — never committed to sellable repo |
| `build/` | Generated build artifacts |
| `backend/BLOG_PLAN.md` | Internal marketing content — not for buyers |
| `backend/MARKETING_AND_SEO_PLAYBOOK.md` | Internal marketing strategy |
| `backend/PILOT_PRICING_INTERNAL.md` | Internal pricing notes — confidential |
| `backend/PRICING_TRUTH.md` | Internal pricing strategy |
| `backend/EU_REPRESENTATIVE_REMINDER.md` | Internal compliance reminder |
| `backend/EXECUTIVE_AUDIT_REPORT.md` | Internal executive document |
| `backend/HOSTING_PICK_FAIR_PRICE.md` | Internal infrastructure cost notes |
| Any `.env` (non-example) | Live secrets — never included |
| `__pycache__/` | Python bytecode — generated at runtime |
| `node_modules/` | JS dependency installs — generated at runtime |
| `*.log` files | Runtime logs |
| Screenshots/uploads | Personal machine artifacts |
| `terminal/` files | PerplexTerminal / UACP terminal simulator |
| `backend/landing-dev/workspace-app.html` | Generated static app shell |

---

## Route Families (43 Routers)

| Router File | Route Prefix | Category |
|-------------|-------------|----------|
| `health.py` | `/health` | Core |
| `auth.py` | `/auth` | Auth |
| `workspace.py` | `/workspace` | Tenant |
| `admin.py` | `/admin` | Admin |
| `ai.py` | `/ai` | AI Exec |
| `exec_router.py` | `/v1/exec` | AI Exec SSE |
| `audit.py` | `/audit` | Compliance |
| `compliance.py` | `/compliance` | Compliance |
| `content_safety.py` | `/content-safety` | Compliance |
| `privacy.py` | `/privacy` | Compliance |
| `explainability.py` | `/explainability` | Compliance |
| `billing.py` | `/billing` | Billing |
| `subscriptions.py` | `/subscriptions` | Billing |
| `token_wallet.py` | `/wallet` | Billing |
| `budget.py` | `/budget` | Billing |
| `cost.py` | `/cost` | Billing |
| `monitoring_suite.py` | `/monitoring` | Monitoring |
| `platform_pulse.py` | `/platform/pulse` | Monitoring SSE |
| `security_suite.py` | `/security` | Security |
| `locker_monitoring.py` | `/locker/monitoring` | Security |
| `locker_security.py` | `/locker/security` | Security |
| `locker_users.py` | `/locker/users` | Security |
| `kill_switch.py` | `/kill-switch` | Security |
| `marketplace_v1.py` | `/marketplace` | Marketplace |
| `marketplace_automation.py` | `/marketplace/automation` | Marketplace |
| `pipelines.py` | `/pipelines` | Pipelines |
| `pipeline_interactive.py` | `/pipeline/interactive` | Pipelines |
| `demo_pipeline.py` | `/demo/pipeline` | Demo |
| `deployments.py` | `/deployments` | Deployments |
| `edge_canary.py` | `/edge/canary` | Edge |
| `routing.py` | `/routing` | Routing |
| `autonomous.py` | `/autonomous` | Autonomous |
| `internal_uacp.py` | `/internal/uacp` | Internal/UACP |
| `internal_operators.py` | `/internal/operators` | Internal/Operators |
| `source_of_truth_bridge.py` | `/source-of-truth` | Internal |
| `insights.py` | `/insights` | Analytics |
| `metrics.py` | `/metrics` | Analytics |
| `telemetry.py` | `/telemetry` | Analytics |
| `job.py` | `/jobs` | Jobs |
| `plugins.py` | `/plugins` | Plugins |
| `onboarding.py` | `/onboarding` | Onboarding |
| `referrals.py` | `/referrals` | Growth |
| `support_bot.py` | `/support` | Support |
| `search.py` | `/search` | Search |
| `upload.py` | `/upload` | Files |
| `transcribe.py` | `/transcribe` | Files |
| `extract.py` | `/extract` | Files |
| `export.py` | `/export` | Files |
| `suggestions.py` | `/suggestions` | UX |
| `stripe_connect.py` | `/stripe/connect` | Payments |
| `qstash_webhooks.py` | `/webhooks/qstash` | Webhooks |
| `resend_webhooks.py` | `/webhooks/resend` | Webhooks |

---

## DB Model Families

| Family | Models |
|--------|--------|
| Auth / Users | `User`, `Session`, `MFADevice`, `OAuthToken` |
| Workspace / Tenant | `Workspace`, `WorkspaceMember`, `WorkspaceSettings` |
| API Keys | `APIKey`, `APIKeyUsage` |
| AI Execution | `ExecLog`, `ExecRequest`, `ModelConfig` |
| Audit | `AuditLog`, `AuditHash` |
| Billing | `Subscription`, `Invoice`, `WalletTransaction`, `BudgetRule` |
| Marketplace | `MarketplaceListing`, `MarketplacePurchase` |
| Pipelines | `Pipeline`, `PipelineRun`, `PipelineStep` |
| Deployments | `Deployment`, `DeploymentZone` |
| Compliance | `ComplianceCheck`, `RegulationPolicy` |
| Security | `SecurityEvent`, `LockerEntry`, `KillSwitchState` |
| Monitoring | `HealthEvent`, `MetricSnapshot` |

---

## Migrations

- Alembic migration directory: `backend/db/migrations/`
- `alembic.ini` at `backend/alembic.ini`
- Run: `alembic upgrade head`

---

## Required Environment Variables

See `ENVIRONMENT.md` and `.env.example` for complete list. Core required vars:

```
DATABASE_URL
REDIS_URL
JWT_SECRET_KEY
JWT_ALGORITHM
STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET
OPENAI_API_KEY
ANTHROPIC_API_KEY
RESEND_API_KEY
MINIO_ENDPOINT / S3_BUCKET
LICENSE_PRIVATE_KEY
LICENSE_SERVER_URL
APP_ENV (production|development)
CORS_ORIGINS
```

---

## External Service Dependencies

| Service | Purpose | Required? |
|---------|---------|----------|
| PostgreSQL | Primary database | Required |
| Redis | Sessions, caching, job queue | Required |
| Stripe | Billing, subscriptions, webhooks | Required for billing |
| OpenAI | AI completions (default provider) | Required for AI exec |
| Anthropic | Claude completions | Optional |
| Resend | Transactional email | Required for auth emails |
| MinIO / S3 | File upload, storage | Required for upload/transcribe |
| Upstash QStash | Background job queue | Optional (async jobs) |
| Cloudflare Tunnel | Edge proxy (buyer deploy) | Recommended for BYOS |
| vLLM / Ollama | Private model runtime | Optional (sovereign mode) |

---

## Runtime Dependencies

- Python 3.11+
- FastAPI 0.110+
- SQLAlchemy 2.x
- Alembic
- Pydantic v2
- Uvicorn / Gunicorn
- httpx
- passlib / bcrypt
- python-jose (JWT)
- stripe
- resend
- boto3 (S3/MinIO)
- redis
- celery (optional async jobs)

---

## Test Categories

| Category | Path | What It Tests |
|----------|------|---------------|
| Auth | `tests/test_auth.py` | Login, register, JWT, MFA |
| Health | `tests/test_health.py` | `/health` route |
| AI Exec | `tests/test_exec.py` | `/v1/exec` SSE stream |
| Billing | `tests/test_billing.py` | Wallet, subscriptions |
| Compliance | `tests/test_compliance.py` | Regulation checks, PII |
| Audit | `tests/test_audit.py` | Log creation, hash verify |
| Workspace | `tests/test_workspace.py` | Tenant isolation |
| License | `tests/test_license.py` | Package guard, activation |
