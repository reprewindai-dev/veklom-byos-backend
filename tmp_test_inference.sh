#!/bin/bash
# Test eval-session + /ai/inference routing
TOKEN=$(curl -s -X POST http://localhost:8088/api/v1/auth/eval-session \
  -H 'Content-Type: application/json' -d '{}' | \
  python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

echo "=== Token acquired ==="

RESP=$(curl -s -X POST http://localhost:8088/api/v1/ai/inference \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"messages":[{"role":"user","content":"say hello in 3 words"}]}')

echo "=== Inference response ==="
echo "$RESP" | python3 -c '
import sys,json
d=json.load(sys.stdin)
print("provider:", d.get("provider"))
print("tier:", d.get("tier"))
print("cache_hit:", d.get("cache_hit"))
print("model:", d.get("model"))
print("response:", (d.get("response_text") or "")[:120])
'

echo ""
echo "=== Chat with memory ==="
RESP2=$(curl -s -X POST http://localhost:8088/api/v1/ai/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"messages":[{"role":"user","content":"remember: my name is Veklom admin"}],"session_id":"test-session-1"}')

echo "$RESP2" | python3 -c '
import sys,json
d=json.load(sys.stdin)
print("provider:", d.get("provider"))
print("memory:", d.get("memory"))
print("response:", (d.get("response_text") or "")[:120])
'
