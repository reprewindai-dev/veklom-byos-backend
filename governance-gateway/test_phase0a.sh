#!/bin/bash

# Phase 0A Governance Gateway Test Script
# Tests identity verification, policy checking, and audit logging

echo "🚀 Testing Phase 0A Governance Gateway"

# Configuration
GATEWAY_URL="http://localhost:8080"
BACKEND_URL="http://localhost:8000"

echo "📍 Gateway URL: $GATEWAY_URL"
echo "📍 Backend URL: $BACKEND_URL"

# Test 1: Health Check
echo ""
echo "🔍 Test 1: Health Check"
curl -s "$GATEWAY_URL/health" | jq '.'

# Test 2: MCP Ping
echo ""
echo "🔍 Test 2: MCP Ping"
curl -s -X POST "$GATEWAY_URL/mcp" \
  -H "Content-Type: application/json" \
  -d '{"method":"ping","params":{},"id":1}' | jq '.'

# Test 3: List MCP Tools
echo ""
echo "🔍 Test 3: List MCP Tools"
curl -s -X POST "$GATEWAY_URL/mcp" \
  -H "Content-Type: application/json" \
  -d '{"method":"list_tools","params":{},"id":2}' | jq '.'

# Test 4: Execute Action with Valid Identity (should be allowed for test data)
echo ""
echo "🔍 Test 4: Execute Action - Valid Identity"
curl -s -X POST "$GATEWAY_URL/mcp" \
  -H "Content-Type: application/json" \
  -d '{
    "method": "execute_action",
    "params": {
      "agent_id": "agent_12345",
      "certificate_id": "cert_abc123",
      "latest_genome_hash": "sha256:abc123def456",
      "tool_name": "web_search",
      "workspace_id": "workspace_67890",
      "action_context": {"query": "test search"}
    },
    "id": 3
  }' | jq '.'

# Test 5: Execute Action with Invalid Identity (should be denied)
echo ""
echo "🔍 Test 5: Execute Action - Invalid Identity"
curl -s -X POST "$GATEWAY_URL/mcp" \
  -H "Content-Type: application/json" \
  -d '{
    "method": "execute_action",
    "params": {
      "agent_id": "agent_invalid",
      "certificate_id": "cert_invalid",
      "latest_genome_hash": "sha256:invalid",
      "tool_name": "web_search",
      "workspace_id": "workspace_67890"
    },
    "id": 4
  }' | jq '.'

# Test 6: Invalid Method (should return error)
echo ""
echo "🔍 Test 6: Invalid Method"
curl -s -X POST "$GATEWAY_URL/mcp" \
  -H "Content-Type: application/json" \
  -d '{"method":"invalid_method","params":{},"id":5}' | jq '.'

echo ""
echo "✅ Phase 0A Testing Complete"
echo ""
echo "📋 Expected Results:"
echo "- Health check should return 'healthy' status"
echo "- MCP ping should return 'pong'"
echo "- List tools should show execute_action and ping"
echo "- Valid identity should be allowed (Phase 0A: stub message)"
echo "- Invalid identity should be denied with verification error"
echo "- Invalid method should return 'method not found' error"
