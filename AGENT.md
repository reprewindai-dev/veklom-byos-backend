# AGENT.md — Veklom Infrastructure Alignment Guide

> **Last Updated:** 2026-06-21
> **Authored by:** Comet (AI Agent, Perplexity)
> **Protocol Bible:** https://x402.org
> **Owner:** reprewindai-dev

This document is the canonical alignment reference for ALL agents, developers, and AI systems working on the Veklom ecosystem. Read this before touching anything.

---

## 1. What Is Veklom?

Veklom is a **sovereign AI infrastructure platform** — a Bring-Your-Own-Server (BYOS) governed AI backend. It provides:
- Policy-governed AI workload execution
- Multi-tenant agent isolation
- x402 micropayment-gated API access
- Decentralized identity (veklom-id)
- Compliance frameworks (SOC-2, GDPR, HIPAA, PCI-DSS)

**Core domain:** https://veklom.com
**API root:** https://api.veklom.com

---

## 2. Repository Map

| Repo | Purpose | Live URL | Status |
|------|---------|----------|--------|
| `veklom-byos-backend` | PRIMARY — FastAPI backend, x402 router, BYOS engine | https://api.veklom.com | LIVE |
| `veklom-control-plane` | Sovereign control plane frontend (TypeScript/Next.js) | https://control.veklom.com | LIVE |
| `veklom-id` | Decentralized identity service (Vercel) | https://id.veklom.com | LIVE (Vercel) |
| `cAPI` (Covenant Protocol) | Governed connection layer v2.0.0 | https://capi.veklom.com | LIVE |
| `gnomledger` | Project Genome Ledger — FastAPI evidence chain | https://pgl.veklom.com | LIVE |
| `veklom-gpc` | Governed Plan Compiler — AI workflow intent engine | https://gpc.veklom.com | LIVE |
| `cappo-backend` | Cappo backend service | https://cappo.veklom.com | LIVE |
| `seked-spec` | SEKED measurement language canonical spec | (public decoder) | LIVE |

---

## 3. x402 Protocol Alignment

**Bible:** https://x402.org

### What x402 Is
x402 is a payment-required HTTP protocol. When a client hits a gated endpoint, the server returns HTTP `402 Payment Required` with a JSON body describing the payment terms. The client pays on-chain (Base/ETH), then retries with a payment proof header.

### Veklom x402 Implementation

**Router location:** `backend/apps/api/routers/x402.py`

**Key endpoints (live at https://api.veklom.com):**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/x402/payment-required` | GET | Returns 402 with payment terms |
| `/api/v1/x402/verify` | POST | Verifies on-chain payment proof |
| `/api/v1/x402/protected` | GET | x402-gated resource example |
| `/api/v1/pricing` | GET | Returns current pricing tiers |
| `/api/v1/health` | GET | Health check |

**x402 Response Headers agents must handle:**
```
X-Payment-Required: true
X-Payment-Amount: <amount in USDC>
X-Payment-Network: base
X-Payment-Address: <wallet address>
X-Payment-Token: <ERC20 contract>
```

**Payment flow:**
1. Agent hits endpoint → receives `402` + payment descriptor JSON
2. Agent submits payment on Base network
3. Agent retries request with `X-Payment-Proof: <txhash>` header
4. Server verifies on-chain → grants access

---

## 4. Infrastructure — Coolify Deployment

**Coolify host:** http://5.78.135.11:8000
**Server:** localhost (Hetzner VPS)
**Project:** veklom > production

### Current Service Status (as of 2026-06-21)

#### Applications
| Name | Domain | Status | Notes |
|------|--------|--------|-------|
| `veklom-byos-backend` | veklom.com, app.veklom.com, api.veklom.com | Running (healthy) | Primary backend + frontend monorepo |
| `veklom-control-plane` | control.veklom.com | Running (healthy) | Control plane frontend |
| `cAPI` | capi.veklom.com | Running (unknown*) | Covenant Protocol v2.0.0 — LIVE confirmed |
| `cappo-backend` | cappo.veklom.com | Running (unknown*) | Running fine, no Docker healthcheck configured |
| `gnomledger` | pgl.veklom.com | Running (unknown*) | FastAPI — LIVE confirmed via /docs |
| `veklom-gpc` | gpc.veklom.com | Running (unknown*) | GPC UI — LIVE confirmed, Signal Feed live |
| `co2router-site` | co2router.com | Running (healthy) | CO2 Router public site |
| `ecobe-engine` | (internal) | Running (healthy) | CO2 Router engine |
| `ecobe-mvp` | api.co2router.com, x402.co2router.com, mcp.co2router.com | Running (healthy) | ECOBE control plane |

*`Running (unknown)` = Docker healthcheck not configured. App IS running and responding. Not a real error.

#### Databases
| Name | Type | Status | Notes |
|------|------|--------|-------|
| `veklom-postgres` | PostgreSQL 15-alpine | Running (healthy) — 147x restarts | **ACTION NEEDED:** Pending config change not applied. Run redeploy to apply. Restart count is historical from before. |
| `veklom-redis` | Redis | Running (healthy) | Fine |
| `cappodb` | PostgreSQL | Running (healthy) | Fine |

#### Services
| Name | Status | Root Cause | Fix |
|------|--------|------------|-----|
| `github-runner-n7c69w73sfjoygmimv2j3wlj` | Degraded (unhealthy) — Restarting | `REPO_URL` env var is EMPTY. Runner requires `REPO_URL` for repo-scoped runners | Set `REPO_URL=https://github.com/reprewindai-dev/<target-repo>` in Coolify env vars |
| `github-runner-sjuu3jfh08pzslbwhe61xnig` | Exited — No such container | Never deployed successfully | Set `REPO_URL` + valid `ACCESS_TOKEN`, then click Deploy |
| `newapi-jv2pt97j6vgxcbfrbteue2k1` | Running (healthy) | — | Fine |

#### Unmanaged Docker Containers (running outside Coolify)
| Name | Image | Status |
|------|-------|--------|
| `terminal-veklom` | terminal-local:latest | running |
| `veklom-paid-gateway` | veklom-paid-gateway:latest | running |
| `veklom-ollama` | (Ollama) | running |
| `n13gp1nhrcdp0hvazvbnlxru-*` | veklom-local:latest | running (Coolify internal) |
| `coolify` | ghcr.io/coollabsio/coolify:4.1.2 | running |
| `coolify-db` | postgres:15-alpine | running |
| `coolify-redis` | redis:7-alpine | running |

---

## 5. GitHub Runners — What They Are & Fix Instructions

These are **self-hosted GitHub Actions runners** deployed as Docker services in Coolify using the `myoung34/github-runner:latest` image.

### Why They Are Broken
Both runners use `RUNNER_SCOPE=repo` which requires a `REPO_URL`. The value is currently **blank/not set**.

### How To Fix
1. Go to Coolify → veklom → production → github-runner service
2. Click Configuration → Environment Variables
3. Set the following:
 ```
 REPO_URL=https://github.com/reprewindai-dev/veklom-byos-backend
 ACCESS_TOKEN=<your GitHub PAT with repo + admin:org scope>
 RUNNER_SCOPE=repo
 LABELS=veklom-runner,self-hosted,linux
 ORG_NAME=reprewindai-dev
 ```
4. Click Save → Restart
5. Repeat for the second runner (set a different `RUNNER_NAME_PREFIX`)
6. Verify in GitHub → Settings → Actions → Runners

### Alternative: Use Org-Level Scope
If you want one runner to serve ALL repos in `reprewindai-dev`:
```
RUNNER_SCOPE=org
ORG_NAME=reprewindai-dev
ACCESS_TOKEN=<PAT>
```
(Remove `REPO_URL` when using org scope)

---

## 6. veklom-postgres Restart Issue

**Status:** Running healthy but shows 147x restarts (historical) and has a **pending config change warning**.

**Action needed:**
1. Go to Coolify → veklom → production → veklom-postgres
2. Click **Restart** (not Redeploy, to avoid data loss risk) OR click **Redeploy** if the config change is intentional
3. The 147 restarts are from a prior period and not ongoing — current health is good

---

## 7. Veklom-byos-backend-2 Clarification

`veklom-byos-backend-2` **does NOT exist** as a separate GitHub repo or Coolify managed app. This name appears in Coolify's resource stats dashboard as a Docker container name variant (Coolify appends suffixes for internal container tracking). It is the same application as `veklom-byos-backend`.

---

## 8. PayAPI Market Listing

**Target:** https://payapi.market
**Status:** Listing attempted — encountered 500 server error on PayAPI's side during submission.

**Listing details prepared:**
- API Name: Veklom AI API
- Base URL: https://api.veklom.com
- Auth: x402 (HTTP 402 Payment Required)
- Payment network: Base (USDC)
- Key endpoints: /api/v1/x402/payment-required, /api/v1/pricing, /api/v1/health

**Action needed:** Retry submission at https://payapi.market/list when their service is stable.

---

## 9. Second Server — Unreachable

Coolify shows a second server: `stupid-seahorse-n7gx1qmxtb1ulrbmb09rtyt0` with status **"Not reachable & Not usable by Coolify"**.

This server is likely a previous/decommissioned node. If it's no longer needed, it can be safely removed from Coolify settings (it does not affect localhost operations). Do NOT delete unless you confirm no services depend on it.

---

## 10. What Agents Must NEVER Do

- Do NOT delete any services, databases, or containers
- Do NOT spend Coinbase/Base wallet funds (reserved for game activation)
- Do NOT modify payment routing logic without testing x402 flow end-to-end
- Do NOT change veklom-postgres credentials without updating all service env vars
- Do NOT touch `SEKED_SECRET_KEY` or auth signing keys

---

## 11. Key Environment Variables (Do Not Expose)

All sensitive values are stored in Coolify's locked/secret env vars. Never log or print:
- `DATABASE_URL` / `POSTGRES_PASSWORD`
- `REDIS_URL`
- `SECRET_KEY` / `JWT_SECRET`
- `COINBASE_API_KEY` / `CDP_API_KEY`
- `GITHUB_ACCESS_TOKEN` (runner PAT)
- Any `X_PAYMENT_*` signing keys

---

## 12. x402 Compliance Checklist

Before any agent marks an endpoint as "x402 compliant" verify:
- [ ] Returns HTTP 402 (not 200, not 401) when payment is missing
- [ ] Response body contains `{ "x402Version": 1, "accepts": [...], "error": "Payment Required" }`
- [ ] `accepts` array has at minimum: `{ "scheme": "exact", "network": "base", "maxAmountRequired": "...", "resource": "...", "description": "...", "mimeType": "...", "payTo": "...", "maxTimeoutSeconds": 300, "asset": "...", "extra": { "name": "...", "version": "1" } }`
- [ ] After payment: server verifies `X-PAYMENT-*` header, returns 200
- [ ] Facilitator verify endpoint is configured if using facilitator flow

---

## 13. Deployment Workflow

1. Push to `main` branch on any Veklom repo
2. Coolify webhook triggers auto-deploy (Dockerfile build)
3. New container replaces old with zero-downtime swap
4. Check Coolify logs for build errors
5. Verify endpoint responds after deploy

**GitHub Actions (when runners are fixed):**
- Runners tagged: `veklom-runner, self-hosted, linux`
- Use in workflows: `runs-on: [self-hosted, veklom-runner]`

---

## 14. Contact / Ownership

- **GitHub org:** reprewindai-dev
- **Email:** reprewindai@gmail.com
- **Coolify:** http://5.78.135.11:8000
- **Hetzner VPS IP:** 5.78.135.11

---

*This file was generated by Comet (Perplexity AI Agent) on 2026-06-21 after a full infrastructure audit of the Veklom ecosystem. Keep this updated as the system evolves.*
