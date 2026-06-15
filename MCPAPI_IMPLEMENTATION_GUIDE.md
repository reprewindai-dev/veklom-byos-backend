# MCPAPI Implementation Guide

**Version:** 1.0.0  
**Status:** Locked  
**Last Updated:** June 12, 2026

---

## Overview

This guide walks runtime builders through implementing MCPAPI. There are three implementation paths:

1. **Veklom Flagship Runtime** — Full integration with Veklom infrastructure
2. **Enterprise Runtime** — Standalone with PGL support
3. **Local Runtime** — Edge deployment with offline capability

This guide covers all three.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Architecture Overview](#architecture-overview)
3. [Implementation Phases](#implementation-phases)
4. [Component Breakdown](#component-breakdown)
5. [Integration Points](#integration-points)
6. [Testing Strategy](#testing-strategy)
7. [Deployment](#deployment)
8. [Operations](#operations)

---

## Prerequisites

### Knowledge Requirements
- Protocol specification (MCPAPI_PROTOCOL_SPECIFICATION.md)
- Model Context Protocol (MCP) standard
- Project Genome Ledger (PGL) concepts
- Cryptographic signing (Ed25519)
- JSON Schema validation

### Technical Requirements
- Node.js 18+ or Python 3.10+
- TypeScript 5+ (if using TypeScript implementation)
- PostgreSQL 14+ (for ledger storage)
- Redis 7+ (for caching + rate limiting)
- OpenSSL (for key generation)

### Infrastructure Requirements
- MCPAPI-compatible DNS
- Key management service (KMS) or equivalent
- Monitoring + logging system
- Secrets management (Vault, AWS Secrets, etc.)

---

## Architecture Overview

### Runtime Structure

```
┌─────────────────────────────────────────┐
│ MCPAPI Runtime                          │
├─────────────────────────────────────────┤
│                                         │
│ ┌─ Request Handler ─────────────────┐  │
│ │ - Parse + validate request        │  │
│ │ - Route to processor              │  │
│ └───────────────────────────────────┘  │
│                                         │
│ ┌─ Identity Layer ──────────────────┐  │
│ │ - Resolve agent identity          │  │
│ │ - Verify signature                │  │
│ │ - Resolve capability identity     │  │
│ └───────────────────────────────────┘  │
│                                         │
│ ┌─ Policy Engine ───────────────────┐  │
│ │ - Load applicable policies        │  │
│ │ - Evaluate rules                  │  │
│ │ - Check conditions                │  │
│ │ - Route approvals                 │  │
│ └───────────────────────────────────┘  │
│                                         │
│ ┌─ Trust Engine ────────────────────┐  │
│ │ - Compute trust score             │  │
│ │ - Update scores                   │  │
│ │ - Apply thresholds                │  │
│ └───────────────────────────────────┘  │
│                                         │
│ ┌─ Capability Router ───────────────┐  │
│ │ - Resolve endpoint (MCP/HTTP)     │  │
│ │ - Execute capability              │  │
│ │ - Capture result                  │  │
│ │ - Handle errors + retries         │  │
│ └───────────────────────────────────┘  │
│                                         │
│ ┌─ Evidence Generator ──────────────┐  │
│ │ - Create evidence record          │  │
│ │ - Hash chain                      │  │
│ │ - Sign evidence                   │  │
│ └───────────────────────────────────┘  │
│                                         │
│ ┌─ PGL Client ──────────────────────┐  │
│ │ - Commit to ledger                │  │
│ │ - Get immutable hash              │  │
│ │ - Retrieve historical records     │  │
│ └───────────────────────────────────┘  │
│                                         │
│ ┌─ Audit Logger ────────────────────┐  │
│ │ - Write to audit log              │  │
│ │ - Compress old logs               │  │
│ │ - Query + export                  │  │
│ └───────────────────────────────────┘  │
│                                         │
├─────────────────────────────────────────┤
│ Storage                                 │
│ - PostgreSQL (identity, policies)       │
│ - Redis (cache, rate limits)            │
│ - File system (audit logs)              │
│ - PGL ledger (external)                 │
└─────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1-2)

**Goal:** Core protocol implementation without external dependencies.

#### 1.1 Identity Layer

```typescript
// src/identity/agent-identity.ts
export class AgentIdentityService {
  // Register agent from authority bundle
  registerFromBundle(bundle: AuthorityBundle): AgentIdentity
  
  // Resolve agent by ID
  resolveAgent(agent_id: string): AgentIdentity | null
  
  // Verify agent signature
  verifySignature(agent: AgentIdentity, message: Buffer, signature: Buffer): boolean
}

// src/identity/capability-identity.ts
export class CapabilityIdentityService {
  // Register capability
  register(capability: CapabilityIdentity): boolean
  
  // Resolve by ID
  resolve(capability_id: string): CapabilityIdentity | null
  
  // List capabilities for agent
  listForAgent(agent_id: string): CapabilityIdentity[]
}
```

**Deliverable:**
- Identity registry (in-memory or PostgreSQL)
- Signature verification utility
- Identity resolution service

#### 1.2 Policy Engine

```typescript
// src/policy/policy-engine.ts
export class PolicyEngine {
  // Load policies
  loadPolicy(policy: Policy): boolean
  
  // Evaluate access
  evaluate(
    agent_id: string,
    capability_id: string,
    context?: Record<string, unknown>
  ): PolicyDecision
  
  // Check conditions
  private checkConditions(rule: PolicyRule, context: PolicyContext): boolean
}

// src/policy/types.ts
interface PolicyDecision {
  authorized: boolean
  policy_id?: string
  requires_approval?: boolean
  approval_path?: string
  reason?: string
}
```

**Deliverable:**
- Policy parser + validator
- Rule evaluation engine
- Condition checker (time, rate limit, trust)

#### 1.3 Trust Engine

```typescript
// src/trust/trust-engine.ts
export class TrustEngine {
  // Compute trust score
  compute(agent_id: string): TrustScore
  
  // Update score
  update(agent_id: string, delta: number): TrustScore
  
  // Apply decay
  applyDecay(): void
  
  // Check threshold
  meetsThreshold(agent_id: string, required: number): boolean
}
```

**Deliverable:**
- Trust scoring algorithm
- Score persistence
- Threshold evaluation

#### 1.4 Evidence Generator

```typescript
// src/evidence/evidence-generator.ts
export class EvidenceGenerator {
  // Create evidence record
  generate(
    request: MCPAPIRequest,
    result: ExecutionResult
  ): Evidence
  
  // Chain with previous
  chainWithPrevious(evidence: Evidence): Evidence
  
  // Sign evidence
  sign(evidence: Evidence, key: string): string
}
```

**Deliverable:**
- Evidence structure builder
- Hash chain integrity
- Signature generation

---

### Phase 2: Core Runtime (Week 3-4)

**Goal:** Request processing pipeline with policy enforcement.

#### 2.1 Request Handler

```typescript
// src/runtime/request-handler.ts
export class RequestHandler {
  async handle(request: MCPAPIRequest): Promise<MCPAPIResponse> {
    // Step 1: Resolve identity
    const agent = await this.identityService.resolve(request.agent_id)
    if (!agent) throw new UnauthorizedError()
    
    // Step 2: Verify signature
    const isValid = this.identityService.verifySignature(agent, request)
    if (!isValid) throw new SignatureVerificationError()
    
    // Step 3: Resolve capability
    const capability = await this.identityService.resolve(request.capability_id)
    if (!capability) throw new NotFoundError()
    
    // Step 4: Evaluate policy
    const decision = await this.policyEngine.evaluate(
      request.agent_id,
      request.capability_id
    )
    if (!decision.authorized) throw new PolicyDeniedError()
    
    // Step 5: Route to capability
    const result = await this.capabilityRouter.execute(
      request,
      capability
    )
    
    // Step 6: Generate evidence
    const evidence = this.evidenceGenerator.generate(request, result)
    
    // Step 7: Commit to PGL
    const pgl_hash = await this.pglClient.commit(evidence)
    
    // Step 8: Update trust
    this.trustEngine.update(request.agent_id, 2) // success bonus
    
    return MCPAPIResponse.success(pgl_hash, result)
  }
}
```

**Deliverable:**
- Full request processing pipeline
- Error handling + logging
- Response formatting

#### 2.2 Capability Router

```typescript
// src/runtime/capability-router.ts
export class CapabilityRouter {
  async execute(
    request: MCPAPIRequest,
    capability: CapabilityIdentity
  ): Promise<ExecutionResult> {
    const { method, endpoint } = this.parseEndpoint(capability.endpoint)
    
    switch (method) {
      case 'mcp':
        return this.routeMCP(endpoint, request)
      case 'http':
        return this.routeHTTP(endpoint, request)
      case 'local':
        return this.routeLocal(endpoint, request)
      default:
        throw new UnsupportedEndpointError()
    }
  }
  
  private async routeMCP(endpoint: string, request: MCPAPIRequest) {
    // Route to MCP server
  }
  
  private async routeHTTP(endpoint: string, request: MCPAPIRequest) {
    // Route to HTTP API
  }
  
  private async routeLocal(endpoint: string, request: MCPAPIRequest) {
    // Route to local function
  }
}
```

**Deliverable:**
- MCP server integration
- HTTP endpoint routing
- Local function invocation
- Result capturing + error handling

#### 2.3 Audit Logger

```typescript
// src/audit/audit-logger.ts
export class AuditLogger {
  // Log interaction
  log(entry: AuditLogEntry): Promise<void>
  
  // Query logs
  query(filters: QueryFilters): Promise<AuditLogEntry[]>
  
  // Export logs
  export(start: Date, end: Date): Promise<Buffer>
  
  // Compress old logs
  compress(): Promise<void>
}
```

**Deliverable:**
- Structured audit logging
- Query interface
- Log rotation + compression
- Export formats (JSON, CSV)

---

### Phase 3: Integration (Week 5-6)

**Goal:** PGL integration, Veklom wiring, and deployment readiness.

#### 3.1 PGL Client

```typescript
// src/pgl/pgl-client.ts
export class PGLClient {
  // Commit evidence to ledger
  async commit(evidence: Evidence): Promise<string> {
    const hash = await this.pglService.register({
      who: evidence.who.agent_id,
      what: evidence.what.capability_id,
      when: evidence.when.executed_at,
      why: evidence.why.policy_applied,
      how: evidence.how.method,
      proof: evidence.pgl_hash
    })
    return hash
  }
  
  // Retrieve evidence
  async retrieve(hash: string): Promise<Evidence | null> {
    return this.ledger.get(hash)
  }
  
  // Replay interaction chain
  async replay(hash: string): Promise<Evidence[]> {
    const evidence = await this.retrieve(hash)
    const chain = [evidence]
    let current = evidence
    
    while (current.previous_hash) {
      current = await this.retrieve(current.previous_hash)
      if (!current) break
      chain.unshift(current)
    }
    
    return chain
  }
}
```

**Deliverable:**
- PGL protocol client
- Ledger commitment
- Evidence retrieval
- Chain replay capability

#### 3.2 Veklom Integration

```typescript
// src/veklom/veklom-integration.ts
export class VeklomIntegration {
  // Validate authority bundle
  validateBundle(bundle: AuthorityBundle): boolean
  
  // Register to gnom ledger
  registerToGnomLedger(entry: GnomLedgerEntry): Promise<void>
  
  // Route to governance
  routeToGovernance(
    agent_id: string,
    decision: PolicyDecision
  ): Promise<GovernanceRouting>
  
  // Register to PGL with birth certificate
  registerWithBirthCertificate(
    agent: VeklomAgent,
    evidence: Evidence
  ): Promise<string>
}
```

**Deliverable:**
- Authority bundle validation
- Gnom ledger integration
- Governance routing
- Birth certificate generation

#### 3.3 API Server

```typescript
// src/server/mcpapi-server.ts
import express from 'express'

const app = express()

// POST /mcpapi/request
app.post('/mcpapi/request', async (req, res) => {
  const request = req.body as MCPAPIRequest
  const response = await runtime.handle(request)
  res.json(response)
})

// GET /mcpapi/capabilities/{agent_id}
app.get('/mcpapi/capabilities/:agent_id', async (req, res) => {
  const capabilities = runtime.discoverCapabilities(req.params.agent_id)
  res.json(capabilities)
})

// GET /mcpapi/audit/log
app.get('/mcpapi/audit/log', async (req, res) => {
  const logs = runtime.getAuditLog(req.query)
  res.json(logs)
})

// GET /mcpapi/pgl/{hash}
app.get('/mcpapi/pgl/:hash', async (req, res) => {
  const evidence = runtime.getEvidenceByHash(req.params.hash)
  if (!evidence) return res.status(404).json({})
  res.json(evidence)
})

// GET /mcpapi/replay/{hash}
app.get('/mcpapi/replay/:hash', async (req, res) => {
  const chain = runtime.replayInteraction(req.params.hash)
  res.json(chain)
})

app.listen(3000)
```

**Deliverable:**
- REST API endpoints
- Request validation middleware
- Error handling
- Response formatting

---

## Component Breakdown

### Identity Service

**Responsibility:** Agent + capability identity resolution + signature verification

**Storage:** PostgreSQL table `identities`
```sql
CREATE TABLE identities (
  id UUID PRIMARY KEY,
  entity_type VARCHAR(20), -- 'agent' or 'capability'
  entity_id VARCHAR(255) UNIQUE,
  owner_id VARCHAR(255),
  public_key TEXT,
  metadata JSONB,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);

CREATE INDEX idx_identities_entity_id ON identities(entity_id);
```

**Caching:** Redis key: `identity:{entity_id}`

**API:**
```typescript
interface IIdentityService {
  register(identity: AgentIdentity | CapabilityIdentity): Promise<void>
  resolve(entity_id: string): Promise<Identity | null>
  verifySignature(agent: AgentIdentity, message: Buffer, signature: Buffer): boolean
  list(filter: IdentityFilter): Promise<Identity[]>
}
```

### Policy Engine

**Responsibility:** Policy evaluation + condition checking

**Storage:** PostgreSQL table `policies`
```sql
CREATE TABLE policies (
  id UUID PRIMARY KEY,
  policy_id VARCHAR(255) UNIQUE,
  policy_name VARCHAR(255),
  version VARCHAR(20),
  rules JSONB,
  metadata JSONB,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);

CREATE INDEX idx_policies_policy_id ON policies(policy_id);
```

**Caching:** Redis key: `policy:{policy_id}`

**API:**
```typescript
interface IPolicyEngine {
  load(policy: Policy): Promise<void>
  evaluate(
    principal: string,
    action: string,
    context?: PolicyContext
  ): Promise<PolicyDecision>
  checkCondition(rule: PolicyRule, context: PolicyContext): boolean
}
```

### Trust Engine

**Responsibility:** Trust score computation + persistence

**Storage:** PostgreSQL table `trust_scores`
```sql
CREATE TABLE trust_scores (
  agent_id VARCHAR(255) PRIMARY KEY,
  score FLOAT,
  success_rate FLOAT,
  policy_adherence FLOAT,
  denial_frequency FLOAT,
  escalation_events FLOAT,
  last_updated TIMESTAMP
);

CREATE INDEX idx_trust_scores_score ON trust_scores(score);
```

**Caching:** Redis key: `trust:{agent_id}`

**API:**
```typescript
interface ITrustEngine {
  compute(agent_id: string): Promise<TrustScore>
  update(agent_id: string, delta: number): Promise<TrustScore>
  meetsThreshold(agent_id: string, required: number): Promise<boolean>
}
```

### Evidence Generator

**Responsibility:** Evidence creation + hash chaining + signing

**Storage:** PostgreSQL table `evidence`
```sql
CREATE TABLE evidence (
  id UUID PRIMARY KEY,
  evidence_id VARCHAR(255) UNIQUE,
  connection_id VARCHAR(255),
  pgl_hash VARCHAR(255),
  agent_id VARCHAR(255),
  capability_id VARCHAR(255),
  status VARCHAR(20),
  result_hash VARCHAR(255),
  previous_hash VARCHAR(255),
  created_at TIMESTAMP
);

CREATE INDEX idx_evidence_pgl_hash ON evidence(pgl_hash);
CREATE INDEX idx_evidence_agent_id ON evidence(agent_id);
CREATE INDEX idx_evidence_previous_hash ON evidence(previous_hash);
```

**API:**
```typescript
interface IEvidenceGenerator {
  generate(request: MCPAPIRequest, result: ExecutionResult): Promise<Evidence>
  sign(evidence: Evidence, key: string): string
  verifyChain(hash: string): Promise<boolean>
}
```

### Capability Router

**Responsibility:** Route requests to MCP/HTTP/local endpoints

**Supported Endpoints:**
- `mcp://server-id/tool-id` → MCP server
- `http://api.example.com/endpoint` → HTTP API
- `local://function-name` → Local function

**API:**
```typescript
interface ICapabilityRouter {
  execute(
    request: MCPAPIRequest,
    capability: CapabilityIdentity
  ): Promise<ExecutionResult>
  
  registerMCPServer(server: MCPServerConfig): Promise<void>
  registerHTTPEndpoint(config: HTTPEndpointConfig): Promise<void>
  registerLocalFunction(name: string, fn: Function): Promise<void>
}
```

### Audit Logger

**Responsibility:** Log all interactions + support queries

**Storage:** PostgreSQL table `audit_log`
```sql
CREATE TABLE audit_log (
  id UUID PRIMARY KEY,
  connection_id VARCHAR(255),
  agent_id VARCHAR(255),
  capability_id VARCHAR(255),
  action VARCHAR(255),
  decision VARCHAR(20), -- 'authorized', 'denied', 'error'
  evidence_hash VARCHAR(255),
  created_at TIMESTAMP
);

CREATE INDEX idx_audit_log_agent_id ON audit_log(agent_id);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at);
```

**API:**
```typescript
interface IAuditLogger {
  log(entry: AuditLogEntry): Promise<void>
  query(filters: QueryFilters): Promise<AuditLogEntry[]>
  export(start: Date, end: Date): Promise<Buffer>
}
```

---

## Integration Points

### With Veklom

```typescript
// src/veklom/adapters.ts

// 1. Authority Bundle → MCPAPI Policy
function authorityBundleToPolicy(bundle: AuthorityBundle): Policy {
  return {
    policy_id: `policy-${bundle.bundle_id}`,
    policy_name: `Authority: ${bundle.bundle_id}`,
    rules: bundle.mcp_tools.map(tool => ({
      rule_id: `rule-${tool}`,
      effect: 'allow',
      principal: bundle.agent_id,
      action: tool,
      conditions: {}
    })),
    metadata: {
      enforcement_mode: 'strict',
      escalation_threshold: 100,
      audit_trail: true
    }
  }
}

// 2. Agent Mission → MCPAPI Identity
function missionToAgentIdentity(agent: VeklomAgent): AgentIdentity {
  return {
    agent_id: agent.agent_id,
    agent_name: agent.agent_name,
    owner_id: agent.owner_id,
    public_key: agent.public_key,
    capabilities_manifest: agent.mission_file,
    created_at: agent.created_at,
    identity_proof: 'veklom-signed',
    metadata: {
      version: '1.0.0',
      framework: 'Veklom',
      inference_provider: 'claude',
      tier: agent.governance_tier
    }
  }
}

// 3. Evidence → PGL Birth Certificate
function evidenceToBirthCertificate(
  agent: VeklomAgent,
  evidence: Evidence
): VeklomPGLEntry {
  return {
    who: agent.agent_id,
    what: evidence.what.capability_id,
    when: evidence.when.executed_at,
    why: evidence.why.policy_applied,
    how: evidence.how.method,
    proof: evidence.pgl_hash,
    birth_certificate: generateBirthCertificate(agent)
  }
}

// 4. Policy Decision → Governance Routing
function policyDecisionToGovernanceRoute(
  decision: PolicyDecision,
  agent: VeklomAgent
): GovernanceRoute {
  if (decision.authorized) return { route: 'allowed' }
  if (decision.requires_approval) {
    return {
      route: 'requires_approval',
      approver: decision.approval_path
    }
  }
  return { route: 'denied' }
}
```

### With PGL

```typescript
// src/pgl/adapter.ts

// Evidence → PGL Entry
function evidenceToPGLEntry(evidence: Evidence): PGLEntry {
  return {
    who: evidence.who.agent_id,
    what: evidence.what.capability_id,
    when: evidence.when.executed_at,
    why: evidence.why.policy_applied,
    how: evidence.how.method,
    proof: crypto
      .createHash('sha256')
      .update(JSON.stringify(evidence))
      .digest('hex')
  }
}

// PGL Response → Evidence Hash
function pglResponseToHash(response: PGLResponse): string {
  return response.entry_hash
}
```

### With MCP Servers

```typescript
// src/mcp/adapter.ts

// MCPAPI Request → MCP Tool Call
function mcpapiRequestToMCPCall(
  request: MCPAPIRequest,
  capability: CapabilityIdentity
): MCPToolCall {
  return {
    server_id: extractServerId(capability.endpoint),
    tool_name: extractToolName(capability.endpoint),
    args: request.input
  }
}

// MCP Tool Result → MCPAPI Result
function mcpResultToMCPAPI(toolResult: MCPToolResult): ExecutionResult {
  return {
    status: 'success',
    output: toolResult.result,
    execution_time_ms: toolResult.duration_ms
  }
}
```

---

## Testing Strategy

### Unit Tests

```typescript
// test/identity.test.ts
describe('IdentityService', () => {
  it('should register agent identity', async () => {
    const service = new IdentityService()
    const agent = createTestAgent()
    
    await service.register(agent)
    const resolved = await service.resolve(agent.agent_id)
    
    expect(resolved).toEqual(agent)
  })
  
  it('should verify valid signature', async () => {
    const service = new IdentityService()
    const agent = createTestAgent()
    const message = Buffer.from('test')
    const signature = signMessage(message, agent.private_key)
    
    const isValid = service.verifySignature(agent, message, signature)
    expect(isValid).toBe(true)
  })
  
  it('should reject invalid signature', async () => {
    const service = new IdentityService()
    const agent = createTestAgent()
    const message = Buffer.from('test')
    const badSignature = Buffer.from('bad')
    
    const isValid = service.verifySignature(agent, message, badSignature)
    expect(isValid).toBe(false)
  })
})

// test/policy.test.ts
describe('PolicyEngine', () => {
  it('should allow authorized requests', async () => {
    const engine = new PolicyEngine()
    const policy = createAllowPolicy()
    await engine.load(policy)
    
    const decision = await engine.evaluate('agent-1', 'cap-1')
    expect(decision.authorized).toBe(true)
  })
  
  it('should deny unauthorized requests', async () => {
    const engine = new PolicyEngine()
    const policy = createDenyPolicy()
    await engine.load(policy)
    
    const decision = await engine.evaluate('agent-1', 'cap-1')
    expect(decision.authorized).toBe(false)
  })
})

// test/trust.test.ts
describe('TrustEngine', () => {
  it('should compute initial trust score', async () => {
    const engine = new TrustEngine()
    const score = await engine.compute('agent-1')
    expect(score.score).toBe(50) // neutral
  })
  
  it('should increase trust on success', async () => {
    const engine = new TrustEngine()
    const score1 = await engine.compute('agent-1')
    await engine.update('agent-1', 2)
    const score2 = await engine.compute('agent-1')
    expect(score2.score).toBeGreaterThan(score1.score)
  })
})
```

### Integration Tests

```typescript
// test/integration.test.ts
describe('MCPAPI Runtime', () => {
  let runtime: MCPAPIRuntime
  
  beforeEach(async () => {
    runtime = new MCPAPIRuntime()
    await runtime.start()
  })
  
  afterEach(async () => {
    await runtime.stop()
  })
  
  it('should process complete request flow', async () => {
    // Register agent
    const agent = createTestAgent()
    await runtime.registerAgent(agent)
    
    // Register capability
    const capability = createTestCapability()
    await runtime.registerCapability(capability)
    
    // Register policy
    const policy = createAllowPolicy()
    await runtime.registerPolicy(policy)
    
    // Create signed request
    const request = createSignedRequest(agent, capability)
    
    // Process
    const response = await runtime.handle(request)
    
    // Verify response
    expect(response.status).toBe('authorized')
    expect(response.evidence_hash).toBeDefined()
    expect(response.result).toBeDefined()
  })
  
  it('should deny unauthorized requests', async () => {
    const agent = createTestAgent()
    const capability = createTestCapability()
    const policy = createDenyPolicy()
    
    await runtime.registerAgent(agent)
    await runtime.registerCapability(capability)
    await runtime.registerPolicy(policy)
    
    const request = createSignedRequest(agent, capability)
    const response = await runtime.handle(request)
    
    expect(response.status).toBe('denied')
  })
  
  it('should generate verifiable evidence chain', async () => {
    // ... setup ...
    
    const response1 = await runtime.handle(request1)
    const response2 = await runtime.handle(request2)
    
    const chain = await runtime.replayInteraction(response2.evidence_hash)
    
    expect(chain.length).toBe(2)
    expect(chain[1].previous_hash).toBe(chain[0].pgl_hash)
  })
})
```

### Load Tests

```bash
# test/load.sh
#!/bin/bash

# Generate 1000 requests
for i in {1..1000}; do
  curl -X POST http://localhost:3000/mcpapi/request \
    -H "Content-Type: application/json" \
    -d @test/fixtures/request-$i.json &
done

wait
echo "1000 requests completed"
```

---

## Deployment

### Docker

```dockerfile
# Dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install --production

COPY dist/ ./dist/

EXPOSE 3000

CMD ["node", "dist/server.js"]
```

### Kubernetes

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcpapi-runtime
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mcpapi
  template:
    metadata:
      labels:
        app: mcpapi
    spec:
      containers:
      - name: mcpapi
        image: mcpapi-runtime:1.0.0
        ports:
        - containerPort: 3000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: mcpapi-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: mcpapi-secrets
              key: redis-url
        - name: PGL_ENDPOINT
          valueFrom:
            configMapKeyRef:
              name: mcpapi-config
              key: pgl-endpoint
        livenessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: mcpapi-service
spec:
  type: ClusterIP
  ports:
  - port: 80
    targetPort: 3000
  selector:
    app: mcpapi
```

### Environment Configuration

```bash
# .env.production
DATABASE_URL=postgresql://user:pass@db.example.com/mcpapi
REDIS_URL=redis://cache.example.com:6379
PGL_ENDPOINT=https://pgl.example.com/api
VEKLOM_ENDPOINT=https://veklom.example.com/api
LOG_LEVEL=info
NODE_ENV=production
MCPAPI_PORT=3000
MCPAPI_HOST=0.0.0.0
MCPAPI_WORKERS=4
```

---

## Operations

### Monitoring

```typescript
// src/monitoring/prometheus.ts
import prometheus from 'prom-client'

export const metrics = {
  requestsTotal: new prometheus.Counter({
    name: 'mcpapi_requests_total',
    help: 'Total requests processed',
    labelNames: ['status', 'capability']
  }),
  
  requestDuration: new prometheus.Histogram({
    name: 'mcpapi_request_duration_ms',
    help: 'Request processing duration',
    labelNames: ['capability'],
    buckets: [10, 50, 100, 500, 1000, 5000]
  }),
  
  trustScores: new prometheus.Gauge({
    name: 'mcpapi_trust_score',
    help: 'Agent trust scores',
    labelNames: ['agent_id']
  }),
  
  policyViolations: new prometheus.Counter({
    name: 'mcpapi_policy_violations_total',
    help: 'Total policy violations',
    labelNames: ['policy_id']
  })
}

// Usage in request handler
const startTime = Date.now()
try {
  const response = await runtime.handle(request)
  metrics.requestsTotal.inc({
    status: response.status,
    capability: request.capability_id
  })
  metrics.requestDuration.observe(
    Date.now() - startTime,
    { capability: request.capability_id }
  )
} catch (error) {
  metrics.requestsTotal.inc({
    status: 'error',
    capability: request.capability_id
  })
}
```

### Alerting

```yaml
# monitoring/alerts.yml
groups:
- name: MCPAPI Alerts
  rules:
  - alert: HighPolicyViolationRate
    expr: rate(mcpapi_policy_violations_total[5m]) > 0.1
    for: 5m
    annotations:
      summary: "High policy violation rate detected"
  
  - alert: LowTrustScore
    expr: mcpapi_trust_score < 30
    for: 10m
    annotations:
      summary: "Agent has low trust score"
  
  - alert: SlowRequests
    expr: histogram_quantile(0.95, rate(mcpapi_request_duration_ms_bucket[5m])) > 5000
    for: 5m
    annotations:
      summary: "95th percentile request latency > 5s"
```

### Debugging

```typescript
// src/debugging/tracer.ts
export class MCPAPITracer {
  // Trace single request
  traceRequest(request: MCPAPIRequest): TraceResult {
    const trace = {
      request_id: request.connection_id,
      steps: [],
      errors: []
    }
    
    // Log each step
    trace.steps.push({
      step: 'identity_resolution',
      duration_ms: 10,
      agent_id: request.agent_id
    })
    
    trace.steps.push({
      step: 'signature_verification',
      duration_ms: 5,
      valid: true
    })
    
    // ... more steps ...
    
    return trace
  }
}

// Usage
const tracer = new MCPAPITracer()
const trace = tracer.traceRequest(request)
console.log(JSON.stringify(trace, null, 2))
```

---

## Troubleshooting

### Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| 401 Unauthorized | Invalid signature | Verify agent public key, request signing |
| 403 Policy Denied | Policy rule match | Review policy rules, check agent permissions |
| 404 Not Found | Missing capability | Register capability, check endpoint |
| 429 Rate Limited | Exceeding rate limit | Check rate limit config, implement backoff |
| 500 Internal Error | Capability execution failed | Check capability endpoint, review logs |

---

## Next Steps

1. **Implement Phase 1** (weeks 1-2)
2. **Implement Phase 2** (weeks 3-4)
3. **Implement Phase 3** (weeks 5-6)
4. **Internal testing** (week 7)
5. **Design partner onboarding** (week 8)
6. **Production deployment** (week 9)

