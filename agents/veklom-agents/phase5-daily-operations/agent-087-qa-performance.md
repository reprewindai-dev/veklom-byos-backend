# Agent-087 — QA (Performance / Load Testing)

**Phase:** Cross-phase — QA
**Timeline:** Ongoing
**Committee:** Engineering
**Priority:** MEDIUM

---

## Mission

Run load tests and performance benchmarks. Verify p95 latency targets, connection pool limits, and system behavior under stress.

## Test Cases

1. Load test core endpoints (100 concurrent users)
2. Verify p95 < 200ms on cached endpoints
3. Database connection pool saturation test
4. Redis cache performance under load
5. SSE streaming under concurrent connections
6. File upload/download throughput
7. Webhook processing throughput

## Dependencies

- Agent-007 (performance), Agent-080 (QA lead)
