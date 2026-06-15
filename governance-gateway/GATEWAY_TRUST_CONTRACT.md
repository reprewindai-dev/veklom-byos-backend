# Gateway Trust Contract

## Core Constraint

**The edge MCP MUST verify every privileged execution against a signed, short-lived Execution Authorization Token minted by the inside MCP; without a valid EAT, it MUST NOT perform the action, even if it receives syntactically valid requests.**

## Explicit Phase 0 & Phase 1 Constraint

**There MUST be no tools that move money out of Veklom (x402 or otherwise) in Phase 0 and Phase 1. All payments are ingress-only until explicit approval to add disbursement tools.**

## Architecture Overview

### Inside MCP (Governance Gateway - Backend)
- **Location**: Runs inside FastAPI/backend environment (Coolify container)
- **Network**: Same network as PostgreSQL, Redis, UACP, ledger
- **Responsibilities**:
  - Identity attestation
  - Authority/UACP calls
  - Approval workflows
  - Audit context creation
  - Execution token minting
  - Final ledger append orchestration

### Edge MCP (Ingress/Execution Gateway)
- **Location**: Runs at the edge (behind Traefik/Cloudflare, near public APIs)
- **Responsibilities**:
  - Accept external traffic (including x402 flows)
  - Accept "execute this action" calls from inside MCP
  - Verify EATs
  - Perform tightly-scoped side effects (HTTP, webhooks, browser, paid endpoint unlock)
  - Return execution receipts to inside MCP

## Execution Authorization Token (EAT)

### Token Fields

```json
{
  "eat_id": "unique-identifier-for-this-execution-authorization",
  "agent_id": "who-this-execution-is-on-behalf-of",
  "authority_run_id": "the-governance-run-this-execution-is-part-of",
  "tool_name": "name/class-of-the-action",
  "resource_scope": {
    "url": "https://api.example.com/resource",
    "method": "GET",
    "max_amount": 0.00,
    "domain": "api.example.com"
  },
  "workspace_id": "workspace-tenant-context",
  "issued_at": "2024-01-01T12:00:00Z",
  "expires_at": "2024-01-01T12:02:00Z",
  "nonce": "random-string-for-replay-protection",
  "constraints": {
    "max_retries": 3,
    "timeout_seconds": 30,
    "requires_x402": false,
    "allowed_methods": ["GET", "POST"]
  },
  "signature": "cryptographic-signature-from-backend-key"
}
```

### Canonical Signing Payload

The inside MCP signs this stable JSON representation:

```json
{
  "eat_id": "...",
  "agent_id": "...",
  "authority_run_id": "...",
  "tool_name": "...",
  "resource_scope": {...},
  "workspace_id": "...",
  "issued_at": "...",
  "expires_at": "...",
  "nonce": "...",
  "constraints": {...}
}
```

Signature is computed over this payload; signature field is appended after signing.

## Inside MCP Responsibilities

### For Each Action Request from Agent

1. **Identity + Policy**
   - Verify agent's birth/identity against PGL
   - Call UACP with agent + bundle + tool + workspace
   - Get allow/deny/needs_approval decision

2. **Decision**
   - If deny: return error to agent; log `tool_call_denied`
   - If needs_approval: pause; trigger human path; log `tool_call_needs_approval`
   - If allow: proceed to token minting

3. **Mint EAT**
   - Construct EAT with agent_id, authority_run_id, tool_name, resource_scope, workspace_id
   - issued_at = now; expires_at = now + short TTL (30-120 seconds)
   - nonce = random string
   - constraints = extra rules (e.g., "only GET", "must use x402")
   - Sign payload with backend private key; attach signature

4. **Audit Logging (Pre-execution)**
   - Append `tool_call_allowed` event to ledger with EAT id
   - Chain after previous events for that agent/run

5. **Call Edge MCP**
   - Send EAT + execution request to edge MCP over secure internal channel
   - Use mTLS or private network

6. **Audit Logging (Post-execution)**
   - When edge returns receipt, log `tool_call_success` or `tool_call_error`
   - Include outcome and link back to authority_run_id and eat_id

## Edge MCP Responsibilities

### For Each Incoming Execution from Inside

1. **Verify Token**
   - Check signature (using backend public key)
   - Verify expires_at >= now
   - Ensure eat_id unseen (store briefly to prevent reuse)
   - Verify nonce unused (replay protection)
   - If any check fails: reject; return error; optionally log locally

2. **Enforce Scope**
   - Confirm target URL/route matches resource_scope
   - Verify HTTP method matches constraints
   - If x402 required, verify payment proof is present and valid (Phase 0B)
   - Edge must not expand scope; can only further restrict or reject

3. **Execute**
   - Perform the side effect (HTTP request, webhook, paid endpoint unlock)
   - Capture: status code, response body summary (or hash), execution time, x402 payment reference

4. **Return Receipt**
   - Return to inside MCP:
     - eat_id
     - authority_run_id
     - status (success/error)
     - response_summary or hash
     - x402_payment_reference or metadata

5. **Local Logging**
   - Edge can keep own logs for ops
   - Source-of-truth audit remains in backend ledger

## Allowed Failure Modes

### Token Invalid/Expired/Replayed
- Edge must reject and never call external resource
- Inside can log `tool_call_invalid_eat` error audit event

### External Resource Fails (500, timeout)
- Edge returns status = error to inside
- Inside logs `tool_call_error` with error summary
- Agent sees tool failure, not silent drop

### UACP Down
- Inside MCP must default to deny (fail-closed) or "needs_approval"
- Must not mint EATs when cannot obtain decision

### Ledger/Audit Storage Down
- For privileged actions, inside MCP should either:
  - Fail-closed (do not proceed if cannot log)
  - Buffer events safely until storage returns
- Choose based on risk tolerance

## Policy Rule

**The edge MCP MUST NOT independently authorize any privileged action. It may execute only actions covered by a valid backend-issued execution authorization token.**

## Money Movement Constraint

**Phase 0 & Phase 1: No tools that move money out of Veklom. All payments are ingress-only until explicit approval to add disbursement tools.**

This constraint keeps the implementation honest: no spending power until explicit approval, not just when code exists.
