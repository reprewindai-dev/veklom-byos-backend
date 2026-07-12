/**
 * MCPAPI Veklom Integration Layer
 * Version: 1.0.0
 *
 * Wires MCPAPI into Veklom infrastructure:
 * - Authority bundle validation
 * - Agent identity mapping
 * - PGL evidence generation
 * - Governance routing
 */

import * as crypto from "crypto";

// ============================================================================
// VEKLOM-SPECIFIC TYPES
// ============================================================================

interface AuthorityBundle {
  bundle_id: string;
  agent_id: string;
  issued_by: string;
  issued_at: string;
  expires_at: string;
  mcp_tools: string[]; // list of tool capability IDs
  permissions: {
    can_execute: boolean;
    can_delegate: boolean;
    can_read_ledger: boolean;
    can_write_ledger: boolean;
  };
  signature: string; // signed by issuer
}

interface VeklomAgent {
  agent_id: string;
  agent_name: string;
  mission_file: string; // path to agent mission definition
  authority_bundle_id: string;
  owner_id: string;
  created_at: string;
  public_key: string;
  governance_tier: "system" | "user" | "service";
  associated_mcp_servers: string[];
}

interface GnomLedgerEntry {
  id: string;
  agent_id: string;
  event_type: "created" | "executed" | "denied" | "escalated";
  capability_id: string;
  timestamp: string;
  evidence_hash: string;
  trust_delta: number;
  new_trust_score: number;
  metadata: Record<string, unknown>;
}

interface VeklomPGLEntry {
  who: string; // agent_id
  what: string; // capability_id
  when: string; // timestamp
  why: string; // policy_id
  how: string; // method (mcp|http|local)
  proof: string; // hash chain
  birth_certificate?: string; // agent genome hash
}

// ============================================================================
// VEKLOM INTEGRATION SERVICE
// ============================================================================

export class VeklomMCPAPIIntegration {
  private veklomAgents: Map<string, VeklomAgent> = new Map();
  private authorityBundles: Map<string, AuthorityBundle> = new Map();
  private gnomLedger: GnomLedgerEntry[] = [];
  private pglLedger: Map<string, VeklomPGLEntry> = new Map();
  private agentTrustScores: Map<string, number> = new Map();

  // ========== VEKLOM AGENT REGISTRATION ==========

  registerVeklomAgent(agent: VeklomAgent, authorityBundle: AuthorityBundle): boolean {
    // Verify authority bundle signature
    if (!this.verifyAuthorityBundle(authorityBundle)) {
      return false;
    }

    // Register agent
    this.veklomAgents.set(agent.agent_id, agent);
    this.authorityBundles.set(authorityBundle.bundle_id, authorityBundle);

    // Initialize trust score based on governance tier
    const initialTrust = this.getTrustForGovernanceTier(agent.governance_tier);
    this.agentTrustScores.set(agent.agent_id, initialTrust);

    // Log to gnom ledger
    this.logToGnomLedger({
      id: crypto.randomUUID(),
      agent_id: agent.agent_id,
      event_type: "created",
      capability_id: "system.registration",
      timestamp: new Date().toISOString(),
      evidence_hash: "",
      trust_delta: 0,
      new_trust_score: initialTrust,
      metadata: {
        governance_tier: agent.governance_tier,
        authority_bundle_id: authorityBundle.bundle_id,
      },
    });

    return true;
  }

  private verifyAuthorityBundle(bundle: AuthorityBundle): boolean {
    try {
      // In production: verify signature against issuer's public key
      // For now, accept all valid bundles
      const now = new Date();
      const expiresAt = new Date(bundle.expires_at);
      return expiresAt > now;
    } catch {
      return false;
    }
  }

  private getTrustForGovernanceTier(tier: "system" | "user" | "service"): number {
    switch (tier) {
      case "system":
        return 95; // high initial trust
      case "user":
        return 50; // neutral starting point
      case "service":
        return 75; // medium-high trust
      default:
        return 50;
    }
  }

  // ========== AUTHORITY BUNDLE VALIDATION ==========

  validateAgentAuthority(agent_id: string, capability_id: string): {
    authorized: boolean;
    authority_bundle?: AuthorityBundle;
    reason?: string;
  } {
    const agent = this.veklomAgents.get(agent_id);
    if (!agent) {
      return { authorized: false, reason: "Agent not registered" };
    }

    const bundle = this.authorityBundles.get(agent.authority_bundle_id);
    if (!bundle) {
      return { authorized: false, reason: "Authority bundle not found" };
    }

    // Check if bundle has expired
    const now = new Date();
    const expiresAt = new Date(bundle.expires_at);
    if (expiresAt < now) {
      return { authorized: false, reason: "Authority bundle expired" };
    }

    // Check if agent has permission to use this capability
    const hasPermission = bundle.mcp_tools.includes(capability_id) ||
      bundle.mcp_tools.includes("*");

    if (!hasPermission) {
      return {
        authorized: false,
        reason: `Capability ${capability_id} not in authority bundle`,
        authority_bundle: bundle,
      };
    }

    return { authorized: true, authority_bundle: bundle };
  }

  // ========== MISSION FILE VALIDATION ==========

  validateMissionFile(agent_id: string): {
    valid: boolean;
    mission_file?: string;
    reason?: string;
  } {
    const agent = this.veklomAgents.get(agent_id);
    if (!agent) {
      return { valid: false, reason: "Agent not found" };
    }

    // In production: load + validate mission file
    // For now: assume mission files are pre-validated

    return {
      valid: true,
      mission_file: agent.mission_file,
    };
  }

  // ========== GOVERNANCE ROUTING ==========

  routeToGovernanceLayer(
    agent_id: string,
    capability_id: string,
    action: string,
    request_context: Record<string, unknown>
  ): {
    route: "allowed" | "requires_approval" | "requires_escalation" | "denied";
    approver?: string;
    escalation_path?: string[];
    reason?: string;
  } {
    const agent = this.veklomAgents.get(agent_id);
    if (!agent) {
      return {
        route: "denied",
        reason: "Agent not found",
      };
    }

    const trust = this.agentTrustScores.get(agent_id) || 50;

    // System agents can do anything
    if (agent.governance_tier === "system") {
      return { route: "allowed" };
    }

    // Check trust thresholds
    if (trust < 30) {
      return {
        route: "requires_escalation",
        escalation_path: ["security-team", "commander-agent"],
        reason: "Low trust score",
      };
    }

    if (trust < 50) {
      return {
        route: "requires_approval",
        approver: "human-approver",
        reason: "Medium trust - requires human approval",
      };
    }

    // Check if capability requires approval
    if (action.includes("delete") || action.includes("transfer")) {
      return {
        route: "requires_approval",
        approver: "human-approver",
        reason: "Sensitive action requires approval",
      };
    }

    return { route: "allowed" };
  }

  // ========== PGL INTEGRATION ==========

  async registerToPGL(
    agent_id: string,
    capability_id: string,
    action: string,
    method: "mcp" | "http" | "local",
    result: "success" | "denied" | "error",
    evidence_hash: string
  ): Promise<string> {
    const agent = this.veklomAgents.get(agent_id);
    if (!agent) {
      return "";
    }

    const pglEntry: VeklomPGLEntry = {
      who: agent_id,
      what: capability_id,
      when: new Date().toISOString(),
      why: action,
      how: method,
      proof: evidence_hash,
      birth_certificate: this.generateBirthCertificate(agent),
    };

    // Keep local copy for in-memory reads
    const entryHash = this.hashPGLEntry(pglEntry);
    this.pglLedger.set(entryHash, pglEntry);

    // POST to live gnomledger
    const pglBaseUrl = process.env.PGL_API_URL || "https://api.veklom.com";
    const apiKey = process.env.PGL_API_KEY || "";
    
    // Map VeklomPGLEntry to LedgerEventCreate schema
    const payload = {
      agent_id: agent_id,
      event_type: "custom", // generic action
      actor: agent.owner_id || "system",
      summary: `PGL execution: ${action} on ${capability_id}`,
      details: pglEntry,
      idempotency_key: entryHash,
    };

    try {
      const response = await fetch(`${pglBaseUrl}/api/v1/ledger/events`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-api-key": apiKey,
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        console.error(`PGL sync failed: ${response.status} ${response.statusText}`);
      }
    } catch (e) {
      console.error(`PGL sync error:`, e);
    }

    return entryHash;
  }

  private generateBirthCertificate(agent: VeklomAgent): string {
    // Agent birth certificate = hash of identity + creation timestamp
    return crypto
      .createHash("sha256")
      .update(JSON.stringify({
        agent_id: agent.agent_id,
        created_at: agent.created_at,
        public_key: agent.public_key,
      }))
      .digest("hex");
  }

  private hashPGLEntry(entry: VeklomPGLEntry): string {
    return crypto
      .createHash("sha256")
      .update(JSON.stringify(entry))
      .digest("hex");
  }

  getPGLEntry(hash: string): VeklomPGLEntry | undefined {
    return this.pglLedger.get(hash);
  }

  // ========== GNOM LEDGER (LOCAL AGENT LEDGER) ==========

  private logToGnomLedger(entry: GnomLedgerEntry): void {
    this.gnomLedger.push(entry);
  }

  recordAgentAction(
    agent_id: string,
    capability_id: string,
    action: string,
    result: "success" | "denied" | "error",
    evidence_hash: string,
    trust_delta: number
  ): void {
    const currentTrust = this.agentTrustScores.get(agent_id) || 50;
    const newTrust = Math.max(0, Math.min(100, currentTrust + trust_delta));

    this.agentTrustScores.set(agent_id, newTrust);

    const entry: GnomLedgerEntry = {
      id: crypto.randomUUID(),
      agent_id,
      event_type: result === "success" ? "executed" : result === "denied" ? "denied" : "executed",
      capability_id,
      timestamp: new Date().toISOString(),
      evidence_hash,
      trust_delta,
      new_trust_score: newTrust,
      metadata: {
        action,
        result,
      },
    };

    this.logToGnomLedger(entry);
  }

  getGnomLedger(): GnomLedgerEntry[] {
    return this.gnomLedger;
  }

  getGnomLedgerForAgent(agent_id: string): GnomLedgerEntry[] {
    return this.gnomLedger.filter((entry) => entry.agent_id === agent_id);
  }

  // ========== COMMANDER AGENT OPERATIONS ==========

  isCommanderAgent(agent_id: string): boolean {
    return agent_id === "agent-000"; // Commander agent
  }

  /**
   * Commander can query any agent's state
   */
  getAgentState(commander_id: string, target_agent_id: string): {
    agent_id: string;
    trust_score: number;
    recent_actions: GnomLedgerEntry[];
    authority_bundle?: AuthorityBundle;
    status: "active" | "inactive" | "suspended";
  } | null {
    if (!this.isCommanderAgent(commander_id)) {
      return null; // Only Commander can query agent state
    }

    const agent = this.veklomAgents.get(target_agent_id);
    if (!agent) {
      return null;
    }

    const trust = this.agentTrustScores.get(target_agent_id) || 50;
    const recentActions = this.getGnomLedgerForAgent(target_agent_id).slice(-10);
    const bundle = this.authorityBundles.get(agent.authority_bundle_id);

    return {
      agent_id: target_agent_id,
      trust_score: trust,
      recent_actions: recentActions,
      authority_bundle: bundle,
      status: "active", // simplified
    };
  }

  /**
   * Commander can issue governance decisions
   */
  issueGovernanceDecision(
    commander_id: string,
    target_agent_id: string,
    decision: "approve" | "deny" | "escalate" | "suspend",
    reason: string
  ): boolean {
    if (!this.isCommanderAgent(commander_id)) {
      return false;
    }

    const agent = this.veklomAgents.get(target_agent_id);
    if (!agent) {
      return false;
    }

    // Apply decision
    switch (decision) {
      case "approve":
        this.agentTrustScores.set(target_agent_id, 85);
        break;
      case "deny":
        this.agentTrustScores.set(target_agent_id, 30);
        break;
      case "escalate":
        // Route to higher-level decision
        break;
      case "suspend":
        // Mark agent as suspended
        break;
    }

    return true;
  }

  // ========== COMPLIANCE & AUDIT ==========

  getComplianceReport(
    start_date: string,
    end_date: string,
    agent_id?: string
  ): {
    total_interactions: number;
    authorized_count: number;
    denied_count: number;
    escalated_count: number;
    average_trust_score: number;
    agents_report: Array<{
      agent_id: string;
      interactions: number;
      trust_score: number;
      violations: number;
    }>;
  } {
    const start = new Date(start_date);
    const end = new Date(end_date);

    const filteredLedger = this.gnomLedger.filter((entry) => {
      const entryTime = new Date(entry.timestamp);
      const matchesDate = entryTime >= start && entryTime <= end;
      const matchesAgent = !agent_id || entry.agent_id === agent_id;
      return matchesDate && matchesAgent;
    });

    const authorized = filteredLedger.filter((e) => e.event_type === "executed").length;
    const denied = filteredLedger.filter((e) => e.event_type === "denied").length;
    const escalated = filteredLedger.filter((e) => e.event_type === "escalated").length;

    const agentScores = new Map<string, number>();
    const agentInteractions = new Map<string, number>();

    filteredLedger.forEach((entry) => {
      agentScores.set(entry.agent_id, entry.new_trust_score);
      agentInteractions.set(entry.agent_id, (agentInteractions.get(entry.agent_id) || 0) + 1);
    });

    const avgTrust =
      Array.from(agentScores.values()).reduce((a, b) => a + b, 0) /
      Math.max(1, agentScores.size);

    return {
      total_interactions: filteredLedger.length,
      authorized_count: authorized,
      denied_count: denied,
      escalated_count: escalated,
      average_trust_score: avgTrust,
      agents_report: Array.from(agentScores.entries()).map(([id, trust]) => ({
        agent_id: id,
        interactions: agentInteractions.get(id) || 0,
        trust_score: trust,
        violations: filteredLedger.filter((e) => e.agent_id === id && e.event_type === "denied")
          .length,
      })),
    };
  }

  // ========== UTILITY ==========

  getAgent(agent_id: string): VeklomAgent | undefined {
    return this.veklomAgents.get(agent_id);
  }

  getTrustScore(agent_id: string): number {
    return this.agentTrustScores.get(agent_id) || 50;
  }

  getAllAgents(): VeklomAgent[] {
    return Array.from(this.veklomAgents.values());
  }
}

// ============================================================================
// EXAMPLE USAGE
// ============================================================================

function main() {
  const integration = new VeklomMCPAPIIntegration();

  // Register system agent (Commander)
  const commanderAgent: VeklomAgent = {
    agent_id: "agent-000",
    agent_name: "Commander",
    mission_file: "missions/commander.json",
    authority_bundle_id: "bundle-system-001",
    owner_id: "system",
    created_at: new Date().toISOString(),
    public_key: "commander-public-key",
    governance_tier: "system",
    associated_mcp_servers: ["auth", "governance", "audit"],
  };

  const commanderBundle: AuthorityBundle = {
    bundle_id: "bundle-system-001",
    agent_id: "agent-000",
    issued_by: "system",
    issued_at: new Date().toISOString(),
    expires_at: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString(),
    mcp_tools: ["*"], // can use all tools
    permissions: {
      can_execute: true,
      can_delegate: true,
      can_read_ledger: true,
      can_write_ledger: true,
    },
    signature: "system-signed",
  };

  integration.registerVeklomAgent(commanderAgent, commanderBundle);

  // Register user agent
  const userAgent: VeklomAgent = {
    agent_id: "agent-001",
    agent_name: "DataProcessor",
    mission_file: "missions/data-processor.json",
    authority_bundle_id: "bundle-user-001",
    owner_id: "user-123",
    created_at: new Date().toISOString(),
    public_key: "user-public-key",
    governance_tier: "user",
    associated_mcp_servers: ["search", "database"],
  };

  const userBundle: AuthorityBundle = {
    bundle_id: "bundle-user-001",
    agent_id: "agent-001",
    issued_by: "system",
    issued_at: new Date().toISOString(),
    expires_at: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
    mcp_tools: ["search", "database.read"],
    permissions: {
      can_execute: true,
      can_delegate: false,
      can_read_ledger: true,
      can_write_ledger: false,
    },
    signature: "system-signed",
  };

  integration.registerVeklomAgent(userAgent, userBundle);

  // Validate authority
  console.log("Validate authority:");
  console.log(integration.validateAgentAuthority("agent-001", "search"));

  // Route to governance
  console.log("\nRoute to governance:");
  console.log(
    integration.routeToGovernanceLayer(
      "agent-001",
      "database.write",
      "delete",
      {}
    )
  );

  // Record action
  integration.recordAgentAction(
    "agent-001",
    "search",
    "execute",
    "success",
    "evidence-hash-001",
    2
  );

  // Get gnom ledger
  console.log("\nGnom ledger for agent-001:");
  console.log(integration.getGnomLedgerForAgent("agent-001"));

  // Commander queries agent state
  console.log("\nCommander queries agent state:");
  console.log(integration.getAgentState("agent-000", "agent-001"));

  // Compliance report
  console.log("\nCompliance report:");
  const report = integration.getComplianceReport(
    new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
    new Date().toISOString()
  );
  console.log(JSON.stringify(report, null, 2));
}

// Uncomment to run:
// main();
