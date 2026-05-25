#!/bin/bash
set -e

echo "=== Test 1: No auth (expect 401) ==="
CODE=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8088/api/v1/auth/me)
[ "$CODE" = "401" ] && echo "PASS: $CODE" || echo "FAIL: $CODE"

echo ""
echo "=== Test 2: Demo token (expect 401) ==="
CODE=$(curl -s -o /dev/null -w '%{http_code}' -H 'Authorization: Bearer veklom-demo-token-quantum' http://localhost:8088/api/v1/auth/me)
[ "$CODE" = "401" ] && echo "PASS: $CODE" || echo "FAIL: $CODE"

echo ""
echo "=== Test 3: Eval session (expect 200) ==="
RESP=$(curl -s -X POST http://localhost:8088/api/v1/auth/eval-session \
  -H 'Content-Type: application/json' \
  -d '{"fingerprint":"test-p1"}')
echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print('token:', d['access_token'][:30]+'...'); print('user:', d['user']['full_name']); print('plan:', d['plan'])"

TOKEN=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo ""
echo "=== Test 4: /auth/me with eval token ==="
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8088/api/v1/auth/me | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('full_name:', d['full_name'])
print('workspace:', d['workspace']['name'])
print('role:', d['role'])
print('is_superuser:', d['is_superuser'])
print('capabilities:')
for k, v in d['capabilities'].items():
    print(f'  {k}: {v}')
"

echo ""
echo "=== Test 5: Workspace overview ==="
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8088/api/v1/workspace/overview | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('workspace_id:', d['workspace_id'])
print('plan:', d['plan'])
print('members:', d['members_count'])
print('models_enabled:', d['models_enabled'])
"

echo ""
echo "=== All Phase 1 tests passed ==="
