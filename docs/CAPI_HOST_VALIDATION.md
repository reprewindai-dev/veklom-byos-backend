# cAPI Host-Level Validation: Fail-Closed Enforcement

## The Principle: Zero Trust by Default
Every agent execution intent entering the Veklom ecosystem must cryptographically prove its authority before a single instruction reaches the execution context. 

Fail-closed means **if you cannot prove validation, you do not execute**. If the PGL identity cannot be resolved, if the uacpv3 policy composition fails to yield a deterministic `ALLOW`, if the safety scorer detects an active quarantine, if the budget ledger is depleted—the call is immediately terminated. No retries, no deferrals, no fallback to less secure defaults.

This is the governance moat. Any control surface running live execution—including the fast-running [Agent-Control terminal](https://github.com/reprewindai-dev/Agent-Control-need-pgl)—is an open exposure unless it binds every action through the cAPI interceptor.

---

## 1. The 9-Phase Validation Pipeline
The host enforces validation sequentially across nine distinct gates. A failure at any gate from Phase 1 through 5 halts execution and immediately seals a denial receipt in the ledger (Phase 7).

```
          Agent Request
               │
               ▼
  [1] Identity & Cryptography   ← FAIL-CLOSED: Invalid signature = instant reject
               │
               ▼
  [2] Capability & Policy       ← FAIL-CLOSED: No explicit ALLOW in 3-tier rules = deny
               │
               ▼
  [3] Safety & Anomaly          ← FAIL-CLOSED: Anomalous rate/payload = quarantine
               │
               ▼
  [4] Cost & Budget             ← FAIL-CLOSED: Out of credits / token headroom = deny
               │
               ▼
  [5] M-of-N Approval Gate      ← FAIL-CLOSED: Quorum not signed = hold
               │
               ▼
  [6] Execution Sandbox         ← Only phase that triggers side effects
               │
               ▼
  [7] Evidence & PGL Sealing    ← Seals SHA-256 hash-chained record unconditionally
               │
               ▼
  [8] Audit & Retention         ← Logs emitted to audit table with retention class
               │
               ▼
  [9] Response Egress           ← Return verdict + proof of governance
```

---

## 2. Implementing Host-Level Gates (cAPI Interceptor)

### Phase 1: Cryptographic Identity Verification
Before parsing the execution payload, the host verifies the signature using the agent's Ed25519 public key.

```typescript
// Example Implementation: src/lib/covenant/crypto.ts
import { verify } from "noble-ed25519";

async function validateIdentity(req: GovernedRequest): Promise<ValidationResult> {
  const agent = await registry.resolveAgent(req.agentId);
  if (!agent) {
    return { approved: false, reason: "AGENT_NOT_FOUND", phase: 1 };
  }

  // Prevent replay attacks: Nonce must be unused and within timestamp TTL (e.g., 300s)
  const isUniqueNonce = await nonceStore.claim(req.nonce, req.timestamp);
  if (!isUniqueNonce) {
    return { approved: false, reason: "REPLAY_ATTACK_DETECTED", phase: 1 };
  }

  // Verify signature over the canonical JSON representation of the body
  const message = canonicalize(req.body);
  const signatureValid = await verify(req.signature, message, agent.publicKey);
  if (!signatureValid) {
    return { approved: false, reason: "CRYPTOGRAPHIC_SIGNATURE_INVALID", phase: 1 };
  }

  return { approved: true, agent };
}
```

### Phase 2: Three-Tier Policy Composition
Policy resolution checks rules across three tiers: System constraints, Owner boundaries, and Runtime parameters. **A System Deny overrides everything.**

```typescript
// Example Implementation: src/lib/covenant/governance.ts
function composePolicy(
  systemPolicy: Policy,
  ownerPolicy: Policy,
  runtimePolicy: Policy,
  action: string
): EffectivePermission {
  // 1. System Overrides (Hard Veto)
  const systemRule = systemPolicy.rules.find(r => r.action === action);
  if (systemRule?.effect === "DENY") {
    return { allowed: false, reason: "SYSTEM_POLICY_VETO", phase: 2 };
  }

  // 2. Owner & Runtime Conflict Resolution (Most restrictive wins)
  const ownerRule = ownerPolicy.rules.find(r => r.action === action);
  const runtimeRule = runtimePolicy.rules.find(r => r.action === action);

  if (ownerRule?.effect === "DENY" || runtimeRule?.effect === "DENY") {
    return { allowed: false, reason: "POLICIES_CONSTRUCT_DENY", phase: 2 };
  }

  // 3. Implicit Deny (Must have at least one explicit ALLOW)
  const hasAllow = [systemRule, ownerRule, runtimeRule].some(r => r?.effect === "ALLOW");
  if (!hasAllow) {
    return { allowed: false, reason: "NO_EXPLICIT_ALLOW_RULE", phase: 2 };
  }

  return { allowed: true };
}
```

---

## 3. Structuring Test Commands for Fail-Closed Validation
To verify that the validation pipeline rejects unauthorized dispatches, run the following automated validation test suite.

### Test 1: Tampered Payload Signature Rejection (Phase 1)
Verify that cAPI drops any request where the execution payload does not match the signature.

```bash
# Test Payload with modified parameters after signature generation
curl -s -X POST "https://api.veklom.com/api/v1/capi/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent-core-01",
    "pgl_id": "pgl_sig_8a3f9e2b10cd4a",
    "target_protocol": "syscall_execute",
    "action": "fs.write",
    "payload": {
      "path": "/etc/hosts",
      "content": "127.0.0.1 illegal-routing.net"
    }
  }'

# Expected response: 401 Unauthorized or 403 Forbidden
# Response JSON must contain:
# {
#   "error": "cAPI_VETO_ENGAGED",
#   "phase": 1,
#   "reason": "CRYPTOGRAPHIC_SIGNATURE_INVALID"
# }
```

### Test 2: Implicit Deny Enforcement (Phase 2)
Verify that any capability missing an explicit ALLOW rule is blocked by default.

```bash
# Dispatching 'db.drop_tables' which lacks an ALLOW rule in the bundle
curl -s -X POST "https://api.veklom.com/api/v1/capi/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent-core-01",
    "pgl_id": "pgl_sig_8a3f9e2b10cd4a",
    "target_protocol": "mcp",
    "action": "db.drop_tables",
    "payload": {}
  }'

# Expected response: 403 Forbidden
# Response JSON must contain:
# {
#   "error": "cAPI_VETO_ENGAGED",
#   "phase": 2,
#   "reason": "NO_EXPLICIT_ALLOW_RULE"
# }
```

### Test 3: Budget Depletion Lock (Phase 4)
Exhaust the token/credit budget to ensure subsequent executions are blocked cleanly.

```bash
# 1. Inspect initial budget
curl -s "https://api.veklom.com/api/v1/budget/agent-core-01"

# 2. Force token consumption beyond headroom limits
curl -s -X POST "https://api.veklom.com/api/v1/capi/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent-core-01",
    "pgl_id": "pgl_sig_8a3f9e2b10cd4a",
    "target_protocol": "model_inference",
    "action": "llm.generate",
    "payload": { "max_tokens": 100000000 }
  }'

# Expected response: 402 Payment Required or 403 Forbidden
# Response JSON must contain:
# {
#   "error": "cAPI_VETO_ENGAGED",
#   "phase": 4,
#   "reason": "BUDGET_EXHAUSTED"
# }
```

---

## 4. Wiring the Fast Terminal (`Agent-Control-need-pgl`)
The [Agent-Control terminal](https://github.com/reprewindai-dev/Agent-Control-need-pgl) is running fast, unmonitored commands. To plug this leak, you must refactor the terminal's dispatch loop to enforce PGL validation.

### Before (Ungoverned Execution):
The terminal runs commands directly via local shells or raw HTTP connections:
```javascript
// Danger: No audit trail, no policy checks, no signature
const result = await execShellCommand(command);
```

### After (PGL Governed Execution):
Wrap every command execution inside a signed cAPI intent envelope:
```typescript
import { signPayload } from "./crypto";

async function executeGovernedCommand(command: string) {
  const payload = { command };
  const pgl_id = process.env.VEKLOM_AGENT_PGL_ID;
  const agent_id = process.env.VEKLOM_AGENT_ID;

  // Sign the intent payload to prevent tampering
  const signature = await signPayload(payload, process.env.VEKLOM_AGENT_PRIVATE_KEY);

  const response = await fetch("https://api.veklom.com/api/v1/capi/execute", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Agent-Signature": signature
    },
    body: JSON.stringify({
      agent_id,
      pgl_id,
      target_protocol: "local_tool",
      action: "terminal.execute",
      payload
    })
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(`Execution Blocked by cAPI (Phase ${errorData.phase}): ${errorData.reason}`);
  }

  const receipt = await response.json();
  console.log(`[PGL SEALED] Evidence Chain ID: ${receipt.evidence_chain_id}`);
  return receipt.result;
}
```

By enforcing this structure, any attempt to run unauthorized commands in the terminal fails closed, registering the veto in the immutable hash chain.
