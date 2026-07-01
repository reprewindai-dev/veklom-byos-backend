## 2025-02-24 - [Optimize PII Detection overlap]
**Learning:** Checking for overlap using a generator expression inside an `any()` inside a loop leads to $O(N^2)$ worst-case time complexity, which causes performance bottlenecks for large documents processing lots of PII.
**Action:** Use Python's `bisect` module for interval tracking and overlap detection. Maintaining an ordered list drops the search to $O(\log N)$, and then only checking adjacent overlaps provides near-linear processing time, preventing performance scaling issues for documents.
## 2026-07-01 - [Throttling frequent DB writes in Auth Middleware]
**Learning:** Updating a timestamp field like `last_activity` in the database on every authenticated API request causes unnecessary write-lock contention and slows down read-heavy routes in a FastAPI/SQLAlchemy application.
**Action:** Throttle such updates by checking the time elapsed since the last update (e.g. 5 minutes) before committing to the database.
