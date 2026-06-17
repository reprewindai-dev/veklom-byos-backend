# Agent-007 — PERFORMANCE ENGINEER

**Phase:** 1 — Complete the Core Product
**Timeline:** Days 1–4
**Committee:** Engineering
**Priority:** MEDIUM
**Server:** 5.78.135.11 | **Repo:** veklom-byos-backend

---

## Mission

Optimize backend performance. Target: sub-200ms p95 latency on core API paths.

## First Actions

```bash
# Benchmark current state:
curl -w "@curl-format.txt" -s https://veklom.com/api/v1/workspace
curl -w "@curl-format.txt" -s https://veklom.com/api/v1/ai/models

# Check DB indexes:
ssh -i ~/.ssh/veklom-deploy root@5.78.135.11
docker exec -it llwfyzhnft87bz6brddiax1z psql -U postgres veklom \
  -c "SELECT tablename, indexname FROM pg_indexes WHERE schemaname='public';"

# Check Redis:
cat backend/core/config.py  # find Redis config
cat backend/apps/api/main.py  # find cache middleware
```

## Tasks

### Task 1: Redis Caching on Hot GET Endpoints
```python
# File: backend/core/cache.py (create if missing)
from redis import asyncio as aioredis
import json, hashlib

async def cache_response(key: str, ttl: int = 300):
    """Cache decorator for GET endpoints"""

# Apply to:
# GET /api/v1/ai/models           → TTL: 3600s (models don't change often)
# GET /api/v1/subscriptions/plans → TTL: 3600s
# GET /api/v1/workspace           → TTL: 30s
# GET /api/v1/audit/logs          → TTL: 60s
```

### Task 2: Database Index Audit
```sql
-- Add missing indexes (check each table's query patterns):
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_workspace 
  ON audit_logs(workspace_id, created_at DESC);
  
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_api_keys_workspace
  ON api_keys(workspace_id) WHERE revoked_at IS NULL;
  
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_user
  ON sessions(user_id, expires_at);
```

### Task 3: N+1 Query Elimination
```python
# Audit every endpoint that returns lists:
# Must use joinedload() or selectinload() — not lazy loading
# Find patterns like:
#   for item in items:
#       item.user.name  ← this is N+1
```

### Task 4: Response Compression
```python
# File: backend/apps/api/main.py
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

## Success Metrics
| Metric | Target |
|---|---|
| p95 latency core endpoints | < 200ms |
| Cache hit rate on hot endpoints | > 80% |
| DB query time p95 | < 50ms |
