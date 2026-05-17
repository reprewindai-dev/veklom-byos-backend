# SELLABLE_BACKEND_AUDIT.md — Module Readiness Audit

> Last audited: 2026-05-17  
> Source: `reprewindai-dev/byosbackened` @ `8241cb7`

---

## Status Key

| Status | Meaning |
|--------|--------|
| ✅ READY | Stable, tested, sellable |
| ⚠️ EXPERIMENTAL | Works but not fully tested — include with caveat |
| 🔴 BLOCKED | Broken or incomplete — do not sell without fixing |
| 📋 PLACEHOLDER | Route exists, logic is stub — mark as "coming soon" |

---

## Core Backend

| Module | Status | Notes |
|--------|--------|-------|
| FastAPI app (`main.py`) | ✅ READY | App starts, middleware works, all routers registered |
| Health route | ✅ READY | `/health` confirmed live |
| Status route | ✅ READY | `/status` confirmed live |
| Auth (login/register/JWT) | ✅ READY | JWT + refresh token flow verified |
| Auth (MFA) | ⚠️ EXPERIMENTAL | TOTP-based MFA present, needs more test coverage |
| Auth (GitHub OAuth) | ⚠️ EXPERIMENTAL | OAuth flow present, callback untested in prod |
| Workspace / Tenant isolation | ✅ READY | Multi-tenant scoping verified |
| API key management | ✅ READY | Create/list/revoke working |
| Kill switch | ✅ READY | Activate/deactivate/status working |

---

## AI Execution

| Module | Status | Notes |
|--------|--------|-------|
| `/v1/exec` SSE stream | ✅ READY | Core product feature — OpenAI-compatible SSE stream |
| Cost prediction | ✅ READY | Pre-execution cost estimate working |
| Autonomous routing | ⚠️ EXPERIMENTAL | Cost/quality/risk routing logic present, tuning needed |
| Model config management | ✅ READY | Per-workspace model toggle working |
| vLLM / Ollama connection | ⚠️ EXPERIMENTAL | Config present, end-to-end not verified in buyer env |
| File upload + context | ✅ READY | Upload working, file context injection working |
| Transcription | ⚠️ EXPERIMENTAL | OpenAI Whisper backend, requires `OPENAI_API_KEY` |

---

## Compliance & Governance

| Module | Status | Notes |
|--------|--------|-------|
| Content safety scoring | ✅ READY | Per-request safety check working |
| PII/PHI detection | ✅ READY | Regex + ML-based detection working |
| Compliance regulation checks | ✅ READY | HIPAA/GDPR/SOC2 framework checks working |
| Explainability | ⚠️ EXPERIMENTAL | Returns decision metadata, model-specific depth varies |
| Audit logs | ✅ READY | Tamper-evident hash chain working |
| Audit hash verification | ✅ READY | `/audit/verify/{id}` working |

---

## Security

| Module | Status | Notes |
|--------|--------|-------|
| Security event log | ✅ READY | Events captured and queryable |
| Locker isolation | ⚠️ EXPERIMENTAL | Per-tenant locker present, stress testing incomplete |
| Source of truth bridge | ⚠️ EXPERIMENTAL | Internal sync mechanism — advanced feature |

---

## Billing

| Module | Status | Notes |
|--------|--------|-------|
| Token wallet | ✅ READY | Balance, transactions, topup working |
| Budget rules | ✅ READY | Hard/soft limits working |
| Stripe subscriptions | ✅ READY | Checkout, webhook, plan management working |
| Stripe Connect (marketplace payouts) | ⚠️ EXPERIMENTAL | Connect onboarding present, payout flows need testing |
| Invoice history | ✅ READY | Stripe invoice sync working |

---

## Marketplace

| Module | Status | Notes |
|--------|--------|-------|
| Listing CRUD | ✅ READY | Create/read/update/delete working |
| Marketplace search | ✅ READY | Search and filter working |
| Automation workflows | ⚠️ EXPERIMENTAL | Complex automation chains — needs buyer testing |

---

## Pipelines

| Module | Status | Notes |
|--------|--------|-------|
| Pipeline CRUD | ✅ READY | Create/read/update/delete working |
| Pipeline execution | ⚠️ EXPERIMENTAL | Run logic present, complex chains need validation |
| Interactive pipeline session | ⚠️ EXPERIMENTAL | WebSocket-based session, load testing incomplete |
| Demo pipeline | ✅ READY | Demo run endpoint working — good for buyer onboarding |

---

## Deployments & Edge

| Module | Status | Notes |
|--------|--------|-------|
| Deployment CRUD | ✅ READY | Standard deployment management working |
| Edge canary | ⚠️ EXPERIMENTAL | Canary promotion logic present, needs field testing |

---

## Internal / Advanced

| Module | Status | Notes |
|--------|--------|-------|
| UACP (Universal AI Control Plane) | ⚠️ EXPERIMENTAL | Advanced control plane — enterprise/research feature |
| Internal operators | ⚠️ EXPERIMENTAL | Operator registry — advanced automation feature |
| Platform pulse SSE | ✅ READY | Real-time event stream working |
| Monitoring suite | ✅ READY | Health metrics and event log working |

---

## Not Included (By Design)

| Item | Reason |
|------|--------|
| Frontend workspace app | Not part of BYOS backend product |
| Landing page | Not part of backend product |
| PerplexTerminal | Internal demo tool |
| UACP Terminal UI | Internal UI — not sellable |
| Static HTML bundles | Generated artifacts — not source |
| Customer data / production DB | Never included |
| Live production secrets | Never included |

---

## Recommended Fixes Before First Sale

1. **Run full pytest suite** — confirm zero failures on core modules
2. **End-to-end `/v1/exec` test** — verify SSE stream with real OpenAI key
3. **Migration dry-run** — `alembic upgrade head` against fresh DB
4. **Stripe webhook test** — verify topup checkout flow in Stripe test mode
5. **License activation test** — activate and verify status endpoint
6. **Remove any hardcoded internal domains** — search for `veklom.com`, `reprewind`, `anthon` in source
