## 2025-02-24 - [Optimize PII Detection overlap]
**Learning:** Checking for overlap using a generator expression inside an `any()` inside a loop leads to $O(N^2)$ worst-case time complexity, which causes performance bottlenecks for large documents processing lots of PII.
**Action:** Use Python's `bisect` module for interval tracking and overlap detection. Maintaining an ordered list drops the search to $O(\log N)$, and then only checking adjacent overlaps provides near-linear processing time, preventing performance scaling issues for documents.

## 2025-02-25 - [Optimize Smart Router _refine_with_observations]
**Learning:** The smart router executes a `GROUP BY` query on `ExecutionLog` every time an LLM model is selected to gather historical latency and cost metrics. This forces an expensive table scan on the critical AI inference path, slowing down the system over time.
**Action:** Use Redis caching (`redis_cache`) to store the queried metrics (`by_provider`) per workspace for 5 minutes (TTL). This drastically reduces database load while still allowing dynamic adjustments when enough samples exist.
