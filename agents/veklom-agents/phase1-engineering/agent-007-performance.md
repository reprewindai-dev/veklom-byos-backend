# Agent-007 — PERFORMANCE ENGINEER

**Phase:** 1 — Complete the Core Product
**Timeline:** Days 1–4
**Committee:** Engineering
**Priority:** MEDIUM

---

## Mission

Optimize backend performance: add Redis caching on hot GET endpoints, audit database indexes, profile slow queries, and ensure sub-200ms p95 latency on core API paths.

## Current State

- Redis is live and configured — ✅
- No Redis caching on GET endpoints
- No DB index audit done
- No query profiling
- Middleware stack is 14 layers deep (potential latency concern)

## Tasks

1. **Redis Caching** — add cache layer to hot endpoints:
   - `GET /marketplace/listings` (5-min TTL)
   - `GET /pipelines` (2-min TTL)
   - `GET /workspace/models` (5-min TTL)
   - `GET /monitoring/overview` (30-sec TTL)
   - Cache invalidation on writes
2. **Database Index Audit**:
   - Check indexes on `user_id`, `workspace_id`, `created_at` across all tables
   - Add composite indexes for common query patterns
   - Add indexes on foreign keys used in JOINs
3. **Query Profiling**:
   - Enable `EXPLAIN ANALYZE` on slow queries
   - Identify N+1 query patterns
   - Add eager loading where needed
4. **Middleware Optimization**:
   - Profile 14-layer middleware stack latency
   - Identify bottleneck middleware
   - Add `FastPathMiddleware` bypass for public/health endpoints
5. **Connection Pooling**:
   - Verify PostgreSQL connection pool settings
   - Verify Redis connection pool settings
   - Add connection health checks

## Success Metrics

| Metric | Target |
|---|---|
| p95 latency (core endpoints) | < 200ms |
| Redis cache hit rate | > 80% |
| Database indexes added | As needed |
| N+1 queries eliminated | All |
| Middleware overhead | < 10ms total |

## Daily Checklist

- [ ] Day 1: Redis caching on top 4 endpoints
- [ ] Day 2: DB index audit + add missing indexes
- [ ] Day 3: Query profiling + N+1 fixes
- [ ] Day 4: Middleware optimization + benchmarks + PR

## Dependencies

- Agent-000 (MASTER_STATE.md)
- Agent-008 (security considerations for caching)

## Playbook

```
Repo: byosbackened
Branch: main
Read MASTER_STATE.md first
Focus: backend/apps/api/routers/ (caching) + database migrations (indexes)
Benchmark: wrk or hey against staging endpoints
```
