## 2025-02-24 - [Optimize PII Detection overlap]
**Learning:** Checking for overlap using a generator expression inside an `any()` inside a loop leads to $O(N^2)$ worst-case time complexity, which causes performance bottlenecks for large documents processing lots of PII.
**Action:** Use Python's `bisect` module for interval tracking and overlap detection. Maintaining an ordered list drops the search to $O(\log N)$, and then only checking adjacent overlaps provides near-linear processing time, preventing performance scaling issues for documents.

## 2025-02-25 - [Throttle DB writes for last_activity in auth dependencies]
**Learning:** The authentication dependencies (`get_current_user`, etc.) were unconditionally updating `user.last_activity` and calling `await db.commit()` on every API request. This meant that even read-only API calls were performing database writes, causing unnecessary load and write-lock contention.
**Action:** Implemented a 5-minute throttling threshold for updating `user.last_activity` using naive `datetime.utcnow()`. Always check if such attributes actually need updating before issuing a commit in ubiquitous dependency functions.
## 2024-07-12 - Reusing Synchronous Redis Clients in FastAPI Dependencies
**Learning:** Re-instantiating `redis.Redis.from_url(...)` inside a highly called function like `verify_token` (used as a FastAPI dependency) can cause severe connection pool thrashing and overhead, as a new connection is created and immediately discarded on every single authenticated request.
**Action:** When using synchronous Redis clients (`redis.Redis`), always instantiate them at the module/global scope. This ensures the connection pool is shared across requests, significantly improving performance on hot paths.
