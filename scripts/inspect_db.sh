#!/bin/bash
DB=byos_ai
USER=byos
echo "=== Tables in $DB ==="
docker exec llwfyzhnft87bz6brddiax1z psql -U $USER -d $DB -c '\dt' 2>&1 | head -100
echo
echo "=== Critical-table presence checks ==="
for tbl in exec_logs repo_risk_gate_runs repo_risk_gate_events users sessions audit_logs accounts agents ledger_events; do
  result=$(docker exec llwfyzhnft87bz6brddiax1z psql -U $USER -d $DB -tAc "SELECT to_regclass('public.$tbl');")
  printf "  %-30s %s\n" "$tbl" "$result"
done
