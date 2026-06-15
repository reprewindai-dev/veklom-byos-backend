/**
 * MCPAPI Reference Runtime
 * Version: 1.0.0
 * 
 * Provider-agnostic protocol for governed machine-to-machine capability exchange.
 * Every interaction carries identity, policy, trust, and evidence as first-class citizens.
 */

import * as crypto from "crypto";

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

export interface AgentIdentity {
  agent_id: string;
  agent_name: string;
  owner_id: string;
  public_key: string; // base64
  capabilities_manifest: string; // ipfs hash
  created_at: string; // iso8601
  identity_proof: string; // signed hash
  metadata: {
    version: string;
    framework: string;
    inference_provider: "claude" | "gpt" | "gemini" | "llama" | "other";
    tier: "system" | "user" | "service";
  };
}

export interface CapabilityIdentity {
  capability_id: string;
  capability_name: string;
  provider_id: string;
  endpoint: string;
  input_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
  public_key: string;
  created_at: string;
  version: string;
  identity_proof: string;
  metadata: {
    category: "tool" | "service" | "agent" | "database" | "human" | "sensor";
    requires_approval: boolean;
    cost: "carbon" | "credits" | "payment" | "free";
    rate_limit: number; // requests per minute
  };
}

export interface PolicyRule {
  rule_id: string;
  effect: "allow" | "deny";
  principal: string; // agent-id, role, or *
  action: string; // capability-id, category, or *
  conditions: {
    time_window?: [string, string]; // [start, end] iso8601
    rate_limit?: number;
    requires_approval?: boolean;
    approval_path?: string;
    context_required?: string[];
    trust_minimum?: number;
  };
}

export interface Policy {
  policy_id: string;
  policy_name: string;
  version: string;
  created_by: string;
  created_at: string;
  rules: PolicyRule[];
  metadata: {
    enforcement_mode: "strict" | "warn" | "audit-only";
    escalation_threshold: number;
    audit_trail: boolean;
    immutable?: boolean;
  };
}

export interface MCPAPIRequest {
  connection_id: string;
  agent_id: string;
  agent_signature: string;
  capability_id: string;
  action: string;
  input: Record<string, unknown>;
  context: {
    trace_id?: string;
    user_context?: Record<string, unknown>;
    audit_tags?: string[];
  };
  timestamp: string;
}

export interface Evidence {
  evidence_id: string;
  connection_id: string;
  pgl_hash: string;
  timestamp: string;
  who: {
    agent_id: string;
    agent_public_key: string;
    owner_id: string;
  };
  what: {
    capability_id: string;
    capability_name: string;
    action: string;
  };
  when: {
    requested_at: string;
    executed_at: string;
    completed_at: string;
  };
  why: {
    policy_applied: string;
    policy_version: string;
    authorization_proof: string;
    request_context: string; // encrypted
  };
  how: {
    method: "mcp" | "http" | "local";
    endpoint: string;
    retry_count: number;
  };
  result: {
    status: "authorized" | "denied" | "error";
    output_hash: string;
    output_size: number;
    execution_time_ms: number;
  };
  compliance: {
    audit_logged: boolean;
    regulatory_category: string;
    data_classification: "public" | "internal" | "confidential" | "restricted";
    retention_policy: string;
  };
  previous_hash?: string; // for chain integrity
}

export interface TrustScore {
  agent_id: string;
  score: number; // 0-100
  success_rate: number;
  policy_adherence: number;
  denial_frequency: number;
  escalation_events: number;
  last_updated: string;
}

export interface MCPAPIResponse {
  connection_id: string;
  status: "authorized" | "denied" | "error";
  evidence_hash?: string;
  result?: {
    output: Record<string, unknown>;
    output_hash: string;
    execution_time_ms: number;
  };
  error?: {
    code: string;
    message: string;
    remediation?: Record<string, unknown>;
  };
  metadata: {
    trust_delta: number;
    new_trust_score: number;
    audit_logged: boolean;
  };
}

// ============================================================================
// CORE MCPAPI RUNTIME
// ============================================================================

export class MCPAPIRuntime {
  public agents: Map<string, AgentIdentity> = new Map();
  public capabilities: Map<string, CapabilityIdentity> = new Map();
  public policies: Map<string, Policy> = new Map();
  public trustScores: Map<string, TrustScore> = new Map();
  public auditLog: Evidence[] = [];
  public pglLedger: Map<string, Evidence> = new Map();
  public requestCounts: Map<string, number> = new Map();
  public lastRequestTime: Map<string, number> = new Map();
  private readonly encryptionKey = crypto.randomBytes(32);

  // ========== IDENTITY MANAGEMENT ==========

  registerAgent(agent: AgentIdentity): boolean {
    if (this.agents.has(agent.agent_id)) {
      return false;
    }
    this.agents.set(agent.agent_id, agent);
    // Initialize trust score
    this.trustScores.set(agent.agent_id, {
      agent_id: agent.agent_id,
      score: 50, // neutral starting point
      success_rate: 1.0,
      policy_adherence: 1.0,
      denial_frequency: 0,
      escalation_events: 0,
      last_updated: new Date().toISOString(),
    });
    return true;
  }

  registerCapability(capability: CapabilityIdentity): boolean {
    if (this.capabilities.has(capability.capability_id)) {
      return false;
    }
    this.capabilities.set(capability.capability_id, capability);
    return true;
  }

  getAgent(agent_id: string): AgentIdentity | undefined {
    return this.agents.get(agent_id);
  }

  getCapability(capability_id: string): CapabilityIdentity | undefined {
    return this.capabilities.get(capability_id);
  }

  // ========== POLICY MANAGEMENT ==========

  registerPolicy(policy: Policy): boolean {
    if (this.policies.has(policy.policy_id)) {
      return false;
    }
    this.policies.set(policy.policy_id, policy);
    return true;
  }

  getPolicy(policy_id: string): Policy | undefined {
    return this.policies.get(policy_id);
  }

  // ========== IDENTITY VERIFICATION ==========

  public verifySignature(
    agent: AgentIdentity,
    request: MCPAPIRequest
  ): boolean {
    try {
      const messageBuffer = Buffer.from(
        [
          request.connection_id,
          request.agent_id,
          request.capability_id,
          request.action,
          JSON.stringify(request.input),
          request.timestamp,
        ].join("")
      );

      const publicKey = Buffer.from(agent.public_key, "base64");
      const signatureBuffer = Buffer.from(request.agent_signature, "base64");

      return crypto
        .createVerify("SHA256")
        .update(messageBuffer)
        .verify(publicKey, signatureBuffer);
    } catch (error) {
      return false;
    }
  }

  // ========== POLICY EVALUATION ==========

  private evaluatePolicy(
    agent_id: string,
    capability_id: string,
    policies: Policy[]
  ): {
    authorized: boolean;
    policy_id?: string;
    requires_approval?: boolean;
    approval_path?: string;
  } {
    // Iterate through policies in order
    for (const policy of policies) {
      for (const rule of policy.rules) {
        // Check principal match
        const principalMatches =
          rule.principal === "*" ||
          rule.principal === agent_id ||
          rule.principal.startsWith("role:");

        if (!principalMatches) continue;

        // Check action match
        const actionMatches =
          rule.action === "*" ||
          rule.action === capability_id ||
          rule.action.startsWith("category:");

        if (!actionMatches) continue;

        // Check conditions
        const conditionsPass = this.checkConditions(
          rule.conditions,
          agent_id,
          capability_id
        );

        if (!conditionsPass) continue;

        // Match found
        if (rule.effect === "allow") {
          return {
            authorized: true,
            policy_id: policy.policy_id,
            requires_approval: rule.conditions.requires_approval,
            approval_path: rule.conditions.approval_path,
          };
        } else {
          return {
            authorized: false,
            policy_id: policy.policy_id,
          };
        }
      }
    }

    // No matching rule found - deny by default
    return { authorized: false };
  }

  private checkConditions(
    conditions: PolicyRule["conditions"],
    agent_id: string,
    capability_id: string
  ): boolean {
    // Check time window
    if (conditions.time_window) {
      const now = new Date();
      const [start, end] = conditions.time_window;
      if (now < new Date(start) || now > new Date(end)) {
        return false;
      }
    }

    // Check rate limit
    if (conditions.rate_limit) {
      const now = Date.now();
      const lastRequest = this.lastRequestTime.get(agent_id) || 0;
      const timeSinceLastRequest = now - lastRequest;
      const minTimeBetweenRequests = (60 * 1000) / conditions.rate_limit;

      if (timeSinceLastRequest < minTimeBetweenRequests) {
        return false;
      }
    }

    // Check trust minimum
    if (conditions.trust_minimum !== undefined) {
      const trust = this.trustScores.get(agent_id);
      if (!trust || trust.score < conditions.trust_minimum) {
        return false;
      }
    }

    return true;
  }

  // ========== TRUST COMPUTATION ==========

  private computeTrustScore(agent_id: string): TrustScore {
    const current = this.trustScores.get(agent_id);
    if (!current) {
      return {
        agent_id,
        score: 50,
        success_rate: 1.0,
        policy_adherence: 1.0,
        denial_frequency: 0,
        escalation_events: 0,
        last_updated: new Date().toISOString(),
      };
    }

    const score =
      current.success_rate * 0.4 +
      current.policy_adherence * 0.3 +
      (1 - current.denial_frequency) * 0.2 +
      (1 - current.escalation_events) * 0.1;

    return {
      agent_id,
      score: Math.max(0, Math.min(100, score * 100)),
      success_rate: current.success_rate,
      policy_adherence: current.policy_adherence,
      denial_frequency: current.denial_frequency,
      escalation_events: current.escalation_events,
      last_updated: new Date().toISOString(),
    };
  }

  private updateTrustScore(
    agent_id: string,
    delta: number
  ): TrustScore {
    const current = this.trustScores.get(agent_id) || {
      agent_id,
      score: 50,
      success_rate: 1.0,
      policy_adherence: 1.0,
      denial_frequency: 0,
      escalation_events: 0,
      last_updated: new Date().toISOString(),
    };

    current.score = Math.max(0, Math.min(100, current.score + delta));
    current.last_updated = new Date().toISOString();

    this.trustScores.set(agent_id, current);
    return current;
  }

  // ========== EVIDENCE GENERATION ==========

  private generateEvidence(
    request: MCPAPIRequest,
    agent: AgentIdentity,
    capability: CapabilityIdentity,
    status: "authorized" | "denied" | "error",
    result?: Record<string, unknown>,
    error?: { code: string; message: string },
    policy_applied?: string
  ): Evidence {
    let resolvedPolicyId = policy_applied;
    if (!resolvedPolicyId) {
      const evaluation = this.evaluatePolicy(
        request.agent_id,
        capability.capability_id,
        Array.from(this.policies.values())
      );
      resolvedPolicyId = evaluation.policy_id || "default-deny-policy";
    }

    const evidence: Evidence = {
      evidence_id: crypto.randomUUID(),
      connection_id: request.connection_id,
      pgl_hash: "", // Will be filled by PGL client
      timestamp: new Date().toISOString(),
      who: {
        agent_id: agent.agent_id,
        agent_public_key: agent.public_key,
        owner_id: agent.owner_id,
      },
      what: {
        capability_id: capability.capability_id,
        capability_name: capability.capability_name,
        action: request.action,
      },
      when: {
        requested_at: request.timestamp,
        executed_at: new Date().toISOString(),
        completed_at: new Date().toISOString(),
      },
      why: {
        policy_applied: resolvedPolicyId,
        policy_version: "1.0.0",
        authorization_proof: request.agent_signature,
        request_context: this.encrypt(JSON.stringify(request.context)),
      },
      how: {
        method: "mcp",
        endpoint: capability.endpoint,
        retry_count: 0,
      },
      result: {
        status,
        output_hash: result
          ? crypto
              .createHash("sha256")
              .update(JSON.stringify(result))
              .digest("base64")
          : "",
        output_size: result ? JSON.stringify(result).length : 0,
        execution_time_ms: 0,
      },
      compliance: {
        audit_logged: true,
        regulatory_category: "standard",
        data_classification: "internal",
        retention_policy: "90-days",
      },
      previous_hash: this.getLastEvidenceHash(),
    };

    return evidence;
  }

  private getLastEvidenceHash(): string {
    if (this.auditLog.length === 0) return "";
    const lastEvidence = this.auditLog[this.auditLog.length - 1];
    return crypto
      .createHash("sha256")
      .update(JSON.stringify(lastEvidence))
      .digest("base64");
  }

  private registerEvidenceToPGL(evidence: Evidence): string {
    // Simulate PGL registration
    const pgl_hash = crypto
      .createHash("sha256")
      .update(JSON.stringify(evidence))
      .digest("base64");

    evidence.pgl_hash = pgl_hash;
    this.pglLedger.set(pgl_hash, evidence);
    return pgl_hash;
  }

  // ========== REQUEST EXECUTION ==========

  async processRequest(request: MCPAPIRequest): Promise<MCPAPIResponse> {
    const startTime = Date.now();

    // Step 1: Identity Resolution
    const agent = this.getAgent(request.agent_id);
    if (!agent) {
      return {
        connection_id: request.connection_id,
        status: "error",
        metadata: {
          trust_delta: 0,
          new_trust_score: 50,
          audit_logged: true,
        },
        error: {
          code: "401",
          message: "Agent not found",
        },
      };
    }

    // Step 2: Signature Verification
    if (!this.verifySignature(agent, request)) {
      return {
        connection_id: request.connection_id,
        status: "error",
        metadata: {
          trust_delta: -5,
          new_trust_score: this.updateTrustScore(request.agent_id, -5).score,
          audit_logged: true,
        },
        error: {
          code: "401",
          message: "Signature verification failed",
        },
      };
    }

    // Step 3: Get Capability
    const capability = this.getCapability(request.capability_id);
    if (!capability) {
      const evidence = this.generateEvidence(
        request,
        agent,
        { capability_id: request.capability_id } as CapabilityIdentity,
        "error"
      );
      this.registerEvidenceToPGL(evidence);
      this.auditLog.push(evidence);

      return {
        connection_id: request.connection_id,
        status: "error",
        evidence_hash: evidence.pgl_hash,
        metadata: {
          trust_delta: 0,
          new_trust_score: this.trustScores.get(request.agent_id)?.score || 50,
          audit_logged: true,
        },
        error: {
          code: "404",
          message: "Capability not found",
        },
      };
    }

    // Step 4: Policy Evaluation
    const policies = Array.from(this.policies.values());
    const policyResult = this.evaluatePolicy(
      request.agent_id,
      request.capability_id,
      policies
    );

    if (!policyResult.authorized) {
      const evidence = this.generateEvidence(
        request,
        agent,
        capability,
        "denied",
        undefined,
        undefined,
        policyResult.policy_id
      );
      this.registerEvidenceToPGL(evidence);
      this.auditLog.push(evidence);

      const trustDelta = -5;
      const newTrust = this.updateTrustScore(request.agent_id, trustDelta);

      return {
        connection_id: request.connection_id,
        status: "denied",
        evidence_hash: evidence.pgl_hash,
        metadata: {
          trust_delta: trustDelta,
          new_trust_score: newTrust.score,
          audit_logged: true,
        },
        error: {
          code: "403",
          message: "Policy denied",
          remediation: {
            policy_id: policyResult.policy_id,
            requires_approval: policyResult.requires_approval,
            approval_path: policyResult.approval_path,
          },
        },
      };
    }

    // Step 5: Execute Capability (simulated)
    const result = { message: "Capability executed successfully" };
    const executionTime = Date.now() - startTime;

    // Step 6: Generate Evidence
    const evidence = this.generateEvidence(
      request,
      agent,
      capability,
      "authorized",
      result,
      undefined,
      policyResult.policy_id
    );
    evidence.result.execution_time_ms = executionTime;

    // Step 7: Register to PGL
    const pgl_hash = this.registerEvidenceToPGL(evidence);
    this.auditLog.push(evidence);

    // Step 8: Update Trust Score
    const trustDelta = 2; // success bonus
    const newTrust = this.updateTrustScore(request.agent_id, trustDelta);

    return {
      connection_id: request.connection_id,
      status: "authorized",
      evidence_hash: pgl_hash,
      result: {
        output: result,
        output_hash: evidence.result.output_hash,
        execution_time_ms: executionTime,
      },
      metadata: {
        trust_delta: trustDelta,
        new_trust_score: newTrust.score,
        audit_logged: true,
      },
    };
  }

  // ========== CAPABILITY DISCOVERY ==========

  discoverCapabilities(agent_id: string): Array<{
    capability_id: string;
    name: string;
    authorized: boolean;
    trust_required: number;
    trust_current: number;
    approval_required: boolean;
  }> {
    const agent = this.getAgent(agent_id);
    if (!agent) return [];

    const trust = this.trustScores.get(agent_id);
    const currentTrust = trust?.score || 50;
    const policies = Array.from(this.policies.values());

    return Array.from(this.capabilities.values()).map((cap) => {
      // Evaluate policy to check authorization
      const policyEvaluation = this.evaluatePolicy(
        agent_id,
        cap.capability_id,
        policies
      );

      // Find required trust score from matching rules
      let trust_required = 0;
      let approval_required = cap.metadata.requires_approval;

      for (const policy of policies) {
        for (const rule of policy.rules) {
          const principalMatches =
            rule.principal === "*" ||
            rule.principal === agent_id ||
            rule.principal.startsWith("role:");
          const actionMatches =
            rule.action === "*" ||
            rule.action === cap.capability_id ||
            rule.action.startsWith("category:");

          if (principalMatches && actionMatches) {
            if (rule.conditions.trust_minimum !== undefined) {
              trust_required = Math.max(trust_required, rule.conditions.trust_minimum);
            }
            if (rule.conditions.requires_approval !== undefined) {
              approval_required = approval_required || rule.conditions.requires_approval;
            }
          }
        }
      }

      return {
        capability_id: cap.capability_id,
        name: cap.capability_name,
        authorized: policyEvaluation.authorized,
        trust_required,
        trust_current: currentTrust,
        approval_required,
      };
    });
  }

  // ========== AUDIT & COMPLIANCE ==========

  getAuditLog(): Evidence[] {
    return this.auditLog;
  }

  getEvidenceByHash(hash: string): Evidence | undefined {
    return this.pglLedger.get(hash);
  }

  replayInteraction(evidence_hash: string): {
    evidence: Evidence | undefined;
    chain: Evidence[];
  } {
    const evidence = this.pglLedger.get(evidence_hash);
    if (!evidence) {
      return { evidence: undefined, chain: [] };
    }

    const chain: Evidence[] = [evidence];
    let current = evidence;

    // Walk back through the chain
    while (current.previous_hash) {
      const prev = this.pglLedger.get(current.previous_hash);
      if (!prev) break;
      chain.unshift(prev);
      current = prev;
    }

    return { evidence, chain };
  }

  // ========== UTILITY ==========

  private encrypt(data: string): string {
    try {
      const iv = crypto.randomBytes(12);
      const cipher = crypto.createCipheriv("aes-256-gcm", this.encryptionKey, iv);
      let encrypted = cipher.update(data, "utf8", "hex");
      encrypted += cipher.final("hex");
      const authTag = cipher.getAuthTag().toString("hex");
      return [iv.toString("hex"), authTag, encrypted].join(":");
    } catch (error) {
      return Buffer.from(data).toString("base64");
    }
  }

  private decrypt(encrypted: string): string {
    try {
      const [ivHex, authTagHex, encryptedHex] = encrypted.split(":");
      if (!ivHex || !authTagHex || !encryptedHex) {
        return Buffer.from(encrypted, "base64").toString("utf-8");
      }
      const iv = Buffer.from(ivHex, "hex");
      const authTag = Buffer.from(authTagHex, "hex");
      const decipher = crypto.createDecipheriv("aes-256-gcm", this.encryptionKey, iv);
      decipher.setAuthTag(authTag);
      let decrypted = decipher.update(encryptedHex, "hex", "utf8");
      decrypted += decipher.final("utf8");
      return decrypted;
    } catch (error) {
      return Buffer.from(encrypted, "base64").toString("utf-8");
    }
  }

  getTrustScore(agent_id: string): TrustScore | undefined {
    return this.trustScores.get(agent_id);
  }

  public update(agent_id: string, delta: number): TrustScore {
    return this.updateTrustScore(agent_id, delta);
  }

  public generate(
    request: MCPAPIRequest,
    agent: AgentIdentity,
    capability: CapabilityIdentity,
    status: "authorized" | "denied" | "error",
    result?: Record<string, unknown>,
    error?: { code: string; message: string },
    policy_applied?: string
  ): Evidence {
    return this.generateEvidence(request, agent, capability, status, result, error, policy_applied);
  }

  public async commit(evidence: Evidence): Promise<string> {
    return this.registerEvidenceToPGL(evidence);
  }
}

// ============================================================================
// EXAMPLE USAGE
// ============================================================================

async function main() {
  const runtime = new MCPAPIRuntime();

  // Register an agent
  const agent: AgentIdentity = {
    agent_id: "agent-001",
    agent_name: "TestAgent",
    owner_id: "owner-001",
    public_key: Buffer.from("test-public-key").toString("base64"),
    capabilities_manifest: "ipfs://QmTest",
    created_at: new Date().toISOString(),
    identity_proof: "signed-proof",
    metadata: {
      version: "1.0.0",
      framework: "Veklom",
      inference_provider: "claude",
      tier: "user",
    },
  };
  runtime.registerAgent(agent);

  // Register a capability
  const capability: CapabilityIdentity = {
    capability_id: "cap-001",
    capability_name: "SearchTool",
    provider_id: "provider-001",
    endpoint: "mcp://provider/search",
    input_schema: { type: "object", properties: { query: { type: "string" } } },
    output_schema: { type: "object", properties: { results: { type: "array" } } },
    public_key: Buffer.from("capability-public-key").toString("base64"),
    created_at: new Date().toISOString(),
    version: "1.0.0",
    identity_proof: "signed-proof",
    metadata: {
      category: "tool",
      requires_approval: false,
      cost: "free",
      rate_limit: 100,
    },
  };
  runtime.registerCapability(capability);

  // Register a policy
  const policy: Policy = {
    policy_id: "policy-001",
    policy_name: "DefaultPolicy",
    version: "1.0.0",
    created_by: "admin",
    created_at: new Date().toISOString(),
    rules: [
      {
        rule_id: "rule-001",
        effect: "allow",
        principal: "*",
        action: "*",
        conditions: { trust_minimum: 30 },
      },
    ],
    metadata: {
      enforcement_mode: "strict",
      escalation_threshold: 100,
      audit_trail: true,
    },
  };
  runtime.registerPolicy(policy);

  // Create a request (in production, this would be signed)
  const request: MCPAPIRequest = {
    connection_id: crypto.randomUUID(),
    agent_id: "agent-001",
    agent_signature: "dummy-signature",
    capability_id: "cap-001",
    action: "execute",
    input: { query: "test" },
    context: { audit_tags: ["test"] },
    timestamp: new Date().toISOString(),
  };

  // Process request
  const response = await runtime.processRequest(request);
  console.log("Response:", JSON.stringify(response, null, 2));

  // Discover capabilities
  const discovered = runtime.discoverCapabilities("agent-001");
  console.log("Discovered Capabilities:", discovered);

  // Get audit log
  const auditLog = runtime.getAuditLog();
  console.log("Audit Log Length:", auditLog.length);
}

// Uncomment to run:
// main().catch(console.error);
