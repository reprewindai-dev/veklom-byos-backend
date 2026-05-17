# SETUP.md — Local Development Setup

## Prerequisites

- Python 3.11 or higher
- PostgreSQL 14+
- Redis 7+
- (Optional) MinIO for local S3-compatible storage

---

## 1. Clone and Enter

```bash
git clone https://github.com/reprewindai-dev/veklom-byos-backend
cd veklom-byos-backend
```

## 2. Create Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## 4. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` — minimum required for local dev:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/veklom
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=your-local-dev-secret-change-this
JWT_ALGORITHM=HS256
APP_ENV=development
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

For AI features, add:
```env
OPENAI_API_KEY=sk-...
```

For billing features, add:
```env
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

## 5. Create Database

```bash
createdb veklom
```

## 6. Run Migrations

```bash
alembic upgrade head
```

## 7. Start the Server

```bash
uvicorn backend.apps.api.main:app --reload --port 8000
```

## 8. Verify

```bash
curl http://localhost:8000/api/v1/health
# Expected: {"status": "ok", ...}
```

Swagger UI: http://localhost:8000/docs  
ReDoc: http://localhost:8000/redoc

---

## Running Tests

```bash
pytest backend/tests/ -v
```

For a specific category:

```bash
pytest backend/tests/test_auth.py -v
pytest backend/tests/test_health.py -v
pytest backend/tests/test_exec.py -v
```

---

## Common Issues

| Issue | Fix |
|-------|-----|
| `asyncpg` not found | `pip install asyncpg` |
| Migration fails | Check `DATABASE_URL` format — must use `asyncpg` driver |
| Redis connection refused | Start Redis: `redis-server` |
| JWT errors on startup | Ensure `JWT_SECRET_KEY` is set in `.env` |
| Import errors on `backend.apps.api.main` | Run from repo root, not from `backend/` |
