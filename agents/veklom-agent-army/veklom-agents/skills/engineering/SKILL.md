---
name: veklom-engineering
description: Backend engineering for Veklom BYOS. Load when writing Python/FastAPI code, database migrations, API endpoints, tests, or deployments on the Hetzner server.
metadata:
  version: 1.0.0
  committee: engineering
  authority_bundle: auth_engineering_v1
  linked_files:
    - api-reference.md
    - deploy-runbook.md
    - payments-guide.md
    - db-schema.md
---

# Veklom Engineering Skill

## Repository
- GitHub: reprewindai-dev/veklom-byos-backend
- Server: root@5.78.135.11 (SSH key: ~/.ssh/veklom-deploy)
- Backend: FastAPI at port 8088, entry: backend/apps/api/main.py
- 43 routers in backend/apps/api/routers/
- Stack: Python/FastAPI + PostgreSQL + Redis + Docker + Coolify

## Live Site
- https://veklom.com
- https://veklom.com/control-plane-next/dashboard/

## Before Writing Code
```bash
# Always read first:
cat backend/apps/api/main.py
cat backend/apps/api/routers/[relevant_router].py
cat backend/db/models.py
cat .env.example  # understand env var names
```

## Branch Policy
- Branch: feature/agent-XXX-description
- NEVER push directly to main
- PR → Agent-080 (QA Lead) reviews → merge

## Deploy After Every Merge
See deploy-runbook.md

## API Base
All routes: /api/v1/
Auth: Authorization: Bearer <token>
Key endpoints: /exec, /auth/, /wallet/, /marketplace/, /compliance/, /audit/

## When to Load Sub-Files
- Writing API endpoints → load api-reference.md
- Deploying to server → load deploy-runbook.md
- Stripe/payments → load payments-guide.md
- Database migrations → load db-schema.md
