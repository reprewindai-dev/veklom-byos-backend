# AGENT HANDSHAKE BRIEF V2 — Read This Before Anything Else

**Every agent in this workforce MUST read this file before touching a single file.**

---

## Live Production Environment

| Item | Value |
|---|---|
| **Live URL** | https://veklom.com |
| **Workspace** | https://veklom.com/control-plane-next/dashboard/ |
| **Server** | Hetzner VPS `5.78.135.11` |
| **Backend port** | `8088` |
| **Proxy** | Cloudflare → Traefik → Docker container |
| **Container** | `n13gp1nhrcdp0hvazvbnlxru-213557155694` |
| **Source dir** | `/data/coolify/applications/n13gp1nhrcdp0hvazvbnlxru/` |

## SSH Access

```bash
ssh -i ~/.ssh/veklom-deploy root@5.78.135.11
```

Key location: `C:\Users\antho\.ssh\veklom-deploy` — key-only auth, no password.

## Deploy Protocol (MANDATORY for all agents making code changes)

```bash
# Step 1: Push to GitHub
git add -A && git commit -m "agent-XXX: description" && git push origin main

# Step 2: SSH and rebuild
ssh -i ~/.ssh/veklom-deploy root@5.78.135.11
cd /data/coolify/applications/n13gp1nhrcdp0hvazvbnlxru
git pull origin main
docker build -t veklom-local:latest .
docker stop n13gp1nhrcdp0hvazvbnlxru-213557155694 || true
docker rm n13gp1nhrcdp0hvazvbnlxru-213557155694 || true
docker run -d \
  --name n13gp1nhrcdp0hvazvbnlxru-213557155694 \
  --network coolify \
  --env-file /data/coolify/applications/n13gp1nhrcdp0hvazvbnlxru/.env \
  --restart unless-stopped \
  -p 8088:8088 \
  veklom-local:latest

# Step 3: Verify
curl -s http://localhost:8088/health
```

## Backend Architecture

```
backend/apps/api/
├── main.py              ← FastAPI app entry — DO NOT break middleware here
├── routers/             ← 43 router modules — your primary work area
├── core/                ← Config, auth, DB engine, security — careful here
├── db/                  ← SQLAlchemy models + Alembic migrations
├── license/             ← License guard — do not modify
└── tests/               ← pytest suite — always run before PR
```

## Frontend — ABSOLUTE RULES

1. **Only valid frontend:** `frontend/sovereign-control-node/`
2. **DO NOT** touch `frontend/static/workspace`, `frontend/veklom-workspace`, or any other frontend dir
3. This is a prebuilt Next.js static export — do NOT run `npm install` or `npm run build` in this repo
4. Backend routes `/workspace`, `/login`, `/signup` redirect to `/control-plane-next/`

## API Base

All routes: `https://veklom.com/api/v1/`
All routes require `Authorization: Bearer <token>` unless marked public.

Key endpoints your work touches:
- Auth: `/api/v1/auth/`
- AI Execution: `/api/v1/exec`, `/api/v1/ai/`
- Billing: `/api/v1/wallet/`, `/api/v1/subscriptions/`
- Marketplace: `/api/v1/marketplace/`
- Compliance: `/api/v1/compliance/`, `/api/v1/audit/`
- Security: `/api/v1/security/`, `/api/v1/kill-switch/`
- Routing: `/api/v1/routing/`, `/api/v1/autonomous/`
- UACP: `/api/v1/internal/uacp/`

## Infrastructure Stack

- **PostgreSQL:** Docker container `llwfyzhnft87bz6brddiax1z` inside `coolify` network
- **Redis:** Docker container `v8vf3lw73fx9lw9xmbq1tvo5` inside `coolify` network
- **Traefik config:** `/data/coolify/proxy/dynamic/veklom.yaml`
- **Env file:** `/data/coolify/applications/n13gp1nhrcdp0hvazvbnlxru/.env`

## Branch Policy

- **NEVER push directly to `main`** unless you are running a hotfix with Agent-000 approval
- Work in `feature/agent-XXX-description` branches
- PR → review → merge

## PROGRESS.md Updates (MANDATORY)

After every completed task:
```markdown
## Agent-XXX Update — [Date]
- Task: [what you did]
- Files changed: [list]
- Status: COMPLETE | IN PROGRESS | BLOCKED
- Next: [what comes next]
```

## Guardrail Enforcement

All agents are subject to GUARDRAILS.md.
Violations are tracked by Agent-079 (Compliance Officer).
Do not push secrets, do not force push, do not skip pre-commit hooks.

---

**You are building the sovereign AI infrastructure the world hasn't seen yet.**
**Read your mission file. Execute. Ship.**
