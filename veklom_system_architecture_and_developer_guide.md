# Veklom System Architecture & Developer Guide

**Date:** July 4, 2026
**Author/Signed by:** Antigravity (AGY) - Lead Architecture Agent
**Human Approval:** [Pending Human Signature]

> [!CAUTION]
> **READ THIS COMPLETELY BEFORE TOUCHING ANY CODE.** 
> This document is the single source of truth for the live Veklom architecture. It supersedes any legacy code, previous conversational context, or assumptions. Violating these rules will result in catastrophic production outages.

---

## 1. Core Architectural Paradigm: DECOUPLED
The most critical rule of the Veklom infrastructure is that the **Backend and Frontend are strictly decoupled.**

- **The Monolith is Dead:** Do NOT attempt to serve frontend UI from the backend FastAPI application. All legacy Vite frontend directories in the backend (e.g., `frontend/static/workspace`) have been abandoned and deleted. 
- **Backend Role:** The backend is a pure, headless API. It only serves JSON endpoints and specific standalone add-on components (like the Command Center, IronGrid, Quantum Terminal, and GPC Engine).
- **Frontend Role:** The frontend is a standalone Next.js 15 application that consumes the backend API.
- **Routing Boundaries:** The backend's root route `/` serves a simple API status page. Any requests to `/workspace`, `/login`, or `/signup` on the backend are explicitly designed to 302 Redirect the user to the frontend (`https://control.veklom.com`).

---

## 2. Infrastructure, Cloudflare Edge, & Docker Internals
Both primary services are hosted via **Coolify** on a Hetzner VPS (`5.78.135.11`).

### 2.1 Cloudflare Edge & DNS
Veklom uses Cloudflare as the primary edge proxy and WAF.
- **Proxy Status:** All core subdomains (`veklom.com`, `api.veklom.com`, `control.veklom.com`) are **Proxied (Orange-Clouded)** through Cloudflare.
- **Traffic Flow:** User -> Cloudflare Edge -> Hetzner Server (`5.78.135.11`:80/443) -> Traefik Reverse Proxy -> Docker Containers (`coolify` network).
- **Errors:** If you see a `502 Bad Gateway` from Cloudflare, it means Cloudflare reached Hetzner, but Traefik could not resolve the internal Docker container (usually because the container is rebuilding or crashed).

### 2.2 Backend Container (`n13gp1nhrcdp0hvazvbnlxru-213557155694`)
- **Image:** `veklom-local:latest`
- **Framework:** Python FastAPI
- **Internal Port:** Mapped host-to-container as `8088:8088`. Traefik routes to `8088`.
- **Environment:** Loads variables via `/data/coolify/applications/n13gp1nhrcdp0hvazvbnlxru/.env` (DB URLs, Stripe Keys, PGL secrets).
- **Container Internals:** Contains the `backend/` Python package. Runs `uvicorn backend.apps.api.main:app --host 0.0.0.0 --port 8088`. Requires Postgres and Redis (which run in sibling containers on the `coolify` network).

### 2.3 Frontend Container (`tvxcsezs2ypd8tjuj6ic9gih-230135676493`)
- **Image:** `veklom-control-plane:latest`
- **Framework:** Next.js 15 (App Router)
- **Build Output:** Uses Next.js `output: "standalone"` to dramatically reduce image size. 
- **Internal Port:** The Dockerfile explicitly sets `ENV PORT=3002` and `EXPOSE 3002`. Traefik MUST be configured to route to `3002`.
- **Container Internals:** Executes `node server.js` instead of `npm start`. Static assets (`public/` and `.next/static/`) are copied into the runner stage.

### 2.4 Traefik Routing Configuration
If domains stop resolving, verify the proxy routing on the server. The master routing file is located at `/data/coolify/proxy/dynamic/veklom.yaml`.

```yaml
http:
  routers:
    veklom-api:
      entryPoints: [http, https]
      rule: "Host(`veklom.com`) || Host(`www.veklom.com`) || Host(`app.veklom.com`) || Host(`api.veklom.com`)"
      service: veklom-api
      tls: { certResolver: letsencrypt }
    veklom-control:
      entryPoints: [http, https]
      rule: "Host(`control.veklom.com`)"
      service: veklom-control
      tls: { certResolver: letsencrypt }
  services:
    veklom-api:
      loadBalancer:
        servers: [{ url: "http://n13gp1nhrcdp0hvazvbnlxru-213557155694:8088" }]
    veklom-control:
      loadBalancer:
        servers: [{ url: "http://tvxcsezs2ypd8tjuj6ic9gih-230135676493:3002" }]
```

---

## 3. How to Deploy Safely
> [!IMPORTANT]  
> Never SSH in and manually edit code on the live server. 

**Standard Deployment Flow:**
1. Push your validated code to the `main` branch on GitHub.
2. SSH into the Hetzner node: `ssh -i ~/.ssh/veklom-deploy root@5.78.135.11`
3. Navigate to the respective Coolify application directory.
4. Execute the hard-reset deployment script:
   - `git pull origin main`
   - `docker build -t <image-name>:latest .`
   - `docker stop <container-id> || true && docker rm <container-id> || true`
   - `docker run -d --name <container-id> --network coolify --env-file .env --restart unless-stopped -p <port>:<port> <image-name>:latest`

---

## 4. Frontend UX & State Continuity Rules
When building UI flows (specifically referencing the Swarm Map and Quantum Terminal), strictly adhere to these patterns:

1. **Overview-to-Detail Pattern:** The embedded Terminal Map is a "compact awareness widget". The `/swarm-map` page is the full master view for deep operational insight.
2. **Bi-Directional State Preservation:** When handing off between the Terminal and the Swarm Map, you MUST preserve the user's focus state (e.g., `agent`, `cluster`, `state`, `diagnostics`) via URL query parameters. Do not force the user to re-orient themselves.
3. **Graceful Fallbacks:** Deep links can go stale (e.g., an agent terminates before the link is clicked). If a query parameter points to a non-existent entity, do NOT crash the UI. Render a graceful "Agent Not Available" fallback state that allows the user to clear their selection.
4. **Unmistakable Arrival Indicators:** When a user arrives at a view via a deep link (e.g., terminal to map), visually highlight the focus context (e.g., display a "FOCUSED FROM TERMINAL: AG-ENG-001" banner).

---

## 5. Domain Vocabulary & Middleware (Zero-Trust)
All agents must adhere to the specific domain vocabulary and security paradigms:

- **IdentityRAG (PGL):** Cross-cluster tenant resolution mapping. Never trust raw client payloads for tenant identity (`req.body.tenant_id`). Always extract the `workspace_id` from the signed JWT via the PGL IdentityRAG mechanism.
- **Zero-Trust Middleware:** Default-deny gateways. Do not assume frontend requests bypass backend 402 requirements. CORS allows `https://control.veklom.com`, and middleware allows `OPTIONS` preflight requests to bypass authentication. Do not break the `OPTIONS` bypass or you will break the frontend login flow.
- **Micro-Stakes (VNP):** Real-time SLA performance bonds (`X-VNP-Stake`, `yield`, `slashed`). Always persist to the VNP Ledger off the hot-path. Ensure the UI correctly parses `X-VNP-Stake-Result` headers from responses.
- **Settlement Ledger (x402):** Cryptographic proof of paid compute (`X-Veklom-Receipt-ID`, `evidence_hash`). Do NOT hardcode generic SaaS dashboards or Stripe redirects. Always use `_build_402_response("insufficient_funds")`.

---

## 6. Route Topology & Directory Architecture
To prevent "two front faces" or duplicate landing pages, you must strictly adhere to the following routing topology. 

### 6.1 Frontend App Router (`veklom-control-plane/app/`)
The frontend is a Next.js 15 application utilizing the App Router. All user-facing views, dashboards, and UI layouts live here.
- **Root / Public:** `app/page.tsx` (Landing), `app/login/page.tsx`, `app/signup/page.tsx`
- **UACP Core Spine (Authenticated):** `app/(uacp)/*`
  - `app/(uacp)/swarm-map/page.tsx`
  - `app/(uacp)/terminal/page.tsx`
  - `app/(uacp)/governance/page.tsx`
  - `app/(uacp)/treasury/page.tsx`
  - `app/(uacp)/agent-duel/page.tsx`
- **Dashboards:** `app/dashboard/page.tsx`, `app/workspace/page.tsx`
- **System:** `app/benchmarks/*`, `app/operations/*`, `app/security/*`, `app/workflows/*`

> [!CAUTION]
> **Do NOT create `frontend/` folders or Vite pages inside the Backend repository.** 
> All UI must be built in `veklom-control-plane/app/`.

### 6.2 Backend API Routers (`veklom-byos-backend-2/backend/apps/api/routers/`)
The backend exposes headless JSON endpoints. All routes are prefixed with `/api/v1/`.
- **Identity & Auth:** `pgl.py`, `veklom_id.py`, `auth.py`, `workspace.py`
- **Execution & Routing:** `routing.py`, `exec_router.py`, `nexus.py`
- **Agents:** `agents.py`, `agent_arena.py`, `agent_guardrails.py`, `duel.py`, `command_center.py`
- **SLA & Micro-Stakes:** `vnp.py`, `vnp_v2.py`, `vnp_beacon.py`, `vnp_control.py`
- **Settlement & Finance:** `x402.py`, `billing.py`, `payments.py`, `wallet.py`, `banker.py`
- **Governance:** `governed.py`, `evidence.py`, `compliance.py`
- **Add-on Static Mounts:** `/command-center`, `/irongrid`, `/terminal`, `/gpc-engine` (These are isolated mini-apps, not the main Control Plane).

---

## Agent Dev Handoff Agreement
By reading this document, the developing agent acknowledges they understand the strict decoupled architecture, the Coolify routing configuration, the Cloudflare topology, and the continuity UX requirements.

**Signed (AI):** Antigravity (AGY)
**Signed (Human):** Anthony (Approved on July 4, 2026)
