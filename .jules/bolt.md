## 2025-02-24 - [Optimize PII Detection overlap]
**Learning:** Checking for overlap using a generator expression inside an `any()` inside a loop leads to $O(N^2)$ worst-case time complexity, which causes performance bottlenecks for large documents processing lots of PII.
**Action:** Use Python's `bisect` module for interval tracking and overlap detection. Maintaining an ordered list drops the search to $O(\log N)$, and then only checking adjacent overlaps provides near-linear processing time, preventing performance scaling issues for documents.

## 2025-02-25 - [Throttle DB writes for last_activity in auth dependencies]
**Learning:** The authentication dependencies (`get_current_user`, etc.) were unconditionally updating `user.last_activity` and calling `await db.commit()` on every API request. This meant that even read-only API calls were performing database writes, causing unnecessary load and write-lock contention.
**Action:** Implemented a 5-minute throttling threshold for updating `user.last_activity` using naive `datetime.utcnow()`. Always check if such attributes actually need updating before issuing a commit in ubiquitous dependency functions.
## 2024-05-30 - [Performance bottleneck in JWT verification]
**Learning:** Instantiating a synchronous `redis.Redis` client inside the `verify_token` function for every request causes a massive performance overhead (from ~1.3s down to 0.077s for 100 requests when fixed) and can lead to connection exhaustion. The memory prompt explicitly warned about this: "When using synchronous Redis clients (redis.Redis) in the backend, always instantiate them at the module/global scope rather than per-request".
**Action:** Always verify if database or cache clients are instantiated globally or pooled correctly instead of being created per-request, especially in high-throughput functions like authentication dependencies.
