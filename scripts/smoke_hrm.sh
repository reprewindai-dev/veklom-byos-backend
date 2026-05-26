#!/usr/bin/env bash
# Smoke test for HRM + skill registry endpoints
set -euo pipefail

BASE=http://localhost:8088

echo "==> Minting token..."
TOKEN=$(curl -s -X POST "$BASE/api/v1/auth/eval-session" \
  -H 'Content-Type: application/json' \
  -d '{"workspace_id":"hrm-smoke","user_id":"smoketest"}' \
  | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("access_token",""))')

if [ -z "$TOKEN" ]; then
  echo "FAIL: could not mint token"
  exit 1
fi
echo "  token: ${TOKEN:0:20}..."

check() {
  local label="$1"
  local method="$2"
  local url="$3"
  local expected="$4"
  local status
  status=$(curl -s -o /dev/null -w '%{http_code}' -X "$method" \
    -H "Authorization: Bearer $TOKEN" "$url")
  if [ "$status" = "$expected" ]; then
    echo "PASS  [$status] $label"
  else
    echo "FAIL  [$status != $expected] $label"
  fi
}

check "GET /agents/hrm/audit (empty task force)"          GET  "$BASE/api/v1/agents/hrm/audit"                    200
check "GET /agents/hrm/monitors (empty)"                  GET  "$BASE/api/v1/agents/hrm/monitors"                 200
check "GET /agents/hrm/sync/telemetry (empty)"            GET  "$BASE/api/v1/agents/hrm/sync/telemetry"           200
check "GET /agents/hrm/agents/1 (not found)"              GET  "$BASE/api/v1/agents/hrm/agents/1"                 404
check "GET /agents/skills (should have passive-income)"   GET  "$BASE/api/v1/agents/skills"                       200
check "GET /agents/skills/passive-income-engine"          GET  "$BASE/api/v1/agents/skills/passive-income-engine" 200
check "GET /agents/skills/does-not-exist (404)"           GET  "$BASE/api/v1/agents/skills/does-not-exist"        404
check "POST /agents/skills/passive-income-engine/invoke (503)" POST "$BASE/api/v1/agents/skills/passive-income-engine/invoke" 503

echo ""
echo "==> passive-income-engine skill detail:"
curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE/api/v1/agents/skills/passive-income-engine" | python3 -m json.tool | grep -E 'skill_id|is_available|missing_reason|version'
