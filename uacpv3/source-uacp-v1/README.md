# Quantum UACP v0

Quantum UACP is a runnable full-stack prototype for hybrid quantum/classical workflow orchestration with three locked user-facing surfaces and six backend object families.

## Included
- Intent Console
- Execution Graph
- Ops / Control Plane
- Express API server
- Gateway execution endpoint
- PlanStatus / RunStatus separation
- Plan revisions
- Idempotent run submission
- Event log sequencing
- Gopher policy evaluation
- Horowitz observability signals
- Mock HHL and VQE hybrid workloads
- Render deployment config

## Local development

```bash
npm install
npm run dev
```

Client runs on `http://localhost:5173` and proxies `/api` to `http://localhost:3001`.

## Production build

```bash
npm run build
npm start
```

This builds the Vite client into `dist/` and compiles the Express server into `dist-server/`.

## Main API routes
- `GET /api/bootstrap`
- `GET /api/plans`
- `POST /api/plans`
- `POST /api/plans/:id/status`
- `POST /api/plans/:id/revise`
- `GET /api/runs`
- `POST /api/runs/:id/status`
- `POST /api/gateway/execute`
- `POST /api/policies/evaluate`
- `GET /api/events`
- `GET /api/observability/signals`
- `POST /api/reset`

## Deployment

### Render
This repo includes `render.yaml`. Connect the repo to Render and deploy as a Node web service. Render supports straightforward deployment of Node/Express apps, and Vite-based full-stack projects commonly use a build step that outputs the frontend and serves it from the Node process [web:372][web:369][web:380].

### GitHub Actions
A CI workflow is included to run install, typecheck, and build on pushes and pull requests [file:1].

## Product doctrine
- Plans are promises, not prompts.
- Plan governance is distinct from run execution.
- Gateway admission is explicit.
- Event sequencing is append-only and ordered.
- Replay can be treated as first-class evidence.
- Policy and observability are core surfaces, not afterthoughts.
