## 2025-02-24 - [Optimize PII Detection overlap]
**Learning:** Checking for overlap using a generator expression inside an `any()` inside a loop leads to $O(N^2)$ worst-case time complexity, which causes performance bottlenecks for large documents processing lots of PII.
**Action:** Use Python's `bisect` module for interval tracking and overlap detection. Maintaining an ordered list drops the search to $O(\log N)$, and then only checking adjacent overlaps provides near-linear processing time, preventing performance scaling issues for documents.

## 2025-02-25 - [Throttle DB writes for last_activity in auth dependencies]
**Learning:** The authentication dependencies (`get_current_user`, etc.) were unconditionally updating `user.last_activity` and calling `await db.commit()` on every API request. This meant that even read-only API calls were performing database writes, causing unnecessary load and write-lock contention.
**Action:** Implemented a 5-minute throttling threshold for updating `user.last_activity` using naive `datetime.utcnow()`. Always check if such attributes actually need updating before issuing a commit in ubiquitous dependency functions.

## 2025-02-26 - [Cache expensive unbounded DB aggregations on ExecutionLog]
**Learning:** Several endpoints in `monitoring.py` (`insights_summary`, `insights_savings`, `performance_metrics`) were performing unbounded aggregate queries (e.g., `SUM`, `AVG`, `COUNT`) across the entire `ExecutionLog` table grouped by workspace. Because the AI gateways create `ExecutionLog` rows very frequently, running full-table aggregation queries on every dashboard load causes extreme DB contention and API latency spikes.
**Action:** Wrap dashboard analytics endpoints with a Redis-backed 5-minute cache. Keep Prometheus-style metrics uncached so observability counters and rates are not distorted.

## 2025-02-27 - [Resolve N+1 bottlenecks in HRM telemetry and audit]
**Learning:** Looping through SQL rows and doing aggregate queries (`COUNT`, `ORDER BY DESC LIMIT 1`) inside the loop creates severe $O(N)$ database query inflation, known as the N+1 query problem. In endpoints like `hrm_sync_telemetry`, this causes massive performance degradation on larger agent task forces. Similarly, in `hrm_audit`, firing two unbounded full-group-by table scans (one for `COUNT`, one for `MAX(created_at)`) on `LedgerEvent` doubles the execution overhead.
**Action:** Use a single bulk group-by SQL query and `DISTINCT ON` block (where applicable, due to Postgres DB backing) to fetch metrics up front outside of the loop. Combine queries that iterate over the exact same tables and group definitions (e.g. `func.count(id)` and `func.max(created_at)`). By pre-fetching values into hash maps using `.in_()`, we drop runtime from $O(N)$ back to $O(1)$.
## 2026-08-07 - Avoid full ORM model instantiations for aggregations in SQLAlchemy
**Learning:** In `backend/apps/api/routers/workspace.py`'s `_overview_payload`, we fetched raw ORM records from `ExecLog` in an iterative Python list generation instead of performing the sum operations via the SQL database using group by. This causes an O(N) memory allocation and increases bandwidth utilization especially for larger intervals.
**Action:** Always fetch only the exact columns needed (e.g., `select(ExecLog.provider)`) using tuples/Rows or push counts back to the database (`select(func.count()).group_by(...)`) instead of parsing them locally from `select(Model).scalars().all()`.
## 2025-02-28 - [Consolidate and push conditional aggregations to the DB]
**Learning:** Using `.scalars().all()` to fetch all rows into Python memory merely to count them with `len()` (or evaluate their status) is a severe memory bottleneck. In `backend/core/services/pgl_identity_gate.py`, two separate queries were pulling all `PGLCertificate` rows to independently count `active_attestations` and `active_rollbacks`.
**Action:** Push counts to the database using SQLAlchemy's `func.sum()` and `case()` (e.g., `func.sum(case((Model.status == 'SUCCEEDED', 1), else_=0))`). Combine multiple conditional counts into a single batch query to avoid both N+1 problems and excessive memory usage.
