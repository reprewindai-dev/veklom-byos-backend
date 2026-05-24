---
description: Veklom BYOS Backend Development
---

# Veklom BYOS Backend Development

This skill provides guidance for developing the Veklom BYOS Backend.

## Project Structure

```
veklom-byos-backend/
├── backend/
│   ├── apps/api/          # FastAPI routers
│   ├── core/              # Config, auth, DB engine
│   ├── db/                # SQLAlchemy models, Alembic migrations
│   ├── scripts/           # Utility scripts
│   └── ops/               # Operational scripts
├── frontend/              # Static files (workspace, command-center)
├── irongrid/dist/         # PYO3 IronGrid distribution
├── sdk/                   # Python and TypeScript SDKs
├── cloudflare/            # Cloudflare Worker
└── .github/workflows/     # CI/CD workflows
```

## Development Workflow

1. **Make changes to backend code**
   - Edit files in `backend/apps/api/`, `backend/core/`, or `backend/db/`

2. **Test locally**
   ```bash
   uvicorn backend.apps.api.main:app --reload
   ```

3. **Create database migrations** (if schema changes)
   ```bash
   cd backend/db/migrations
   alembic revision --autogenerate -m "description"
   alembic upgrade head
   ```

4. **Commit and push**
   ```bash
   git add -A
   git commit -m "description"
   git push origin main
   ```

5. **Deploy to server** (automatic via GitHub Actions or manual)
   ```bash
   ssh -i ~/.ssh/veklom-deploy root@5.78.135.11
   cd /data/coolify/applications/n13gp1nhrcdp0hvazvbnlxru
   git pull origin main
   docker build -t veklom-local:latest .
   docker stop n13gp1nhrcdp0hvazvbnlxru-213557155694
   docker rm n13gp1nhrcdp0hvazvbnlxru-213557155694
   docker run -d --name n13gp1nhrcdp0hvazvbnlxru-213557155694 --network coolify --env-file /data/coolify/applications/n13gp1nhrcdp0hvazvbnlxru/.env --restart unless-stopped -p 8088:8088 veklom-local:latest
   ```

6. **Verify deployment**
   ```bash
   curl -s http://localhost:8088/health
   ```

## Key Concepts

- **Tenant isolation**: All queries must include `workspace_id` filter
- **Role-based access**: Use `get_current_user` dependency for auth
- **Audit logging**: All actions should be logged to AuditLog model
- **Provider routing**: Ollama first for all tenants, owner keys for admin
- **API base URL**: `/api/v1`

## Common Tasks

### Add a new router endpoint

1. Create or edit file in `backend/apps/api/routers/`
2. Add route with `@router.get/post/patch/delete()`
3. Include `user=Depends(get_current_user)` for auth
4. Include `db: AsyncSession = Depends(get_db)` for DB access
5. Register router in `backend/apps/api/main.py`

### Add a new database model

1. Create file in `backend/db/models/`
2. Inherit from `Base` with proper columns
3. Add to `backend/db/models/__init__.py`
4. Create migration: `alembic revision --autogenerate -m "add model"`
5. Run migration: `alembic upgrade head`

## Deployment Environment

- **Server**: Hetzner VPS 5.78.135.11
- **Coolify app ID**: n13gp1nhrcdp0hvazvbnlxru
- **Container name**: n13gp1nhrcdp0hvazvbnlxru-213557155694
- **Internal port**: 8088
- **Proxy**: Cloudflare (443 → 8088)
