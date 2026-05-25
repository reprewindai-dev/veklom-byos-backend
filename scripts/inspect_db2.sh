#!/bin/bash
docker exec llwfyzhnft87bz6brddiax1z psql -U byos -d byos_ai -c "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('exec_logs','users','audit_logs','accounts','agents','ledger_events','workspaces','sessions','repo_risk_gate_runs','repo_risk_gate_events') ORDER BY table_name;"
echo
echo "=== count tables we expect (out of ~30 Veklom models) ==="
docker exec llwfyzhnft87bz6brddiax1z psql -U byos -d byos_ai -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name = ANY(ARRAY['exec_logs','users','audit_logs','accounts','agents','ledger_events','workspaces','sessions','repo_risk_gate_runs','repo_risk_gate_events','marketplace_listings','pipelines','playground_sessions','wallet_transactions','provider_keys','security_events','compliance_checks','api_keys','vendors','deployments','genome_versions','birth_certificates','lineage_edges','workspace_members','model_configs','assets','plugins','budget_rules','subscriptions','invoices']);"
echo
echo "=== test app->db connectivity from app container ==="
docker exec n13gp1nhrcdp0hvazvbnlxru-213557155694 python3 -c "
import asyncio, os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
async def main():
    url = os.environ['DATABASE_URL']
    print('URL=', url)
    e = create_async_engine(url)
    async with e.begin() as c:
        r = await c.execute(text(\"SELECT current_database(), current_user\"))
        print('  connected_to=', r.fetchone())
        r = await c.execute(text(\"SELECT count(*) FROM information_schema.tables WHERE table_schema='public'\"))
        print('  total_public_tables=', r.fetchone())
        r = await c.execute(text(\"SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='exec_logs'\"))
        print('  exec_logs_present=', r.fetchone())
asyncio.run(main())
" 2>&1 | head -20
