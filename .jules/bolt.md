## 2025-03-08 - [SQLAlchemy Aggregation over Scalars]
**Learning:** [When dealing with counts on large time-series data like ExecLogs, querying `.scalars().all()` and relying on python iteration is a significant memory and scale bottleneck, often taking O(N) memory.]
**Action:** [Use SQLAlchemy group aggregations like `func.count()` and `func.extract()` along with `group_by()` in queries where possible to let the database handle large aggregations.]

## 2025-03-08 - [Chronological Ordering in Time-Series]
**Learning:** [When calculating time-series data grouped by database hour `func.extract('hour')`, it is very easy to incorrectly iterate through python buckets chronologically forward by indexing 0-23 without accounting for current rolling timestamps, leading to display bugs.]
**Action:** [Ensure python-side buckets for 24-hour lookups are correctly chronologically ordered, typically done using `(now.hour - i) % 24 for i in range(23, -1, -1)`.]
