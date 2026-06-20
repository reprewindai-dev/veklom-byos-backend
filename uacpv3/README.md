# UACP V3 Control Plane

**Root = UACP V3 control plane. Nested `source-uacpgemini` = UACP V2 working reference copy.**

UACP V3 is the institutional control plane built on top of Quantum UACP and UACPGemini. The root app keeps the actual V2 Deterministic Engine as a surface inside a broader V3 institution:

- `Deterministic Engine`: live research ingestion, plan compilation, run telemetry, compiled artifacts
- `Sunnyvale`: plan review, approval, execution, workflows, live runs
- `Silicon Valley`: founder governance, pillars, committees, skills, source health
- `Archives`: replayable evidence, ordered events, compiled artifact memory

## Canonical structure

```txt
system-uacp-v3-control-plane-you/
├── README.md
├── UACP-V3-MASTER-PROMPT.md
├── UACP-V3-PROMPT-1-SYSTEM.md
├── UACP-V3-PROMPT-2-SKILLS-BUILDERS.md
├── package.json
├── render.yaml
├── server.ts
├── src/
├── data/
├── source-uacpgemini/
├── source-uacp-v1/
└── source-genai-processors/
```

Naming rule:

- `UACP V3 root project` = repository root
- `UACP V2 nested working copy` = `source-uacpgemini`
- `V2 executes; V3 governs.`

## What is real in the root app

- Live public-source research ingestion from:
  - arXiv
  - PubMed
  - Crossref
  - Zenodo
- Persistent file-backed control-plane state in `data/control-plane-state.json`
- Persistent governed registry in `data/governance-registry.json`
- Real plan compilation grounded in live references
- Real governed run stages with compiled artifacts
- Real archive records and ordered event logs
- Real source-health reporting with latency, item counts, and error state
- Telemetry derived from actual plans, runs, archives, and source status
- Real named worker registry, operator runtime, backend-event ingestion, and Command Center truth

The root app does not use seeded plans, hardcoded research cards, or artificial run generation.

## How the root app works

1. Enter intent in `Deterministic Engine`
2. Compile a governed plan
3. Review the plan, live references, pillars, committees, votes, and graph
4. Route the plan into `Sunnyvale`
5. Approve and launch the governed run
6. Inspect stage-by-stage execution telemetry
7. Open the compiled artifact
8. Verify evidence in `Archives`

## API

- `GET /api/bootstrap`
- `GET /api/health`
- `GET /api/governance-registry`
- `GET /api/pillars`
- `GET /api/committees`
- `GET /api/operator-committees`
- `GET /api/operators`
- `GET /api/operator-runtime`
- `GET /api/operator-runs`
- `GET /api/skills`
- `GET /api/workflows`
- `GET /api/escalation-rules`
- `GET /api/backend-summary`
- `GET /api/backend-events`
- `GET /api/command-center`
- `GET /api/research-signals`
- `GET /api/research-status`
- `GET /api/provider-readiness`
- `POST /api/research-refresh`
- `GET /api/plans`
- `POST /api/plans`
- `GET /api/runs`
- `POST /api/runs`
- `GET /api/events`
- `GET /api/archives`
- `GET /api/telemetry`
- `GET /api/observability/signals`
- `GET /api/ssrn-signals`

Protected internal mutation routes:

- `PUT /api/governance-registry`
- `POST /api/v1/internal/backend/events`
- `POST /api/v1/internal/operators/:workerId/run`
- `POST /api/v1/internal/operators/:workerId/pause`
- `POST /api/v1/internal/operators/:workerId/resume`
- `POST /api/v1/internal/operators/:workerId/escalate`

## Local development

```bash
npm install
npm run dev
```

V3 root runs on [http://localhost:3000](http://localhost:3000).

## Runtime contract

- Veklom backend truth is ingested as normalized backend events and summary counters.
- UACP institutional truth owns pillars, committees, workers, operator runs, escalations, and archives.
- Minimum-live workers are scheduled automatically on startup and then on heartbeat intervals.
- Plans select from the governed registry; they do not silently invent active governance objects.

## Run both copies

### V3 working copy

Folder:

- [system-uacp-v3-control-plane-you](C:/Users/antho/Documents/Codex/2026-05-08/system-uacp-v3-control-plane-you)

Run:

```bash
npm install
npm run dev
```

URL:

- [http://localhost:3000](http://localhost:3000)

### V2 working copy

Folder:

- [source-uacpgemini](C:/Users/antho/Documents/Codex/2026-05-08/system-uacp-v3-control-plane-you/source-uacpgemini)

Run:

```bash
npm install
npm run dev
```

URL:

- [http://localhost:3001](http://localhost:3001)

## Environment

Copy `.env.example` to `.env` and set:

```bash
PORT=3000
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
GROQ_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile
HF_TOKEN=
HF_MODEL=openai/gpt-oss-120b
HF_BASE_URL=https://router.huggingface.co/v1
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=
OLLAMA_API_KEY=
UACP_MODEL_PROVIDER_ORDER=groq,ollama,huggingface
UACP_MODEL_PROVIDER=
UACP_ENABLE_GEMINI_PRIMARY=false
ALLOW_GEMINI_FALLBACK=false
USER_EMAIL=founder@company.com
CONTACT_EMAIL=founder@company.com
DEFAULT_RESEARCH_QUERY=ai governance orchestration workflow observability api mcp deployment compliance
DATA_DIR=./data
UACP_ADMIN_KEY=
UACP_INTERNAL_API_KEY=
UACP_BOX_NAME=uacp-pillar-council
UACP_RUNTIME_MODE=pillar_council
UACP_WORKER_GROUP=pillar_council
UACP_ARCHIVE_WRITE_REQUIRED=true
UACP_BACKEND_BASE_URL=
UACP_BACKEND_TIMEOUT_MS=8000
UPSTASH_REDIS_REST_URL=
UPSTASH_REDIS_REST_TOKEN=
UACP_RATE_LIMIT_TRUST_ACCESS_TIER_HEADER=false
UACP_RATE_LIMIT_PUBLIC_FREE_LIMIT=10
UACP_RATE_LIMIT_PUBLIC_PAID_LIMIT=60
UACP_RATE_LIMIT_HEAVY_FREE_LIMIT=3
UACP_RATE_LIMIT_HEAVY_PAID_LIMIT=20
UACP_RATE_LIMIT_REFRESH_FREE_LIMIT=2
UACP_RATE_LIMIT_REFRESH_PAID_LIMIT=12
QSTASH_URL=https://qstash.upstash.io
QSTASH_TOKEN=
QSTASH_CURRENT_SIGNING_KEY=
QSTASH_NEXT_SIGNING_KEY=
UACP_PUBLIC_BASE_URL=https://uacpv3.onrender.com
UACP_QSTASH_QUEUE_NAME=uacp-worker-conveyor
UACP_QSTASH_CONVEYOR_SCHEDULE_ID=uacp-v3-worker-conveyor
UACP_QSTASH_CONVEYOR_CRON="*/5 * * * *"
UPSTASH_SEARCH_REST_URL=
UPSTASH_SEARCH_REST_TOKEN=
UACP_SEARCH_INDEX=default
```

V3 now supports four model providers:

- `Groq` via `GROQ_API_KEY`
- `Hugging Face` via `HF_TOKEN`
- `Ollama` via `OLLAMA_BASE_URL` + `OLLAMA_MODEL`
- `Gemini` via `GEMINI_API_KEY`

Default runtime order is `groq -> ollama -> huggingface`. Gemini is kept configured but is not primary unless you explicitly enable it with `UACP_ENABLE_GEMINI_PRIMARY=true`, set `ALLOW_GEMINI_FALLBACK=true`, or force it with `UACP_MODEL_PROVIDER=gemini`.

If no external model provider is ready, the root app still compiles plans with the deterministic local planner grounded in live public research.

`UACP_ADMIN_KEY` enables governed registry updates.

`UACP_INTERNAL_API_KEY` secures backend-event ingestion and operator mutation endpoints. If it is unset, internal mutation routes are disabled.

`UACP_BOX_NAME`, `UACP_RUNTIME_MODE`, and `UACP_WORKER_GROUP` give a Box or worker runtime a clean identity without changing the full server behavior.

`UACP_ARCHIVE_WRITE_REQUIRED=true` marks this runtime as archive-writing infrastructure. The server logs that requirement at startup but does not print secrets.

`UACP_BACKEND_BASE_URL` points the V3 control plane at the protected backend-truth service so `/api/sunnyvale-internal` can populate Evaluation Surgeon and Hub Growth Navigator from real backend queues using `UACP_INTERNAL_API_KEY`.

`UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` enable production rate limiting for public mutation routes through Upstash Redis. Use the Redis `REST` credentials from Upstash, not the `TCP` endpoint. The Node runtime uses `@upstash/redis` over HTTPS so it does not need Redis host, port, username, or password fields.

`QSTASH_URL`, `QSTASH_TOKEN`, `QSTASH_CURRENT_SIGNING_KEY`, and `QSTASH_NEXT_SIGNING_KEY` enable the durable worker conveyor. Use the QStash Request Builder/Quickstart values directly. QStash publishes signed POST requests to `POST /api/v1/qstash/worker-conveyor`, which releases due workers one lane at a time instead of burst-firing every worker in-process. `UACP_PUBLIC_BASE_URL` must be the public Render URL.

`UPSTASH_SEARCH_REST_URL`, `UPSTASH_SEARCH_REST_TOKEN`, and `UACP_SEARCH_INDEX=default` enable the Upstash Search document layer. This is where workers can index and query real buyer, vendor, market, evidence, and tool documents instead of depending only on in-memory research lists. The Upstash console index you showed is `default`, so V3 now defaults to that index unless overridden per request.

`RESEND_API_KEY`, `RESEND_FROM_EMAIL`, and optional `UACP_OUTBOUND_REPLY_TO` enable governed outbound email sends for worker-backed outreach. The live outbound summary is exposed in `GET /api/outbound/runtime`, and full queue/message inspection is available on the protected internal routes. Contacts can now be inserted directly through the internal outbound work-order route, then released to the `welcome` or `vendor-recruiter` workers for Resend execution.

`DATABASE_URL` and optional `DATABASE_SSL_MODE` enable Postgres-backed hot storage for runtime state and governance registry. V3 keeps file fallback and also writes compressed cold snapshots under `UACP_COLD_STORAGE_DIR` so the database stays small while replayable state remains recoverable.

For infrastructure split:

- Render web service should use the Render-internal database URL.
- Upstash Box should use `UACP_BOX_DATABASE_URL` if the internal Render hostname is not reachable from the Box.

`UACP_RATE_LIMIT_TRUST_ACCESS_TIER_HEADER=false` keeps all public callers on the free tier unless you explicitly trust an upstream gateway to set `x-uacp-access-tier` and `x-uacp-user-id`.

Public mutation profiles:

- `public_mutation`: free `10/10s`, paid `60/10s`
- `heavy_mutation`: free `3/1m`, paid `20/1m`
- `refresh`: free `2/1m`, paid `12/1m`

The live rate-limit state is exposed in `GET /api/health` under `runtime.rateLimit`.

## Render deployment

Deploy V3 from the repository root only.

- Service root: [system-uacp-v3-control-plane-you](C:/Users/antho/Documents/Codex/2026-05-08/system-uacp-v3-control-plane-you)
- Blueprint: [render.yaml](C:/Users/antho/Documents/Codex/2026-05-08/system-uacp-v3-control-plane-you/render.yaml)
- Build command: `npm install && npm run build`
- Start command: `npm run start`

Required environment variables:

- `NODE_ENV=production`
- `USER_EMAIL`
- `CONTACT_EMAIL`

Optional environment variables:

- `GEMINI_API_KEY`
- `GEMINI_MODEL`
- `GROQ_API_KEY`
- `GROQ_MODEL`
- `HF_TOKEN`
- `HF_MODEL`
- `HF_BASE_URL`
- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL`
- `OLLAMA_API_KEY`
- `UACP_MODEL_PROVIDER_ORDER`
- `UACP_MODEL_PROVIDER`
- `UACP_ENABLE_GEMINI_PRIMARY`
- `ALLOW_GEMINI_FALLBACK`
- `UPSTASH_REDIS_REST_URL`
- `UPSTASH_REDIS_REST_TOKEN`
- `RESEND_API_KEY`
- `RESEND_FROM_EMAIL`
- `UACP_OUTBOUND_REPLY_TO`
- `UACP_OUTBOUND_MAX_SENDS_PER_RUN`
- `DATABASE_URL`
- `DATABASE_SSL_MODE`
- `UACP_COLD_STORAGE_DIR`
- `UACP_BOX_DATABASE_URL`
- `UACP_BOX_DATABASE_SSL_MODE`
- `UACP_RATE_LIMIT_TRUST_ACCESS_TIER_HEADER`
- `UACP_RATE_LIMIT_PUBLIC_FREE_LIMIT`
- `UACP_RATE_LIMIT_PUBLIC_PAID_LIMIT`
- `UACP_RATE_LIMIT_HEAVY_FREE_LIMIT`
- `UACP_RATE_LIMIT_HEAVY_PAID_LIMIT`
- `UACP_RATE_LIMIT_REFRESH_FREE_LIMIT`
- `UACP_RATE_LIMIT_REFRESH_PAID_LIMIT`
- `UACP_ADMIN_KEY`
- `UACP_INTERNAL_API_KEY`
- `DEFAULT_RESEARCH_QUERY`
- `DATA_DIR`

## Upstash Box runtime

For the hot control box, use the dedicated pillar-council entrypoint:

```bash
cd /workspace/home/uacpv3 && npm install && npm run build && npm run worker:pillar-council
```

This keeps the existing V3 UI/API/WebSocket/control-plane behavior, but boots it with Box identity defaults:

- `UACP_BOX_NAME=uacp-pillar-council`
- `UACP_RUNTIME_MODE=pillar_council`
- `UACP_WORKER_GROUP=pillar_council`
- `UACP_ARCHIVE_WRITE_REQUIRED=true`

Committee box topology:

- `pillar_council` (hot)
  - workers: `gauge`, `ledger`, `sentinel`, `mirror`, `pulse`, `sheriff`, `polish`, `oracle`, `glide`
  - role: governance, truth, observability, assurance, replay integrity
- `growth_sales` (warm)
  - workers: `signal`, `mint`, `scout`, `spyglass`, `raider`, `welcome`
  - startup: `npm run worker:growth-sales`
- `operations_intake` (warm)
  - workers: `herald`, `harvest`, `bouncer`, `arbiter`
  - startup: `npm run worker:operations-intake`
- `builder_systems` (warm)
  - workers: `builder-scout`, `builder-forge`, `builder-arbiter`
  - startup: `npm run worker:builder-systems`
- `vendor_network` (warm)
  - workers: `vendor-scout`, `vendor-recruiter`, `vendor-auditor`
  - startup: `npm run worker:vendor-network`

Wake rules:

- `growth_sales`: outbound queue pressure, qualified pipeline pressure, competitor movement
- `operations_intake`: backend-event bursts, intake backlog, routing exceptions
- `builder_systems`: accepted build backlog, automation expansion, delivery blockers
- `vendor_network`: partner queue, vendor qualification demand, channel expansion

Handoff rules:

- `operations_intake` -> `growth_sales` when buyer motion is qualified
- `growth_sales` -> `vendor_network` when partner or affiliate path is better than direct sale
- `growth_sales` -> `builder_systems` when tooling or delivery blockers stop conversion
- all warm boxes -> `pillar_council` when policy, truth, replay, or risk thresholds are hit

The runtime logs:

- control plane startup
- box name
- runtime mode
- registry load summary
- minimum-live workers
- operator scheduler status
- archive/data directory
- provider readiness without printing secrets

Health and verification endpoints:

- `GET /api/health`
- `GET /api/bootstrap`
- `GET /api/box-topology`
- `GET /api/outbound/runtime`
- `GET /api/qstash/runtime`
- `GET /api/search/runtime`
- `GET /api/v1/internal/operators` with header `x-uacp-internal-key: $UACP_INTERNAL_API_KEY`
- `GET /api/v1/internal/operators/runs` with header `x-uacp-internal-key: $UACP_INTERNAL_API_KEY`
- `GET /api/v1/internal/outbound/contacts` with header `x-uacp-internal-key: $UACP_INTERNAL_API_KEY`
- `GET /api/v1/internal/outbound/messages` with header `x-uacp-internal-key: $UACP_INTERNAL_API_KEY`
- `POST /api/v1/internal/outbound/contacts` with header `x-uacp-internal-key: $UACP_INTERNAL_API_KEY`
- `POST /api/v1/internal/outbound/release` with header `x-uacp-internal-key: $UACP_INTERNAL_API_KEY`
- `POST /api/v1/internal/qstash/worker-conveyor/publish` with header `x-uacp-internal-key: $UACP_INTERNAL_API_KEY`
- `POST /api/v1/internal/qstash/worker-conveyor/schedule` with header `x-uacp-internal-key: $UACP_INTERNAL_API_KEY`
- `POST /api/v1/qstash/worker-conveyor` signed by QStash; do not call this route manually in production
- `POST /api/v1/internal/search/documents` with header `x-uacp-internal-key: $UACP_INTERNAL_API_KEY`
- `POST /api/v1/internal/search/query` with header `x-uacp-internal-key: $UACP_INTERNAL_API_KEY`

Outbound contact work-order payload:

```json
{
  "release": true,
  "contacts": [
    {
      "kind": "customer",
      "email": "buyer@example.com",
      "accountLabel": "Buyer Name",
      "company": "Buyer Company",
      "sourceUrl": "https://example.com",
      "consentBasis": "targeted business outreach",
      "reason": "Buyer matches governed AI workflow ICP",
      "tags": ["paid-pilot"]
    },
    {
      "kind": "vendor",
      "email": "partner@example.com",
      "accountLabel": "Partner Name",
      "company": "Partner Company",
      "sourceUrl": "https://partner.example.com",
      "reason": "Potential implementation or distribution partner"
    }
  ]
}
```

`release: true` immediately queues the assigned worker run. Without `release`, the contacts remain staged until `POST /api/v1/internal/outbound/release`.

Storage model:

- hot: in-memory runtime state
- warm: Postgres via `DATABASE_URL`
- cold: compressed snapshots in `UACP_COLD_STORAGE_DIR`

If `UACP_INTERNAL_API_KEY` is unset, the internal operator endpoints remain intentionally disabled.

If you want to drive the Box from your local machine with the Upstash Box SDK, use:

```bash
npm run box:setup
```

To create or reconcile the full hot/warm committee fleet in one pass, use:

```bash
npm run box:setup:fleet
```

That script reads:

- `UPSTASH_BOX_API_KEY`
- `UPSTASH_BOX_ID` or `UPSTASH_BOX_NAME`
- `UACP_INTERNAL_API_KEY`
- `UACP_BOX_DATABASE_URL` when the Box cannot reach the Render-internal Postgres hostname

It will connect to the Box, ensure the pillar-council init command, resume or restart the Box when needed, and verify:

- `GET /api/health`
- `GET /api/bootstrap`
- `GET /api/v1/internal/operators`
- `GET /api/v1/internal/operators/runs`

The fleet setup command reads the same base secrets and also:

- auto-detects the local git `origin` URL and branch unless you override them with `UPSTASH_BOX_GIT_URL` and `UPSTASH_BOX_GIT_REF`
- creates missing committee boxes as `keepAlive` node boxes
- bootstraps `/workspace/home/uacpv3`
- writes per-box runtime `.env`
- verifies `GET /api/box-topology` and internal operator endpoints on every lane

Supported fleet boxes:

- `uacp-pillar-council`
- `uacp-growth-sales`
- `uacp-operations-intake`
- `uacp-builder-systems`
- `uacp-vendor-network`

To limit reconciliation to a subset, set:

```bash
UACP_BOX_FLEET=pillar_council,growth_sales
```

For the full access and recovery procedure, including SSH sign-in, the canonical Box name, the live host id, and the stale-runtime replacement path, use:

- [docs/UPSTASH-BOX-OPERATIONS.md](C:/Users/antho/Documents/Codex/2026-05-08/system-uacp-v3-control-plane-you/docs/UPSTASH-BOX-OPERATIONS.md)

Do not point the V3 Render service at `source-uacpgemini` unless you explicitly want to deploy V2 instead.

## Doctrine

- Plans are promises, not prompts.
- Governance is distinct from execution.
- Skills are governed execution artifacts.
- Archives preserve replayable judgment.

## Prompt assets

- [UACP-V3-MASTER-PROMPT.md](C:/Users/antho/Documents/Codex/2026-05-08/system-uacp-v3-control-plane-you/UACP-V3-MASTER-PROMPT.md)
- [UACP-V3-PROMPT-1-SYSTEM.md](C:/Users/antho/Documents/Codex/2026-05-08/system-uacp-v3-control-plane-you/UACP-V3-PROMPT-1-SYSTEM.md)
- [UACP-V3-PROMPT-2-SKILLS-BUILDERS.md](C:/Users/antho/Documents/Codex/2026-05-08/system-uacp-v3-control-plane-you/UACP-V3-PROMPT-2-SKILLS-BUILDERS.md)

## Lineage

- [source-uacp-v1](C:/Users/antho/Documents/Codex/2026-05-08/system-uacp-v3-control-plane-you/source-uacp-v1): UACP V1 reference clone
- [source-uacpgemini](C:/Users/antho/Documents/Codex/2026-05-08/system-uacp-v3-control-plane-you/source-uacpgemini): UACP V2 nested working copy
- [source-genai-processors](C:/Users/antho/Documents/Codex/2026-05-08/system-uacp-v3-control-plane-you/source-genai-processors): reference clone for Gemini processor pipelines
