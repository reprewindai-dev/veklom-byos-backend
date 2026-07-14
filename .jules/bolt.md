## 2025-02-24 - [Optimize PII Detection overlap]
**Learning:** Checking for overlap using a generator expression inside an `any()` inside a loop leads to $O(N^2)$ worst-case time complexity, which causes performance bottlenecks for large documents processing lots of PII.
**Action:** Use Python's `bisect` module for interval tracking and overlap detection. Maintaining an ordered list drops the search to $O(\log N)$, and then only checking adjacent overlaps provides near-linear processing time, preventing performance scaling issues for documents.
