## 2025-02-24 - [Optimize PII Detection overlap]
**Learning:** Checking for overlap using a generator expression inside an `any()` inside a loop leads to $O(N^2)$ worst-case time complexity, which causes performance bottlenecks for large documents processing lots of PII.
**Action:** Use Python's `bisect` module for interval tracking and overlap detection. Maintaining an ordered list drops the search to $O(\log N)$, and then only checking adjacent overlaps provides near-linear processing time, preventing performance scaling issues for documents.

## 2025-02-25 - [Throttle DB writes for last_activity in auth dependencies]
**Learning:** The authentication dependencies (`get_current_user`, etc.) were unconditionally updating `user.last_activity` and calling `await db.commit()` on every API request. This meant that even read-only API calls were performing database writes, causing unnecessary load and write-lock contention.
**Action:** Implemented a 5-minute throttling threshold for updating `user.last_activity` using naive `datetime.utcnow()`. Always check if such attributes actually need updating before issuing a commit in ubiquitous dependency functions.

## 2025-02-26 - [Cache expensive unbounded DB aggregations on ExecutionLog]
**Learning:** Several endpoints in `monitoring.py` (`insights_summary`, `insights_savings`, `performance_metrics`) were performing unbounded aggregate queries (e.g., `SUM`, `AVG`, `COUNT`) across the entire `ExecutionLog` table grouped by workspace. Because the AI gateways create `ExecutionLog` rows very frequently, running full-table aggregation queries on every dashboard load causes extreme DB contention and API latency spikes.
**Action:** Wrap dashboard analytics endpoints with a Redis-backed 5-minute cache. Keep Prometheus-style metrics uncached so observability counters and rates are not distorted.
