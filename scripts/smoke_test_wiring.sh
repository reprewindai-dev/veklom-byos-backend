#!/bin/bash
# Smoke-test every endpoint added by the WIRING_MATRIX rollout.
# Hits the live backend through Traefik on the Hetzner VPS.
#
# Run on the server with:
#   bash /tmp/smoke_test_wiring.sh
#
# Output is a status table.  401/403 are EXPECTED for auth-gated routes when
# called without a JWT.  Anything else (404/500/connection refused) is a real
# failure.

BASE="http://localhost:80"

passes=0
fails=0
unauthorized=0

check() {
  local method="$1"
  local path="$2"
  local expect="$3"   # comma-list of acceptable codes
  local body="$4"

  if [ "$method" = "POST" ] && [ -n "$body" ]; then
    code=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" -d "$body" "$BASE$path")
  elif [ "$method" = "POST" ]; then
    code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE$path")
  else
    code=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" "$BASE$path")
  fi

  case ",$expect," in
    *,$code,*)
      printf "  PASS  %-7s %-55s -> %s\n" "$method" "$path" "$code"
      passes=$((passes + 1))
      if [ "$code" = "401" ] || [ "$code" = "403" ]; then
        unauthorized=$((unauthorized + 1))
      fi
      ;;
    *)
      printf "  FAIL  %-7s %-55s -> %s (expected one of %s)\n" "$method" "$path" "$code" "$expect"
      fails=$((fails + 1))
      ;;
  esac
}

echo "=== Group A: Command Center aliases (auth required) ==="
check GET  /api/v1/command-center/overview            401,403,200
check GET  /api/v1/command-center/audit-log           401,403,200
check GET  /api/v1/command-center/users               401,403,200
check GET  /api/v1/command-center/users/abc           401,403,404
check GET  /api/v1/command-center/users/abc/activity  401,403,404
check GET  /api/v1/command-center/users/abc/sessions  401,403,404
check GET  /api/v1/command-center/operations/health   401,403,200
check GET  /api/v1/command-center/operations/alerts   401,403,200
check GET  /api/v1/command-center/operations/errors   200
check GET  /api/v1/command-center/business/billing    401,403,200
check GET  /api/v1/command-center/activity-feed       401,403,200

echo
echo "=== Group B: Command Center new routes ==="
check GET  /api/v1/command-center/users/summary       401,403,200
check GET  /api/v1/command-center/users/online        401,403,200
check GET  /api/v1/command-center/users/recent        401,403,200
check GET  /api/v1/command-center/live-users          401,403,200
check GET  /api/v1/command-center/sessions            401,403,200
check GET  /api/v1/command-center/funnels             401,403,200
check GET  /api/v1/command-center/terminals/quantum   401,403,200
check GET  /api/v1/command-center/terminals/veklom    401,403,200

echo
echo "=== Marketplace categories ==="
check GET  /api/v1/marketplace/categories             401,403,200

echo
echo "=== GPC stats ==="
check GET  /api/v1/gpc/stats                          401,403,200

echo
echo "=== Repo Risk Gate ==="
check POST /api/v1/repo-risk-gate/runs                401,403,422 '{"repo_url":"https://github.com/octocat/Hello-World"}'
check GET  /api/v1/repo-risk-gate/runs                401,403,200
check GET  /api/v1/repo-risk-gate/runs/nonexistent           401,403,404
check GET  /api/v1/repo-risk-gate/runs/nonexistent/events    401,403,404
check POST /api/v1/repo-risk-gate/runs/nonexistent/decision  401,403,404,422
check GET  /api/v1/repo-risk-gate/runs/nonexistent/ledger    401,403,404

echo
echo "=== Agent Workforce ==="
check GET  /api/v1/agents/registry                    401,403,200
check GET  /api/v1/agents/registry/1                  401,403,404
check GET  /api/v1/agents/fleet                       401,403,200
check GET  /api/v1/agents/runs                        401,403,200
check POST /api/v1/agents/runs                        401,403,422
check GET  /api/v1/agents/decision-frames             401,403,200
check GET  /api/v1/agents/signals                     401,403,200
check GET  /api/v1/agents/violations                  401,403,200
check GET  /api/v1/agents/evidence                    401,403,200
check GET  /api/v1/agents/monthly-report              401,403,200
check GET  /api/v1/agents/guardrails                  401,403,200

echo
echo "=== Existing routes sanity (must still work) ==="
check GET  /health                                    200
check GET  /api/v1/subscriptions/plans                200
check GET  /openapi.json                              200

echo
echo "=== Summary ==="
echo "Total: $((passes + fails))   PASS: $passes (auth-gated $unauthorized)   FAIL: $fails"
exit $fails
