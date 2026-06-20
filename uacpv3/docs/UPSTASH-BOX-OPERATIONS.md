# Upstash Box Operations

## Purpose

This runbook is the canonical access and alignment path for the live UACP Box fleet. Use it when an agent needs to sign in, verify runtime state, or force the committee boxes onto the current production commit.

## Canonical Box Identity

- Hot box:
  - Box name: `uacp-pillar-council`
  - Current Box host id: `sought-python-57910`
  - SSH target: `ssh sought-python-57910@us-east-1.box.upstash.com`
  - Runtime entrypoint: `npm run worker:pillar-council`
  - Runtime port: `3000`
- Warm fleet:
  - `uacp-growth-sales`
  - `uacp-operations-intake`
  - `uacp-builder-systems`
  - `uacp-vendor-network`

Use the Box name as the primary handle. Only fall back to the host id when you need direct SSH.

## Sign-In Rules

The Box API key is not stored in the repo.

Agents must load it from a local secret store or environment before attempting Box operations:

- required env: `UPSTASH_BOX_API_KEY`
- optional override: `UPSTASH_BOX_ID`
- normal target: `UPSTASH_BOX_NAME=uacp-pillar-council`

For SSH, the password is the same `UPSTASH_BOX_API_KEY`.

Do not commit the API key, internal key, admin key, or provider keys into git.

## Required Runtime Secrets

At minimum, the Box runtime should have:

- `UACP_INTERNAL_API_KEY`
- `UACP_ADMIN_KEY`
- `UACP_BOX_NAME=uacp-pillar-council`
- `UACP_RUNTIME_MODE=pillar_council`
- `UACP_WORKER_GROUP=pillar_council`
- `UACP_ARCHIVE_WRITE_REQUIRED=true`

Provider envs are optional for boot, but required for non-deterministic evidence-backed runs:

- `HF_TOKEN`
- `HF_MODEL`
- `GROQ_API_KEY`
- `GROQ_MODEL`
- `GEMINI_API_KEY`
- `GEMINI_MODEL`
- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL`
- `UACP_MODEL_PROVIDER`
- `UACP_MODEL_PROVIDER_ORDER`

## Local Alignment Command

From the repo root:

```bash
npm run box:setup
```

For the full fleet:

```bash
npm run box:setup:fleet
```

The setup script:

- connects to the Box
- verifies Node and npm
- ensures the pillar-council init command
- writes the runtime `.env`
- resumes or relaunches when needed
- verifies:
  - `/api/health`
  - `/api/bootstrap`
  - `/api/v1/internal/operators`
  - `/api/v1/internal/operators/runs`

The fleet setup script:

- creates missing warm committee boxes as keep-alive node boxes
- auto-detects the repo `origin` URL and current branch
- clones or realigns `/workspace/home/uacpv3`
- sets the correct startup command for each committee lane
- writes per-box runtime `.env`
- verifies:
  - `/api/health`
  - `/api/bootstrap`
  - `/api/box-topology`
  - `/api/v1/internal/operators`
  - `/api/v1/internal/operators/runs`

Fleet filter:

```bash
UACP_BOX_FLEET=pillar_council,growth_sales npm run box:setup:fleet
```

## Direct Box Startup Command

Inside the Box workspace:

```bash
cd /workspace/home/uacpv3 && npm install && npm run build && npm run worker:pillar-council
```

## Live Reconciliation Procedure

Use this when the Box is behind repo `main` or serving stale runtime state.

1. Load `UPSTASH_BOX_API_KEY`.
2. Run `npm run box:setup`.
3. Compare the Box workspace commit against local `origin/main`.
4. If the Box workspace is behind:
   - stash Box-local changes with `git stash push --include-untracked`
   - `git fetch origin main`
   - `git reset --hard origin/main`
   - `git clean -fd`
   - `npm install`
   - `npm run build`
5. Replace the active listener on port `3000`.
6. Start the correct runtime:
   - `npm run worker:pillar-council`
   - `npm run worker:growth-sales`
   - `npm run worker:operations-intake`
   - `npm run worker:builder-systems`
   - `npm run worker:vendor-network`
7. Re-verify health and governance endpoints.

## Verification Endpoints

Public runtime checks:

- `GET /api/health`
- `GET /api/bootstrap`
- `GET /api/governance-registry`
- `GET /api/operators`
- `GET /api/operator-runtime`
- `GET /api/v3/workers`
- `GET /api/v3/committees`
- `GET /api/v3/commercial-scorecard`
- `GET /api/provider-readiness`
- `GET /api/research-status`

Internal checks:

- `GET /api/v1/internal/operators` with header `x-uacp-internal-key: $UACP_INTERNAL_API_KEY`
- `GET /api/v1/internal/operators/runs` with header `x-uacp-internal-key: $UACP_INTERNAL_API_KEY`

## Expected Healthy State

- registry version matches repo
- `25` named workers present
- `6` operator committees present
- scheduler enabled
- minimum-live workers heartbeating
- runtime mode is `pillar_council`
- worker group is `pillar_council`
- archive writes required

## Failure Notes

- If `/api/health` is good but a new worker start fails with `EADDRINUSE`, an older worker is still holding port `3000`. Kill the existing listener first, then restart.
- If provider readiness stays `missing`, confirm the setup script was run with provider envs exported in the local shell before `npm run box:setup`.
- SSRN may remain offline because of anti-bot blocking. This is expected and not a Box boot failure.
