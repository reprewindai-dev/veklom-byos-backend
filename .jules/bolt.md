## 2024-05-24 - Batching boolean counts in SQLAlchemy
**Learning:** We can replace multiple scalar queries filtering by different statuses (e.g., counting executions and counting errors separately) with a single query using conditional aggregations via `func.sum(case((Model.status == "error", 1), else_=0))`.
**Action:** Next time I need to count multiple sub-conditions of the same base query (like different statuses within the last 5 minutes), batch them into a single `db.execute(select(...))` using `case` rather than issuing N separate `db.scalar(...)` calls.
