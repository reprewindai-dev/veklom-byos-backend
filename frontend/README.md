# Veklom Workspace — frontend

The dashboard frontend lives **inside** this repo. The FastAPI backend in `backend/` mounts the built bundle at `/workspace` (see `backend/apps/api/main.py` → `WORKSPACE_DIR`). This is a full-stack project; the two halves ship together.

## Why it's structured this way

- **Source is multi-file.** Every page is its own file under `src/pages/`. Every backend router has its own API client under `src/api/`. Upgrade one without touching the others.
- **No external build artifacts committed.** Run `npm run build` only when you want to refresh `static/workspace/` (what FastAPI serves). Day-to-day development uses the Vite dev server.
- **Same origin as the backend.** When `VITE_VEKLOM_API_BASE` is empty (the default), `fetch` calls go to the same origin that served the page — i.e. directly to the FastAPI app. No CORS, no extra config.

## Quickstart

In one terminal (backend):

```bash
cd ../backend
uvicorn apps.api.main:app --reload --port 8000
```

In another (frontend):

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173 — proxies /api/* to :8000
```

To build a static bundle the FastAPI app can serve:

```bash
npm run build        # outputs to ./static/workspace/
```

Then visit `http://localhost:8000/workspace/`.

## Layout

```
frontend/
├── index.html                ← Vite entry
├── package.json
├── vite.config.ts            ← builds to static/workspace, dev-proxies /api → :8000
├── tsconfig.json
├── tailwind.config.ts
├── postcss.config.js
├── public/
│   ├── favicon.svg
│   └── config.js             ← runtime override slot (window.__VEKLOM_API_BASE__)
├── src/
│   ├── main.tsx              ← bootstrap (React, react-query, ToastProvider)
│   ├── App.tsx               ← wouter hash router + auth gate
│   ├── styles/globals.css    ← tokens + Tailwind base + theme
│   ├── lib/
│   │   ├── env.ts            ← API base resolver
│   │   ├── auth.ts           ← veklom_token store (same key the backend's GH OAuth bridge writes)
│   │   ├── http.ts           ← fetch wrapper, Authorization injection
│   │   ├── query.ts          ← QueryClient
│   │   ├── format.ts         ← USD / number / time / hash helpers
│   │   └── utils.ts          ← cn() class merger
│   ├── api/                  ← ONE FILE PER BACKEND ROUTER (drop-in upgrades)
│   │   ├── index.ts          ←   barrel
│   │   ├── types.ts          ←   shared shapes
│   │   ├── auth.ts           ←   /api/v1/auth/*
│   │   ├── ai.ts             ←   /api/v1/ai/*
│   │   ├── workspace.ts      ←   /api/v1/workspace/*
│   │   ├── marketplace.ts    ←   /api/v1/marketplace/* + public veklom.com/marketplace
│   │   ├── compliance.ts     ←   /api/v1/compliance/*, /privacy/*, /content-safety
│   │   ├── audit.ts          ←   /api/v1/audit/*
│   │   ├── billing.ts        ←   /wallet, /subscriptions, /billing, /budget, /cost
│   │   ├── routing.ts        ←   /routing/*, /autonomous/*
│   │   ├── monitoring.ts     ←   /platform/pulse, /monitoring/*, /insights, /telemetry
│   │   ├── security.ts       ←   /security/*, /kill-switch/*, /locker/*
│   │   ├── pipelines.ts      ←   /pipelines/*, /pipeline/interactive
│   │   ├── deployments.ts    ←   /deployments/*, /edge/canary/*
│   │   ├── admin.ts          ←   /admin/*, /internal/uacp/*, /source-of-truth/*
│   │   ├── commandCenter.ts  ←   /command-center/*  (super-user)
│   │   ├── gpc.ts            ←   /gpc/* + /decision-frames/*
│   │   └── agents.ts         ←   /agents/*, /agents/hrm/*, /copilot/*, /repo-risk-gate/*
│   ├── hooks/
│   │   ├── useAuth.ts        ← session state subscription
│   │   └── useToast.tsx      ← in-app toaster
│   ├── components/
│   │   ├── ui/               ← Button, Input, Textarea, Skeleton (hand-written primitives)
│   │   ├── brand/            ← Logo, StatusChips, RouteChip, ComplianceTag, etc.
│   │   ├── charts/Mini.tsx   ← Recharts wrappers (Sparkline, MultiLine, Bars)
│   │   ├── data/States.tsx   ← LoadingState, EmptyState, ErrorState
│   │   └── layout/           ← AppShell, Sidebar, TopBar, PageHeader, DemoBanner, nav.ts
│   └── pages/                ← ONE FILE PER ROUTE
│       ├── Login.tsx
│       ├── Overview.tsx              ← /platform/pulse + /monitoring/events + /audit/logs
│       ├── Playground.tsx            ← /ai/models + /ai/complete + /wallet/balance
│       ├── Marketplace.tsx           ← /marketplace/listings + veklom.com/marketplace
│       ├── MarketplaceListing.tsx    ← /marketplace/listings/{id}
│       ├── Models.tsx                ← /workspace/models (toggle via PATCH)
│       ├── Pipelines.tsx             ← /pipelines
│       ├── Deployments.tsx           ← /deployments
│       ├── Routing.tsx               ← /routing/topology + /routing/economics + /autonomous
│       ├── Monitoring.tsx            ← /monitoring/health + /monitoring/events + /audit
│       ├── Vault.tsx                 ← /auth/api-keys + /workspace/api-keys (create + revoke)
│       ├── Compliance.tsx            ← /compliance/regulations + /privacy/status
│       ├── Billing.tsx               ← /wallet/* + /subscriptions/* + /billing/invoices
│       ├── Team.tsx                  ← /workspace/members (invite)
│       ├── Settings.tsx              ← /workspace
│       ├── CommandCenter.tsx         ← /command-center/*           (super-user)
│       ├── GpcTerminal.tsx           ← /command-center/terminals/* (super-user, allowlist-bound)
│       ├── Gpc.tsx                   ← /gpc/* + /decision-frames/*
│       ├── Agents.tsx                ← /agents/* (registry, fleet, guardrails, skills)
│       └── NotFound.tsx
```

## Adding a backend endpoint (the upgrade workflow)

1. **Backend** — add the route in `backend/apps/api/routers/<name>.py`.
2. **Frontend** — add the matching method to `src/api/<name>.ts`. Type the request/response from the FastAPI model.
3. **UI** — wire it from a page in `src/pages/` using `useQuery` / `useMutation`. Loading, empty, and error states are already plumbed through `src/components/data/States.tsx`.

No central registry to touch, no codegen step, no breakage from one router's changes leaking into another's UI.

## Auth contract (matches the backend)

- Backend issues JWT pairs on `POST /api/v1/auth/login` and `/register`.
- Frontend stores them in `localStorage` under `veklom_token`, `veklom_refresh_token`, `veklom_user` — the same keys the backend's GitHub OAuth bridge writes (see `apps/api/routers/auth.py`).
- `src/lib/http.ts` injects `Authorization: Bearer <token>` automatically and clears storage on `401`.

## Super-user surfaces

- **Command Center** — `/api/v1/command-center/*` cross-workspace ops dashboard.
- **GPC Terminal** — `/api/v1/command-center/terminals/{veklom,quantum}` returns the **allowlist** of commands the terminal is permitted to dispatch. The UI enforces the allowlist client-side and refuses unknown labels.
- **GPC Plans / Runs / Decision Frames** — `/api/v1/gpc/*` + `/api/v1/decision-frames/*`.
- **Agent Workforce** — `/api/v1/agents/*` + `/api/v1/agents/hrm/*`.

## Marketplace source of truth

`https://veklom.com/marketplace` is the public catalog. `src/api/marketplace.ts` merges it with the authenticated workspace catalog from `/api/v1/marketplace/listings`. Unauthenticated visitors see the public set; authenticated tenants see both.
