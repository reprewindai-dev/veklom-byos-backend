# Governance Gateway - Phase 0A

A Rust enforcement gateway that provides identity verification, policy checking, and audit logging for Veklom's governed runtime.

## Architecture

The governance gateway implements Phase 0A of the Veklom governance specification:

- **Identity Module**: Verifies agent certificates and genome hashes against PGL birth state
- **Authority Module**: Integrates with UACP for policy enforcement decisions
- **Audit Ledger Module**: Records hash-chained events for immutable audit trails
- **MCP Interface**: Handles MCP protocol communication with Python runtime

## Phase 0A Features

### 0A.1 Service Skeleton
- Rust service with modular architecture
- MCP-facing API over HTTP
- No external HTTP or payment logic yet

### ⚠️ Explicit Phase 0 & Phase 1 Constraint
**There MUST be no tools that move money out of Veklom (x402 or otherwise) in Phase 0 and Phase 1. All payments are ingress-only until explicit approval to add disbursement tools.**

### 0A.2 Identity Intake & Session Attestation
- Verifies `certificate_id` and `latest_genome_hash` against active birth state
- Validates certificate status and genome hash consistency
- Builds `IdentityContext` for policy decisions
- Rejects invalid sessions before exposing any tools

### 0A.3 Policy Gate Tool (UACP Integration)
- Calls UACP authority service with identity + action + context
- Enforces allow/deny/approval_required decisions exactly
- Exposes MCP `policy_gate` tool for Python agents
- Caches identity verification per session

### 0A.4 Audit Ledger Append
- Records hash-chained events: `tool_call_attempt`, `tool_call_allowed`, `tool_call_denied`, `tool_call_needs_approval`
- Computes SHA-256 hashes with previous event chaining
- Persists events in same ledger as birth_registration and deployment events
- Maintains chain consistency for Alpha/Beta/Gamma packets

### 0A.5 MCP "execute_action" (No Real Side Effects)
- Uses policy_gate internally
- Returns error for deny/approval_required without execution
- For allow: logs "would execute X" stub event
- No external HTTP or browser interactions

## Configuration

Environment variables:

```bash
# Backend service URLs
BACKEND_URL=http://localhost:8000
AUTHORITY_URL=http://localhost:8000/api/v1/authority
PGL_URL=http://localhost:8000/api/v1/pgl
AUDIT_URL=http://localhost:8000/api/v1/evidence

# Gateway settings
GATEWAY_PORT=8080
RUST_LOG=debug
```

## Building and Running

```bash
# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Build
cargo build --release

# Run
cargo run

# Or with custom environment
RUST_LOG=info GATEWAY_PORT=8080 cargo run
```

## API Endpoints

### Health Check
```
GET /health
```

Returns service health status and component operational status.

### MCP Interface
```
POST /mcp
Content-Type: application/json

{
  "method": "execute_action",
  "params": {
    "agent_id": "agent_12345",
    "certificate_id": "cert_abc123",
    "latest_genome_hash": "sha256:hash123",
    "tool_name": "web_search",
    "workspace_id": "workspace_67890",
    "action_context": {
      "query": "example search"
    }
  },
  "id": 1
}
```

### Available MCP Tools

#### execute_action
Executes a governed action with identity verification and policy checking.

**Parameters:**
- `agent_id` (required): Agent identifier
- `certificate_id` (required): PGL birth certificate ID
- `latest_genome_hash` (required): Current genome hash
- `tool_name` (required): Tool to execute
- `workspace_id` (required): Workspace identifier
- `action_context` (optional): Additional context for policy evaluation

**Responses:**
- `allow`: Tool is permitted (Phase 0A: returns stub message)
- `deny`: Tool is not permitted with reason
- `needs_approval`: Tool requires human approval

#### ping
Test connectivity to the governance gateway.

#### list_tools
List available MCP tools and their parameters.

## Integration with Python Runtime

The gateway sits between MCP clients and the Python runtime:

1. MCP client calls `execute_action`
2. Gateway verifies identity against PGL
3. Gateway checks policy with UACP
4. Gateway records audit events
5. Gateway returns decision to client
6. (Phase 0A) No real execution - only logging

## Audit Trail

All actions create hash-chained audit events:

```json
{
  "event_type": "tool_call_allowed",
  "agent_id": "agent_12345",
  "authority_run_id": "run_abcdef12",
  "tool_name": "web_search",
  "summary": "Tool call allowed: web_search",
  "details": {
    "reason": "Tool in allowed list",
    "timestamp": "2024-01-01T12:00:00Z"
  },
  "created_at": "2024-01-01T12:00:00Z",
  "event_hash": "sha256:hash...",
  "prev_event_hash": "sha256:prev_hash..."
}
```

## Testing

```bash
# Run unit tests
cargo test

# Run integration tests (requires backend services)
cargo test --test integration

# Test MCP endpoint
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"method":"ping","params":{},"id":1}'
```

## Phase 0B Preview

Phase 0B will add:
- Single x402-paid endpoint
- Merchant-side x402 verification flow
- Billing integration
- No internal agent spending capabilities

## Development Notes

- Uses FastMCP for MCP protocol handling
- Axum web framework for HTTP server
- Reqwest for HTTP client calls to backend services
- SHA-256 for hash chaining
- UUID generation for authority run IDs
- Comprehensive error handling and logging

## Security Considerations

- All MCP requests require valid identity verification
- Policy decisions are enforced before any execution
- Audit trail is immutable through hash chaining
- No direct database access - goes through backend APIs
- Session-based identity caching to prevent repeated verification
