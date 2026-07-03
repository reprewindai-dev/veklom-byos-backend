## 2025-02-24 - [Optimize PII Detection overlap]
**Learning:** Checking for overlap using a generator expression inside an `any()` inside a loop leads to $O(N^2)$ worst-case time complexity, which causes performance bottlenecks for large documents processing lots of PII.
**Action:** Use Python's `bisect` module for interval tracking and overlap detection. Maintaining an ordered list drops the search to $O(\log N)$, and then only checking adjacent overlaps provides near-linear processing time, preventing performance scaling issues for documents.

## 2025-03-05 - [Throttle last_activity updates in read-heavy auth dependencies]
**Learning:** Updating a user record's `last_activity` indiscriminately inside `get_current_user` (and other core auth dependencies) triggers database writes and transaction commits on every single API request, which creates a massive DB bottleneck via write-lock contention.
**Action:** Throttle these updates in dependencies by checking `(now - user.last_activity).total_seconds() > 300` so the write only happens once every 5 minutes per user.
