## 2025-02-24 - [Optimize PII Detection overlap]
**Learning:** Checking for overlap using a generator expression inside an `any()` inside a loop leads to $O(N^2)$ worst-case time complexity, which causes performance bottlenecks for large documents processing lots of PII.
**Action:** Use Python's `bisect` module for interval tracking and overlap detection. Maintaining an ordered list drops the search to $O(\log N)$, and then only checking adjacent overlaps provides near-linear processing time, preventing performance scaling issues for documents.

## 2025-02-25 - [Throttle DB writes for last_activity in auth dependencies]
**Learning:** The authentication dependencies (`get_current_user`, etc.) were unconditionally updating `user.last_activity` and calling `await db.commit()` on every API request. This meant that even read-only API calls were performing database writes, causing unnecessary load and write-lock contention.
**Action:** Implemented a 5-minute throttling threshold for updating `user.last_activity` using naive `datetime.utcnow()`. Always check if such attributes actually need updating before issuing a commit in ubiquitous dependency functions.
## 2024-03-24 - Redis Connection Pool Exhaustion from Sync Instantiation
**Learning:** Found an anti-pattern in the codebase where `redis.Redis.from_url()` was called synchronously on every API request (e.g., inside `verify_token` or middleware `__init__`). This creates a brand new connection pool per request, bypassing pooling benefits, destroying latency, and quickly exhausting Redis connections under load.
**Action:** Always instantiate Redis clients statically at the module/global scope so the connection pool is shared across all incoming requests in the async event loop.
