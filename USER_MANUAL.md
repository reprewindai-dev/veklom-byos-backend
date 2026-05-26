# BYOS AI — User Manual

**Complete reference for every feature, endpoint, environment variable, and workflow.**

Version: 1.0 | Stack: Python 3.11 · FastAPI · PostgreSQL · Redis · Ollama · Celery · Stripe

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Environment Variables — Complete Reference](#2-environment-variables)
3. [Authentication](#3-authentication)
4. [LLM Inference Engine](#4-llm-inference-engine)
5. [Circuit Breaker & Groq Fallback](#5-circuit-breaker--groq-fallback)
6. [Conversation Memory](#6-conversation-memory)
7. [Cost Intelligence](#7-cost-intelligence)
8. [Security Suite](#8-security-suite)
9. [Privacy & GDPR](#9-privacy--gdpr)
10. [Content Safety](#10-content-safety)
11. [Compliance](#11-compliance)
12. [Monitoring & Observability](#12-monitoring--observability)
13. [Autonomous Intelligence (ML)](#13-autonomous-intelligence-ml)
14. [File Upload & Transcription](#14-file-upload--transcription)
15. [Admin Panel](#15-admin-panel)
16. [Billing & Subscriptions](#16-billing--subscriptions)
17. [Plugin System](#17-plugin-system)
18. [Multi-Tenancy & Isolation](#18-multi-tenancy--isolation)
19. [Database Schema Overview](#19-database-schema-overview)
20. [Industry-Specific Workflows](#20-industry-specific-workflows)
21. [Troubleshooting](#21-troubleshooting)

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         BYOS AI Backend                         │
│                                                                 │
│  ┌──────────┐    ┌─────────────────────────────────────────┐   │
│  │  Client  │───▶│  FastAPI  (apps/api/main.py)            │   │
│  └──────────┘    │  - ZeroTrustMiddleware                  │   │
│                  │  - MetricsMiddleware                     │   │
│                  │  - IntelligentRoutingMiddleware          │   │
│                  │  - BudgetCheckMiddleware                 │   │
│                  └─────────────┬───────────────────────────┘   │
│                                │                               │
│              ┌─────────────────┼──────────────────┐           │
│              ▼                 ▼                  ▼           │
│  ┌─────────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  /v1/exec       │  │  /api/v1/*   │  │  Public Routes   │  │
│  │  LLM Inference  │  │  30+ routers │  │  / (landing)     │  │
│  └────────┬────────┘  └──────┬───────┘  │  /status         │  │
│           │                  │          └──────────────────┘  │
│  ┌────────▼────────┐         │                               │
│  │ Circuit Breaker │         │                               │
│  │   (Redis)       │         │                               │
│  └──┬──────────┬───┘         │                               │
│     │          │             │                               │
│  CLOSED      OPEN            │                               │
│     ▼          ▼             ▼                               │
│  ┌──────┐  ┌──────┐  ┌───────────────┐  ┌────────────────┐  │
│  │Ollama│  │Groq  │  │  PostgreSQL   │  │  Redis         │  │
│  │local │  │cloud │  │  + RLS        │  │  - CB state    │  │
│  └──────┘  └──────┘  └───────────────┘  │  - Conv memory │  │
│                                          │  - Rate limits │  │
│                                          └────────────────┘  │
│                                                               │
│  ┌───────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │  Celery       │  │  MinIO / S3  │  │  Prometheus       │  │
│  │  Workers      │  │  File Store  │  │  Grafana / Loki   │  │
│  └───────────────┘  └──────────────┘  └───────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Key Design Principles

- **Zero data leaves your server by default** — all inference runs locally via Ollama
- **Multi-tenant isolation** — every DB query is filtered by `workspace_id` via Postgres RLS
- **Self-healing** — circuit breaker detects Ollama failures, routes to Groq, recovers silently
- **Audit-everything** — every AI call produces an HMAC-SHA256 immutable log record
- **Modular** — each router is independent; disable/swap without touching others

---

## 2. Environment Variables

### Required — App

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | — | JWT signing key. Generate: `openssl rand -hex 32` |
| `ENCRYPTION_KEY` | — | AES-256 field encryption key. Different from SECRET_KEY |
| `DATABASE_URL` | `postgresql://byos:...@postgres:5432/byos_ai` | Postgres connection string |
| `REDIS_URL` | `redis://:...@redis:6379/0` | Redis connection string |

### LLM Engine

| Variable | Default | Description |
|---|---|---|
| `LLM_BASE_URL` | `http://host.docker.internal:11434` | Ollama API URL (Docker→host) |
| `LLM_MODEL_DEFAULT` | `qwen2.5:3b` | Default model for all inference |
| `LLM_FALLBACK` | `groq` | `groq` = enable cloud fallback, `off` = hard fail |
| `LLM_TIMEOUT_SECONDS` | `60` | Max wait per Ollama call |
| `LLM_MAX_TOKENS` | `2048` | Default max output tokens |

### External AI Providers (Optional)

Used when routing strategy selects external providers. Ollama (local) is always primary.

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | OpenAI API key (sk-...) - enables GPT-4, Whisper |
| `OPENAI_MODEL_CHAT` | `gpt-4o-mini` | Default chat model for OpenAI provider |
| `OPENAI_MODEL_WHISPER` | `whisper-1` | Default STT model for OpenAI provider |
| `HUGGINGFACE_API_KEY` | — | HuggingFace API key (hf_...) - free tier available |
| `HUGGINGFACE_MODEL_CHAT` | `mistralai/Mistral-7B-Instruct-v0.1` | Default chat model for HF provider |
| `HUGGINGFACE_MODEL_EMBED` | `sentence-transformers/all-MiniLM-L6-v2` | Default embedding model for HF |

### Circuit Breaker

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | — | Free at console.groq.com. Required to enable fallback |
| `GROQ_MODEL` | `llama-3.1-8b-instant` | Model used when circuit is open |
| `CIRCUIT_BREAKER_FAILURE_THRESHOLD` | `3` | Failures before circuit opens |
| `CIRCUIT_BREAKER_COOLDOWN_SECONDS` | `60` | Seconds before probing Ollama again |

### Conversation Memory

| Variable | Default | Description |
|---|---|---|
| `MEMORY_TTL_SECONDS` | `86400` | 24 hours. How long conversations persist in Redis |
| `MEMORY_MAX_MESSAGES` | `20` | Max messages kept per conversation (oldest trimmed) |

### Security

| Variable | Default | Description |
|---|---|---|
| `ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | JWT access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `30` | Refresh token lifetime |
| `MAX_FAILED_LOGIN_ATTEMPTS` | `10` | Before account lockout |
| `ACCOUNT_LOCKOUT_MINUTES` | `30` | Lockout duration |

### Content Safety

| Variable | Default | Description |
|---|---|---|
| `CONTENT_FILTERING_ENABLED` | `true` | Enable/disable content scan pipeline |
| `AGE_VERIFICATION_REQUIRED` | `false` | Set `true` for adult platforms — forces age gate |

### Billing (Stripe)

| Variable | Default | Description |
|---|---|---|
| `STRIPE_SECRET_KEY` | — | From Stripe dashboard |
| `STRIPE_PUBLISHABLE_KEY` | — | From Stripe dashboard |
| `STRIPE_WEBHOOK_SECRET` | — | From Stripe webhook endpoint config |

### Infrastructure

| Variable | Default | Description |
|---|---|---|
| `S3_ENDPOINT_URL` | `http://minio:9000` | MinIO or AWS S3 endpoint |
| `S3_ACCESS_KEY_ID` | `minioadmin` | Storage access key |
| `S3_SECRET_ACCESS_KEY` | — | Storage secret |
| `S3_BUCKET_NAME` | `byos-ai` | Default bucket |
| `CELERY_BROKER_URL` | Redis URL | Celery task queue |
| `CORS_ORIGINS` | `[]` | Allowed frontend origins (JSON array of strings) |

### Observability

| Variable | Default | Description |
|---|---|---|
| `SENTRY_DSN` | — | Optional error tracking |
| `LOG_FORMAT` | `json` | `json` or `text` |
| `METRICS_ENABLED` | `true` | Expose `/metrics` Prometheus endpoint |
| `GRAFANA_USER` | `admin` | Grafana login (prod stack) |
| `GRAFANA_PASSWORD` | — | Grafana password (prod stack) |

---

## 3. Authentication

**Base path:** `/api/v1/auth`

All protected routes require one of:
- `Authorization: Bearer <jwt_access_token>` header, OR
- `X-API-Key: byos_<key>` header (for machine-to-machine / `/v1/exec`)

### Endpoints

#### Register (create workspace + first user)
```
POST /api/v1/auth/register
{
  "email": "you@example.com",
  "password": "strongpassword",
  "full_name": "Your Name",
  "workspace_name": "My Company"
}
→ { "access_token": "...", "refresh_token": "...", "workspace_id": "..." }
```

#### Login
```
POST /api/v1/auth/login
{
  "email": "you@example.com",
  "password": "strongpassword",
  "mfa_code": "123456"   ← optional, required if MFA enabled
}
→ { "access_token": "...", "refresh_token": "...", "expires_in": 1800 }
```

#### Refresh Token
```
POST /api/v1/auth/refresh
{ "refresh_token": "..." }
→ { "access_token": "..." }
```

#### Current User
```
GET /api/v1/auth/me
→ { "id": "...", "email": "...", "role": "admin", "workspace_id": "..." }
```

#### Enable MFA (TOTP)
```
POST /api/v1/auth/mfa/enable
→ { "secret": "...", "provisioning_uri": "otpauth://...", "qr_url": "..." }
# Scan QR with Google Authenticator or Authy
```

#### Verify MFA Setup
```
POST /api/v1/auth/mfa/verify
{ "code": "123456" }
```

#### Create API Key
```
POST /api/v1/auth/api-keys
{
  "name": "Production Key",
  "expires_days": 365   ← optional
}
→ { "key": "byos_xxxxxxxxxxxx", "id": "...", "name": "..." }
# IMPORTANT: key is shown only once. Copy it immediately.
```

#### List API Keys
```
GET /api/v1/auth/api-keys
→ [{ "id": "...", "name": "...", "created_at": "...", "expires_at": "..." }]
# Keys are never returned in full — only metadata
```

#### Revoke API Key
```
DELETE /api/v1/auth/api-keys/{key_id}
```

### User Roles

| Role | Can Do |
|---|---|
| `admin` | Everything including user management and workspace settings |
| `member` | Use AI endpoints, view own logs, manage own API keys |
| `viewer` | Read-only access to logs and dashboards |

---

## 4. LLM Inference Engine

**The primary endpoint.** Everything else in the platform supports this.

### POST /v1/exec

Execute a prompt with local Ollama inference, circuit breaker protection, and conversation memory.

**Request:**
```json
{
  "prompt": "Your prompt text here",
  "model": "qwen2.5:3b",          ← optional, overrides LLM_MODEL_DEFAULT
  "conversation_id": "chat-001",  ← optional, enables persistent memory
  "use_memory": true,             ← default true, set false to ignore history
  "max_tokens": 2048,             ← optional
  "temperature": 0.7              ← optional
}
```

**Response:**
```json
{
  "response": "The AI response text...",
  "provider": "ollama",           ← "ollama" or "groq"
  "model": "qwen2.5:3b",
  "conversation_id": "chat-001",
  "tenant_id": "workspace-uuid",
  "log_id": "exec_abc123...",     ← immutable audit log ID
  "prompt_tokens": 142,
  "completion_tokens": 287,
  "total_tokens": 429,
  "latency_ms": 1840
}
```

**Authentication:** `X-API-Key: byos_yourkey` or `Authorization: Bearer <token>`

**What happens internally:**
1. API key decoded → SHA-256 hash lookup → tenant resolved → RLS applied
2. Circuit breaker state checked
3. If `conversation_id` given: last 20 messages loaded from Redis, prepended to prompt
4. Inference called (Ollama if CLOSED, Groq if OPEN)
5. Response saved to Redis conversation buffer (TTL: 24h)
6. Execution logged to `execution_logs` table (tenant, model, provider, tokens, latency)
7. HMAC-SHA256 audit record written to `ai_audit_logs` table

### GET /status

Public endpoint — no authentication required. Shows live system state.

```json
{
  "status": "healthy",
  "db_ok": true,
  "redis_ok": true,
  "llm_ok": true,
  "llm_model": "qwen2.5:3b",
  "llm_models_available": ["qwen2.5:3b", "llama3.1:8b"],
  "groq_fallback_enabled": true,
  "circuit_breaker": {
    "state": "CLOSED",
    "failures": 0,
    "threshold": 3,
    "cooldown_seconds": 60
  },
  "uptime_seconds": 43200
}
```

---

## 5. Circuit Breaker & Groq Fallback

**File:** `core/llm/circuit_breaker.py`

### How It Works

The circuit breaker has three states stored in Redis:

| State | Meaning | Traffic Goes To |
|---|---|---|
| `CLOSED` | Ollama healthy | Local Ollama |
| `OPEN` | Ollama failing | Groq cloud |
| `HALF_OPEN` | Cooldown elapsed, testing | Single probe to Ollama |

### State Transitions

```
CLOSED → OPEN:      3 consecutive Ollama failures (configurable)
OPEN → HALF_OPEN:   After 60 seconds cooldown (configurable)
HALF_OPEN → CLOSED: Ollama probe succeeds
HALF_OPEN → OPEN:   Ollama probe fails (reset cooldown)
```

### Configuration

```env
CIRCUIT_BREAKER_FAILURE_THRESHOLD=3   # failures before opening
CIRCUIT_BREAKER_COOLDOWN_SECONDS=60   # seconds before probing
GROQ_API_KEY=gsk_...                  # required to enable fallback
GROQ_MODEL=llama-3.1-8b-instant       # which Groq model to use
```

### Checking Circuit State

```bash
GET /status
→ "circuit_breaker": { "state": "CLOSED", "failures": 0 }
```

### When GROQ_API_KEY Is Not Set

If `GROQ_API_KEY` is empty, `LLM_FALLBACK` is effectively `off`. When Ollama fails, the request returns a 503 error instead of falling back. Set the key for production reliability.

---

## 6. Conversation Memory

**File:** `core/memory/conversation.py`

Redis-backed per-tenant conversation history. Every `conversation_id` is namespaced by `workspace_id` — tenant A cannot access tenant B's conversations.

### How To Use

Pass `conversation_id` in any `/v1/exec` call. The backend:
1. Loads the last `MEMORY_MAX_MESSAGES` messages (default: 20) from Redis
2. Formats them as a conversation history and prepends to your prompt
3. Appends the new prompt + response to the Redis list
4. Resets the TTL to `MEMORY_TTL_SECONDS` (default: 24h)

### Memory Key Structure (Redis)
```
conv:{workspace_id}:{conversation_id}  → Redis LIST of JSON messages
```

### Memory Configuration

```env
MEMORY_TTL_SECONDS=86400    # 24 hours per conversation
MEMORY_MAX_MESSAGES=20      # rolling window, oldest trimmed first
```

### Disabling Memory Per-Request

```json
{ "prompt": "...", "use_memory": false }
```

### Clearing a Conversation

Memory expires automatically after TTL. To clear immediately, you can flush via Redis CLI:
```bash
docker exec -it byos_redis redis-cli DEL "conv:{workspace_id}:{conversation_id}"
```

---

## 7. Cost Intelligence

**Base path:** `/api/v1/cost`, `/api/v1/routing`, `/api/v1/budget`, `/api/v1/billing`

### 7.1 Cost Prediction

Know the cost before you commit to running an operation.

```
POST /api/v1/cost/predict
{
  "operation_type": "inference",
  "provider": "openai",
  "input_text": "Your text...",
  "model": "gpt-4"
}
→ {
  "predicted_cost": "0.002341",
  "confidence_lower": "0.002100",
  "confidence_upper": "0.002600",
  "accuracy_score": 0.94,
  "alternative_providers": [
    { "provider": "ollama", "cost": "0.000000", "savings_percent": 100 },
    { "provider": "groq",   "cost": "0.000180", "savings_percent": 92.3 }
  ]
}
```

### 7.2 Intelligent Provider Routing

Automatically choose the best provider based on your constraints.

**Routing Strategies:**
- `cost_optimized` — cheapest provider that meets quality floor
- `quality_optimized` — best quality within your budget
- `speed_optimized` — fastest response within constraints
- `hybrid` — balanced cost/quality/speed scoring

```
POST /api/v1/routing/test
{
  "operation_type": "inference",
  "constraints": {
    "strategy": "cost_optimized",
    "max_cost": "0.001",
    "min_quality": 0.80
  }
}
→ {
  "selected_provider": "ollama",
  "reasoning": "Selected ollama: lowest cost (free), meets quality threshold (0.85 >= 0.80).",
  "expected_cost": "0.000000",
  "expected_quality_score": 0.85,
  "expected_latency_ms": 1800,
  "alternatives_considered": [...]
}
```

### 7.3 Budget Management

Set monthly/weekly/daily budgets with automatic enforcement and alerts.

```
POST /api/v1/budget
{
  "budget_type": "monthly",
  "amount": "100.00",
  "alert_thresholds": [50, 80, 95]   ← % at which alerts fire
}

GET /api/v1/budget?budget_type=monthly
→ {
  "amount": "100.00",
  "current_spend": "34.21",
  "remaining": "65.79",
  "percent_used": 34.21,
  "forecast_exhaustion_date": "2026-02-20T00:00:00",
  "alert_level": "ok"   ← "ok", "warning", "critical", "exhausted"
}
```

When `alert_level` is `exhausted`, the `BudgetCheckMiddleware` blocks all new AI calls for that workspace and returns HTTP 402.

### 7.4 Cost Allocation & Client Billing

Tag costs to projects/clients and generate invoice-ready reports.

```
POST /api/v1/billing/allocate
{
  "operation_id": "audit-log-uuid",
  "allocation_method": "percentage",
  "allocation_rules": {
    "client_acme": 60,
    "client_globex": 40
  }
}

GET /api/v1/billing/report?start_date=2026-01-01&end_date=2026-01-31
→ {
  "summary": {
    "total_operations": 1240,
    "total_base_cost": "87.43",
    "total_markup": "17.49",
    "total_final_cost": "104.92"
  },
  "by_project": { "client_acme": "62.95", "client_globex": "41.97" }
}
```

**Precision:** All cost calculations use `Decimal(10,6)` — precise to 6 decimal places, no rounding errors.

### 7.5 Kill Switch

Emergency halt — blocks all AI calls for a workspace instantly.

```
POST /api/v1/cost/kill-switch
{ "reason": "Runaway usage detected" }

DELETE /api/v1/cost/kill-switch   ← re-enable
```

---

## 8. Security Suite

**Base path:** `/api/v1/security`

### 8.1 Zero-Trust Middleware

Every single request (except `/`, `/status`, `/health`) passes through `ZeroTrustMiddleware`:
1. Token/API key extracted and validated
2. Workspace resolved and attached to request context
3. User roles and permissions checked against the route
4. Failed checks return 401/403 — never a partial result

### 8.2 Security Events

Log and track threat events with AI-confidence scoring.

```
POST /api/v1/security/events
{
  "event_type": "suspicious_login",
  "threat_type": "brute_force",
  "security_level": "HIGH",
  "description": "5 failed login attempts from same IP",
  "ip_address": "1.2.3.4",
  "ai_confidence": 0.92,
  "ai_recommendations": { "action": "block_ip", "duration": "1h" }
}

GET /api/v1/security/events?threat_type=brute_force&status=open
→ [list of security events with IDs for resolution]

POST /api/v1/security/events/{event_id}/resolve
{ "resolution_notes": "Blocked IP at firewall" }
```

### 8.3 Security Score Dashboard

```
GET /api/v1/security/stats
→ {
  "total": 142,
  "open": 3,
  "resolved": 139,
  "critical": 0,
  "last_24h": 2,
  "by_type": { "brute_force": 12, "suspicious_login": 8 },
  "security_score": 94   ← 0-100, higher is better
}
```

### 8.4 Threat Types

Supported threat types: `brute_force`, `sql_injection`, `xss`, `unauthorized_access`, `data_exfiltration`, `suspicious_login`, `rate_limit_abuse`, `anomaly`

### 8.5 Encryption

- **AES-256-GCM** for sensitive fields at rest (API keys stored as hash, PII fields encrypted)
- **File:** `core/security/encryption.py`
- **Usage:** `from core.security.encryption import encrypt_field, decrypt_field`

### 8.6 Rate Limiting

Redis sliding window rate limiting per workspace. Configurable windows:
- Per-minute limit
- Per-hour limit
- Per-day limit

Set via routing policy or workspace settings. Exceeded limits return HTTP 429.

---

## 9. Privacy & GDPR

**Base path:** `/api/v1/privacy`

### 9.1 PII Detection

Automatically detect personally identifiable information in any text.

```
POST /api/v1/privacy/detect-pii
{ "text": "Contact John Smith at john@example.com or 555-123-4567. SSN: 123-45-6789." }
→ {
  "has_pii": true,
  "pii_types": ["email", "phone", "ssn", "name"],
  "count": 4
}
```

**Detected types:** email, phone, SSN, credit card, IP address, full name, date of birth

### 9.2 PII Masking

```
POST /api/v1/privacy/mask-pii
{
  "text": "John Smith: john@example.com, card 4111-1111-1111-1111",
  "strategy": "redact"   ← "redact", "hash", "replace", "partial"
}
→ {
  "masked_text": "[NAME] [REDACTED]: [EMAIL], card [CREDIT_CARD]",
  "pii_found": ["name", "email", "credit_card"]
}
```

### 9.3 GDPR Right to Access (Data Export)

```
GET /api/v1/privacy/export
→ {
  "user": { "id": "...", "email": "...", "created_at": "..." },
  "executions": [...],   ← all AI calls
  "audit_logs": [...],
  "api_keys": [...metadata only, no secrets...],
  "export_generated_at": "2026-01-15T14:30:00Z"
}
```

### 9.4 GDPR Right to Deletion

```
DELETE /api/v1/privacy/delete-account
{ "confirmation": "DELETE MY ACCOUNT" }
```

Deletes: user record, all executions, all conversation memory, all audit logs for that user. Irreversible.

### 9.5 Data Retention Policies

```
POST /api/v1/privacy/retention-policy
{
  "data_type": "execution_logs",
  "retention_days": 90
}
```

Celery beat job runs daily to purge records beyond retention window.

---

## 10. Content Safety

**Base path:** `/api/v1/content-safety`

Designed specifically for adult platforms, creator networks, and any platform handling user-generated content.

### 10.1 Content Scanning

```
POST /api/v1/content-safety/scan
{
  "content_hash": "sha256:...",   ← hash of the file/content
  "content_type": "image/jpeg",
  "filename": "upload.jpg",
  "tags": ["adult", "explicit"]
}
→ {
  "allowed": true,
  "category": "adult",
  "confidence": 0.96,
  "flags": ["nsfw"],
  "action": "allow",
  "requires_age_verification": true,
  "message": null
}
```

**Categories:** `safe`, `adult`, `explicit`, `violent`, `illegal` (CSAM = immediate hard block, no exceptions)

**Actions:** `allow`, `require_age_verification`, `flag_for_review`, `block`

### 10.2 Age Verification

```
POST /api/v1/content-safety/age-verify
{ "verification_method": "self_attestation" }
→ {
  "verification_token": "avt_...",
  "expires_at": "2027-01-15T00:00:00Z",
  "status": "verified"
}

GET /api/v1/content-safety/age-verify/status
→ {
  "status": "verified",   ← "unverified", "pending", "verified", "expired"
  "verified_at": "2026-01-15T...",
  "expires_at": "2027-01-15T...",
  "verification_method": "self_attestation"
}
```

**Verification methods:** `self_attestation` (checkbox), `document` (ID upload — hook in your own verification provider)

### 10.3 Platform Configuration

Set `AGE_VERIFICATION_REQUIRED=true` in `.env` to force all users to complete age verification before any content access. Without it, age gate is opt-in per content item.

### 10.4 CSAM Zero-Tolerance Policy

The backend includes a hard-coded zero-tolerance block for CSAM. Any content matching CSAM patterns:
- Returns `allowed: false`, `action: "block"`, `category: "illegal"` immediately
- Logs the attempt with full metadata
- Cannot be overridden by any configuration

---

## 11. Compliance

**Base path:** `/api/v1/compliance`

### 11.1 Immutable Audit Logs

Every AI call writes an HMAC-SHA256 audit record. These cannot be modified after creation.

```
GET /api/v1/audit?start_date=2026-01-01&end_date=2026-01-31&limit=100
→ [{
  "id": "audit_...",
  "workspace_id": "...",
  "operation_type": "inference",
  "provider": "ollama",
  "model": "qwen2.5:3b",
  "input_tokens": 142,
  "output_tokens": 287,
  "cost": "0.000000",
  "latency_ms": 1840,
  "hmac_hash": "sha256:abc123...",   ← cryptographic proof
  "created_at": "2026-01-15T14:30:00Z"
}]
```

### 11.2 Compliance Reports

Generate on-demand compliance reports for GDPR, CCPA, SOC2.

```
POST /api/v1/compliance/report
{
  "regulation": "gdpr",   ← "gdpr", "ccpa", "soc2"
  "start_date": "2026-01-01",
  "end_date": "2026-01-31"
}
→ {
  "regulation": "GDPR",
  "period": "2026-01-01 to 2026-01-31",
  "compliance_score": 97,
  "findings": [...],
  "recommendations": [...],
  "generated_at": "2026-01-31T23:59:00Z"
}
```

### 11.3 AI Explainability

Understand WHY the system made a routing or cost decision.

```
GET /api/v1/explain/routing/{decision_id}
→ {
  "decision": "ollama selected",
  "reasoning": "ollama offers lowest cost ($0.00) and meets quality threshold (0.85 >= 0.80). Saves 100% vs openai.",
  "confidence": 0.94,
  "factors": [
    { "factor": "cost", "weight": 0.6, "score": 1.0 },
    { "factor": "quality", "weight": 0.3, "score": 0.85 }
  ]
}

GET /api/v1/explain/cost/{prediction_id}
→ {
  "predicted_cost": "0.000234",
  "actual_cost": "0.000218",
  "error_percent": 6.8,
  "reasoning": "Based on 847 historical samples for qwen2.5:3b inference...",
  "confidence": 0.91
}
```

### 11.4 AI Quality Scoring

Every response is scored for quality dimensions:

```
GET /api/v1/audit/{log_id}/quality
→ {
  "relevance": 0.92,
  "accuracy": 0.88,
  "coherence": 0.95,
  "completeness": 0.81,
  "overall": 0.89
}
```

---

## 12. Monitoring & Observability

**Base path:** `/api/v1/monitoring`

### 12.1 System Health

```
GET /api/v1/monitoring/health
→ {
  "status": "healthy",
  "score": 98,
  "uptime_seconds": 86400,
  "components": {
    "database": { "status": "healthy", "response_time_ms": 2.1 },
    "redis":    { "status": "healthy", "response_time_ms": 0.8 },
    "minio":    { "status": "healthy", "response_time_ms": 4.2 },
    "ollama":   { "status": "healthy", "response_time_ms": 45.0 }
  }
}
```

### 12.2 Metrics

```
GET /api/v1/monitoring/metrics
→ [{
  "name": "api.requests.total",
  "value": 14823,
  "unit": "count",
  "timestamp": "2026-01-15T14:30:00Z"
}, ...]
```

Prometheus endpoint (for Grafana scraping): `GET /metrics`

### 12.3 Alerts

```
GET /api/v1/monitoring/alerts
→ [{
  "id": "...",
  "severity": "WARNING",
  "message": "Budget 80% consumed (monthly)",
  "created_at": "...",
  "resolved": false
}]

POST /api/v1/monitoring/alerts/{alert_id}/resolve
```

### 12.4 Request Insights

```
GET /api/v1/insights
→ {
  "total_requests_today": 1240,
  "avg_latency_ms": 1640,
  "error_rate_percent": 0.3,
  "top_models": [{ "model": "qwen2.5:3b", "calls": 1180 }],
  "provider_split": { "ollama": 0.94, "groq": 0.06 }
}
```

---

## 13. Autonomous Intelligence (ML)

**Base path:** `/api/v1/autonomous`

These modules learn from your actual usage patterns and improve predictions over time.

### 13.1 ML Cost Predictor

```
POST /api/v1/autonomous/cost/predict
{
  "operation_type": "inference",
  "provider": "ollama",
  "input_tokens": 142,
  "estimated_output_tokens": 300,
  "model": "qwen2.5:3b"
}
→ {
  "predicted_cost": "0.000000",
  "confidence_lower": "0.000000",
  "confidence_upper": "0.000001",
  "is_ml_prediction": true,
  "model_version": "v1.3"
}
```

### 13.2 Train ML Models

Train the cost predictor, routing optimizer, or quality predictor on your historical data.

```
POST /api/v1/autonomous/train
{ "min_samples": 100 }
→ {
  "cost_predictor": { "trained": true, "samples_used": 847 },
  "routing_optimizer": { "trained": true, "samples_used": 847 },
  "quality_predictor": { "trained": true, "samples_used": 847 }
}
```

### 13.3 Quality Optimization

```
POST /api/v1/autonomous/quality/optimize
{
  "operation_type": "inference",
  "target_quality": 0.90,
  "max_cost": "0.001"
}
→ {
  "recommended_provider": "ollama",
  "recommended_model": "llama3.1:8b",
  "expected_quality": 0.91,
  "expected_cost": "0.000000"
}
```

### 13.4 Feature Flags

```
GET /api/v1/autonomous/feature-flags
→ { "ml_routing": true, "quality_scoring": true, "auto_training": false }

POST /api/v1/autonomous/feature-flags
{ "ml_routing": false }   ← disable ML routing for this workspace
```

---

## 14. File Upload & Transcription

**Base paths:** `/api/v1/upload`, `/api/v1/transcribe`, `/api/v1/extract`, `/api/v1/jobs`

### 14.1 Upload a File

```
POST /api/v1/upload
Content-Type: multipart/form-data
file: <binary>
→ { "asset_id": "...", "filename": "...", "size_bytes": 1048576, "url": "..." }
```

Files are stored in MinIO (S3-compatible). Each file is tenant-isolated — you can only access your own workspace's files.

### 14.2 Transcribe Audio/Video

```
POST /api/v1/transcribe
{
  "asset_id": "...",
  "provider": "local_whisper"   ← default: local_whisper (self-hosted)
}
→ { "job_id": "..." }   ← transcription runs async via Celery

GET /api/v1/jobs/{job_id}
→ {
  "id": "...",
  "status": "completed",   ← "pending", "running", "completed", "failed"
  "result": { "text": "Transcribed text here..." },
  "created_at": "...",
  "completed_at": "..."
}
```

### 14.3 Extract Structured Data

Use AI to extract structured information from text.

```
POST /api/v1/extract
{
  "source_type": "text",
  "content": "Invoice #INV-2026-001. Client: Acme Corp. Amount: $4,500. Due: Feb 1.",
  "extraction_schema": {
    "invoice_number": "string",
    "client": "string",
    "amount": "number",
    "due_date": "string"
  },
  "provider": "local"   ← uses local Ollama
}
→ {
  "invoice_number": "INV-2026-001",
  "client": "Acme Corp",
  "amount": 4500,
  "due_date": "2026-02-01"
}
```

---

## 15. Admin Panel

**Base path:** `/api/v1/admin` — requires `admin` role

### Workspace Management

```
GET /api/v1/admin/workspaces          ← list all workspaces
GET /api/v1/admin/workspaces/{id}     ← workspace detail
POST /api/v1/admin/workspaces/{id}/suspend   ← suspend workspace
DELETE /api/v1/admin/workspaces/{id}  ← delete workspace + all data
```

### User Management

```
GET /api/v1/admin/users
→ [{ "id": "...", "email": "...", "role": "...", "workspace_id": "...", "status": "active" }]

PUT /api/v1/admin/users/{id}/role
{ "role": "viewer" }

POST /api/v1/admin/users/{id}/deactivate
```

### System-Wide Audit

```
GET /api/v1/admin/audit?workspace_id=...&limit=500
```

---

## 16. Billing & Subscriptions

**Base path:** `/api/v1/subscriptions`

### Plans

| Tier Key | Name | Monthly Price | Calls/mo |
|---|---|---|---|
| `starter` | Starter | $79 | 50,000 |
| `agency` | Agency | $249 | 500,000 |
| `enterprise` | Enterprise | $999 | Unlimited |

### Start Checkout (Stripe)

```
POST /api/v1/subscriptions/checkout
{ "plan": "agency", "success_url": "https://app.yourdomain.com/billing/success" }
→ { "checkout_url": "https://checkout.stripe.com/pay/cs_live_..." }
# Redirect user to checkout_url
```

### Customer Portal (manage/cancel)

```
POST /api/v1/subscriptions/portal
{ "return_url": "https://app.yourdomain.com/billing" }
→ { "portal_url": "https://billing.stripe.com/session/..." }
```

### Check Subscription Status

```
GET /api/v1/subscriptions/current
→ {
  "plan": "agency",
  "status": "active",
  "current_period_end": "2026-02-01T00:00:00Z",
  "features": { "api_calls_per_month": 500000, "intelligent_routing": true }
}
```

### Stripe Webhook

Configure your Stripe webhook endpoint to: `POST https://yourdomain.com/api/v1/subscriptions/webhook`

Events handled: `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_succeeded`, `invoice.payment_failed`

---

## 17. Plugin System

**Base path:** `/api/v1/plugins`

Extend the backend with custom AI providers, processing steps, or integrations — without touching core code.

### List Available Plugins

```
GET /api/v1/plugins
→ [{ "id": "...", "name": "My Custom Provider", "enabled": true }]
```

### Enable/Disable Plugin

```
POST /api/v1/plugins/{plugin_id}/enable
POST /api/v1/plugins/{plugin_id}/disable
```

### Creating a Plugin

1. Create `apps/plugins/my_plugin/` folder
2. Add `plugin.py` with a class that implements `BasePlugin`
3. The plugin system auto-discovers and loads it on startup
4. Each workspace can independently enable/disable plugins

See `docs/PLUGIN_SYSTEM.md` for the full plugin development guide.

---

## 18. Multi-Tenancy & Isolation

Every piece of data in the system is tenant-isolated at the database level using PostgreSQL Row-Level Security (RLS).

### How It Works

When a request arrives:
1. API key or JWT is validated
2. `workspace_id` is extracted and set as a Postgres session variable: `SET app.workspace_id = '...'`
3. RLS policies on every table automatically filter queries to only return rows where `workspace_id` matches
4. Even if a bug in application code queries the wrong table, RLS prevents cross-tenant data leakage

### Isolation Guarantees

- One tenant **cannot** read another tenant's executions, conversations, files, or API keys
- One tenant **cannot** exhaust another tenant's budget
- One tenant **cannot** access another tenant's workspace settings
- Admin users can see all workspaces (bypass RLS with `require_admin` dependency)

### Workspace vs User

- A **Workspace** is the top-level tenant unit (a company or account)
- **Users** belong to exactly one workspace
- **API Keys** belong to exactly one workspace
- All data is isolated at the workspace level

---

## 19. Database Schema Overview

```
Core Tables (Migration 001)
├── workspaces          — tenant root: id, name, slug, plan, settings
├── users               — id, email, password_hash, role, workspace_id, mfa_*
├── user_sessions       — refresh tokens, expiry, device info
├── api_keys            — id, key_hash, workspace_id, scopes, expires_at
├── jobs                — async task tracking: id, type, status, result
├── subscriptions       — stripe subscription state per workspace

Security Suite (Migration 002)
├── security_events     — threat events, AI confidence, resolution
├── alerts              — system alerts with severity levels
├── system_metrics      — time-series metric snapshots

LLM Engine (Migration 003)
├── execution_logs      — every /v1/exec call: tenant, model, provider, tokens, latency
├── ai_audit_logs       — immutable HMAC-SHA256 records of every AI operation
├── cost_predictions    — predicted vs actual cost tracking
├── routing_decisions   — provider routing decisions with reasoning
├── cost_allocations    — per-client/project cost tagging
├── budgets             — budget limits with spend tracking
├── routing_policies    — per-workspace routing strategy config
├── content_filter_logs — content scan results
├── age_verifications   — age verification records per user
├── abuse_logs          — rate limit and abuse detection events
├── incident_logs       — incident tracking and resolution
```

---

## 20. Industry-Specific Workflows

### Adult Content Platform Setup

1. Set `AGE_VERIFICATION_REQUIRED=true` in `.env`
2. All users must complete age verification via `POST /api/v1/content-safety/age-verify` before accessing content
3. Run content scans via `POST /api/v1/content-safety/scan` for every user-uploaded asset
4. Any content returning `category: "illegal"` is hard-blocked with no override
5. Use `conversation_id` for AI-assisted content moderation conversations
6. Pull GDPR reports monthly to satisfy data subject rights obligations

**Key endpoints:**
- `POST /api/v1/content-safety/age-verify`
- `POST /api/v1/content-safety/scan`
- `GET /api/v1/content-safety/age-verify/status`

### Agency / White-Label Setup

1. Each client = one workspace (register via `POST /api/v1/auth/register`)
2. Each workspace gets its own API keys, rate limits, and budget
3. Enable `intelligent_routing` on Agency plan — routes to cheapest provider automatically
4. Tag all costs via `POST /api/v1/billing/allocate` with `client_id`
5. Generate monthly billing reports via `GET /api/v1/billing/report`
6. Mark up AI costs 30-40% before sending to client invoices

**Key endpoints:**
- `POST /api/v1/budget` — per-client budget
- `POST /api/v1/billing/allocate` — cost tagging
- `GET /api/v1/billing/report` — invoice-ready export

### Legal / LegalTech Setup

1. Use default config — no data leaves server
2. Conversation memory via `conversation_id` maintains context across a legal matter
3. Use `GET /api/v1/privacy/export` for data subject access requests
4. Generate SOC2 compliance reports quarterly
5. Use `/api/v1/extract` for contract clause extraction with structured output
6. Audit logs prove exactly what AI ran, when, at what cost — satisfies privilege documentation

**Key endpoints:**
- `POST /v1/exec` with `conversation_id` for matter-specific context
- `POST /api/v1/extract` for contract analysis
- `POST /api/v1/compliance/report` with `"regulation": "soc2"`

### Healthcare / Telehealth Setup

1. Enable PII masking in all audit logs (automatic via `core/privacy/pii_detection.py`)
2. Set `DATA_RETENTION_DAYS=90` per HIPAA retention guidance
3. Use `POST /api/v1/privacy/detect-pii` before logging any input text
4. All inference runs locally — zero PHI to external servers
5. Use `POST /api/v1/privacy/delete` for patient data deletion requests

---

## 21. Troubleshooting

### Ollama Not Responding

**Symptom:** `/status` shows `llm_ok: false`

1. Check Ollama is running: open a new terminal, run `ollama list`
2. If not running: start Ollama from the system tray or run `ollama serve`
3. Verify Docker can reach host: `docker exec -it byos_api curl http://host.docker.internal:11434/api/tags`
4. If circuit is OPEN but Ollama is back, wait 60s for auto-recovery or restart API: `docker compose -f docker-compose.dev.yml restart api`

### Model Not Found

**Symptom:** `{"error": "model not found"}`

```powershell
ollama pull qwen2.5:3b
# Then restart API
docker compose -f docker-compose.dev.yml restart api
```

### Migrations Failed

```powershell
docker exec -it byos_api alembic upgrade head
docker exec -it byos_api alembic current   ← check current version
docker exec -it byos_api alembic history   ← see migration chain
```

### Circuit Breaker Stuck Open

If Ollama is healthy but circuit is still OPEN:

```powershell
# Clear circuit breaker state in Redis
docker exec -it byos_redis redis-cli DEL "circuit_breaker:ollama"
# Circuit will re-initialize as CLOSED on next request
```

### API Key Not Working

1. Check the key starts with `byos_`
2. Check it hasn't expired: `GET /api/v1/auth/api-keys` (check `expires_at`)
3. Check `is_active` — key may have been revoked
4. Re-generate: `POST /api/v1/auth/api-keys`

### Database Connection Error

```powershell
# Check Postgres is running
docker compose -f docker-compose.dev.yml ps postgres

# Check connection from API container
docker exec -it byos_api python -c "from db.session import get_db; print('DB OK')"

# Reset Postgres
docker compose -f docker-compose.dev.yml restart postgres
```

### Budget Blocking Requests (HTTP 402)

Budget exhausted for the workspace. Options:
1. Increase budget: `POST /api/v1/budget` with higher amount
2. Reset spend tracking for testing: contact admin
3. Check current usage: `GET /api/v1/budget?budget_type=monthly`

### Conversation Memory Not Working

1. Check Redis is running: `GET /status` → `redis_ok: true`
2. Verify you're passing the same `conversation_id` string on each call
3. Memory expires after `MEMORY_TTL_SECONDS` (default 24h) — start new `conversation_id`
4. Check `use_memory` is not set to `false` in your request

---

*Last updated: 2026-04-02 | BYOS AI v1.0*
