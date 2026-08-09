#!/bin/bash

# verify_capi_fail_closed.sh
# Automated validation test suite for cAPI Fail-Closed Enforcement.

API_URL=${1:-"http://localhost:8088"}

echo "--- 1. Testing Phase 1: Tampered Payload Signature Rejection ---"
curl -s -X POST "$API_URL/api/v1/capi/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent-core-01",
    "pgl_id": "badsig",
    "target_protocol": "syscall_execute",
    "action": "fs.write",
    "payload": {
      "path": "/etc/hosts",
      "content": "127.0.0.1 illegal-routing.net"
    }
  }' | jq .

echo -e "\n--- 2. Testing Phase 2: Implicit Deny Enforcement ---"
curl -s -X POST "$API_URL/api/v1/capi/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent-core-01",
    "pgl_id": "valid-signature-mock",
    "target_protocol": "mcp",
    "action": "db.drop_tables",
    "payload": {}
  }' | jq .

echo -e "\n--- 3. Testing Phase 4: Budget Depletion Lock ---"
# Note: This expects a real agent with exhausted budget or we simulate it.
# We'll use a payload that triggers a budget error if implemented.
curl -s -X POST "$API_URL/api/v1/capi/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent-core-01",
    "pgl_id": "valid-signature-mock",
    "target_protocol": "model_inference",
    "action": "llm.generate",
    "payload": { "max_tokens": 1000000000 }
  }' | jq .

echo -e "\n--- 4. Testing Governed Terminal Wiring ---"
curl -s -X POST "$API_URL/api/v1/terminal/run" \
  -H "Content-Type: application/json" \
  -d '{
    "intent": "cat /etc/passwd",
    "agent_id": "terminal-agent",
    "pgl_id": "terminal-sig"
  }' | jq .
