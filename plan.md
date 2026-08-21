1. **Optimize `monitoring_health` in `backend/apps/api/routers/workspace.py`**:
   - Currently, it executes three separate `await db.scalar(select(func.count())...)` queries for recent executions, errors, and security events.
   - Refactor these into a single batched query using conditional aggregation (`func.sum(case(...))`), saving two database roundtrips.

2. **Optimize `monitoring_metrics` in `backend/apps/api/routers/workspace.py`**:
   - Currently, it executes four separate `await db.scalar(...)` queries for `total_execs`, `total_tokens`, `total_cost`, and `avg_latency`.
   - Refactor these into a single batched query with multiple aggregations, saving three database roundtrips.

3. **Pre-commit checks**:
   - Complete pre-commit steps to ensure proper testing, verification, review, and reflection are done before submitting.

4. **Submit PR**:
   - Create the PR with a descriptive commit message following the required format.
