#!/bin/bash
# Authenticated smoke test against new wiring.
# Mints a JWT via /auth/eval-session, then calls every new auth-gated route.

set -e

BASE="http://localhost:8088"
TOKEN=$(curl -s -X POST -H "Content-Type: application/json" -d '{}' "$BASE/api/v1/auth/eval-session" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

if [ -z "$TOKEN" ]; then
  echo "FAILED to obtain eval-session JWT"
  exit 1
fi
echo "Got JWT (length ${#TOKEN}). First 24 chars: ${TOKEN:0:24}..."
echo

passes=0
fails=0

call() {
  local method="$1"
  local path="$2"
  local expect="$3"
  local body="$4"
  local args=(-s -o /tmp/resp -w "%{http_code}" -X "$method" -H "Authorization: Bearer $TOKEN")
  if [ -n "$body" ]; then
    args+=(-H "Content-Type: application/json" -d "$body")
  fi
  code=$(curl "${args[@]}" "$BASE$path")
  case ",$expect," in
    *,$code,*)
      printf "  PASS  %-7s %-55s -> %s\n" "$method" "$path" "$code"
      passes=$((passes + 1))
      ;;
    *)
      printf "  FAIL  %-7s %-55s -> %s (expected %s)\n" "$method" "$path" "$code" "$expect"
      head -c 200 /tmp/resp; echo
      fails=$((fails + 1))
      ;;
  esac
}

echo "=== Command Center authenticated ==="
call GET  /api/v1/command-center/overview            200
call GET  /api/v1/command-center/audit-log           200
call GET  /api/v1/command-center/operations/health   200
call GET  /api/v1/command-center/operations/alerts   200
call GET  /api/v1/command-center/operations/errors   200
call GET  /api/v1/command-center/business/billing    200
call GET  /api/v1/command-center/activity-feed       200
call GET  /api/v1/command-center/terminals/quantum   200
call GET  /api/v1/command-center/terminals/veklom    200
# Admin-required routes — eval session is USER role, expect 403
call GET  /api/v1/command-center/users               403
call GET  /api/v1/command-center/users/summary       403
call GET  /api/v1/command-center/users/online        403
call GET  /api/v1/command-center/funnels             403
call GET  /api/v1/command-center/sessions            403

echo
echo "=== Marketplace categories ==="
call GET  /api/v1/marketplace/categories             200

echo
echo "=== GPC stats ==="
call GET  /api/v1/gpc/stats                          200

echo
echo "=== Repo Risk Gate (real run lifecycle) ==="
RUN_JSON=$(curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"repo_url":"https://github.com/octocat/Hello-World"}' "$BASE/api/v1/repo-risk-gate/runs")
RUN_ID=$(echo "$RUN_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "  Created run $RUN_ID"
echo "  Status from run: $(echo "$RUN_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['status'])")"
call GET  /api/v1/repo-risk-gate/runs                200
call GET  /api/v1/repo-risk-gate/runs/$RUN_ID        200
call GET  /api/v1/repo-risk-gate/runs/$RUN_ID/events 200
call POST /api/v1/repo-risk-gate/runs/$RUN_ID/decision 200 '{"decision":"approve","reason":"smoke test"}'
call GET  /api/v1/repo-risk-gate/runs/$RUN_ID/ledger 200
echo "  Ledger sample:"
curl -s -H "Authorization: Bearer $TOKEN" "$BASE/api/v1/repo-risk-gate/runs/$RUN_ID/ledger" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'    chain_intact={d[\"chain_intact\"]}  events={d[\"event_count\"]}  head_hash={d[\"head_hash\"][:16]}...')
for ev in d['events']:
    print(f'    - {ev[\"type\"]:30}  hash={ev[\"event_hash\"][:12]}...')
"

echo
echo "=== Agent Workforce (eval session has no account, expect empty-state JSON not 500) ==="
call GET  /api/v1/agents/registry                    200
call GET  /api/v1/agents/fleet                       200
call GET  /api/v1/agents/runs                        200
call GET  /api/v1/agents/decision-frames             200
call GET  /api/v1/agents/signals                     200
call GET  /api/v1/agents/violations                  200
call GET  /api/v1/agents/evidence                    200
call GET  /api/v1/agents/monthly-report              200
call GET  /api/v1/agents/guardrails                  200

echo
echo "=== Sanity: previously-broken endpoints from Phase 2 trace ==="
call GET  /api/v1/workspace/overview/live            200
call GET  /api/v1/workspace/overview                 200
call GET  /api/v1/auth/me                            200
call POST /api/v1/auth/eval-session                  200

echo
echo "=== Summary ==="
echo "Total: $((passes + fails))   PASS: $passes   FAIL: $fails"
exit $fails
