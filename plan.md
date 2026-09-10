1. **Identify Performance Bottleneck**: In `backend/apps/api/routers/archive/admin_billing.py`, the `get_reconciliation_summary` endpoint uses `len(findings_result.scalars().all())` and iterates over `dead_letter_result.scalars().all()` to count the number of rows. This loads all rows into Python memory, causing O(N) memory and bandwidth bottlenecks.
2. **Optimize Query**: Modify the queries to use `func.count()` and `.group_by()` in the database layer.
   - For `total_findings`: `select(func.count()).select_from(ReconFinding)`
   - For `status_counts`: `select(WebhookDeadLetter.status, func.count()).select_from(WebhookDeadLetter).group_by(WebhookDeadLetter.status)`
3. **Pre-commit Steps**: Ensure proper testing, verification, review, and reflection are done by calling the `pre_commit_instructions` tool.
4. **Submit PR**: Format the PR title as `⚡ Bolt: [performance improvement]` and provide a description detailing the What, Why, Impact, and Measurement of the optimization.
