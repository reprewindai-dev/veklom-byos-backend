#!/bin/bash
TOKEN=$(curl -s -X POST http://localhost:8088/api/v1/auth/eval-session \
  -H 'Content-Type: application/json' -d '{}' | \
  python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

echo "Token: ${TOKEN:0:30}..."

echo "=== Raw inference response ==="
curl -s -X POST http://localhost:8088/api/v1/ai/inference \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"messages":[{"role":"user","content":"say hello"}]}'

echo ""
echo "=== Inference via /ai/complete (existing) ==="
curl -s -X POST http://localhost:8088/api/v1/ai/complete \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"messages":[{"role":"user","content":"say hi in 3 words"}]}' | head -c 300
