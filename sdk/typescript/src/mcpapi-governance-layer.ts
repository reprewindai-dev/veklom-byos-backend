/**
 * MCPAPI Governance Composition Layer
 * Version: 2.0.0
 *
 * Policy composition & governance:
 * - Policy merging (system + owner + runtime)
 * - Conflict detection & resolution
 * - Temporal policy composition
 * - Agent lifecycle management
 * - Effective permissions calculation
 */

import * as crypto from "crypto";

// ============================================================================
// GOVERNANCE LAYER TYPES
// ============================================================================

export interface PolicyComposition {
  composition_id: string;
  agent_id: string;
  capability_id: string;
  timestamp: string;
  system_policy?: any; // Policy
  owner_policy?: any; // Policy
  runtime_policy?: any; // Policy
  temporal_policies?: any[]; // time-based policies
  effective_policy: any; // merged result
  conflicts_detected: PolicyConflict[];
  resolution_method: "system-wins" | "owner-wins" | "most-restrictive" | "union" | "intersection";
  is_valid: boolean;
  affected_permissions: string[];
  evidence_hash: string;
}

export interface PolicyConflict {
  conflict_id: string;
  conflict_type:
    | "allow-deny"
    | "rate-limit-mismatch"
    | "trust-requirement-mismatch"
    | "time-window-overlap"
    | "approval-conflict";
  source1: string; // policy_id
  source2: string; // policy_id
  conflicting_field: string;
  value1: any;
  value2: any;
  severity: "low" | "medium" | "high" | "critical";
  resolution: string;
  requires_admin_review: boolean;
  evidence_hash: string;
}

export interface TemporalPolicyLayer {
  policy_id: string;
  time_windows: Array<{
    window_name: string;
    start: string; // iso8601
    end: string; // iso8601
    policy: any;
    rate_limit?: number;
    trust_required?: number;
    requires_approval?: boolean;
    escalation_needed?: boolean;
  }>;
  holiday_adjustments?: Map<string, any>; // date -> special_policy
  peak_hour_adjustments?: Map<number, any>; // hour -> policy
  seasonal_swaps?: Map<string, any>; // season -> policy
}

export interface DelegationChain {
  delegation_id: string;
  source_agent: string;
  target_agent: string;
  capability_id: string;
  timestamp: string;
  depth: number; // how many hops from original?
  max_depth: number; // can't exceed this
  trust_multiplier: number; // trust degrades per hop
  evidence_chain: string[]; // pgl_hashes of each hop
  is_valid: boolean;
  is_revoked: boolean;
  can_further_delegate: boolean;
}

export interface EffectivePermissions {
  agent_id: string;
  capability_id: string;
  calculated_at: string;
  can_execute: boolean;
  requires_approval: boolean;
  approval_path?: string[];
  rate_limit?: number;
  trust_required: number;
  trust_current: number;
  time_restricted: boolean;
  time_windows?: [string, string][];
  cost_limit?: number;
  delegation_depth: number; // if delegated, how many hops?
  confidence_score: number; // 0-100, how sure is this calculation?
  expires_at?: string;
  evidence_hash: string;
}

export interface PolicyValidator {
  is_valid: boolean;
  conflicts: PolicyConflict[];
  warnings: string[];
  errors: string[];
  suggestions: string[];
}

// ============================================================================
// POLICY COMPOSITION ENGINE
// ============================================================================

export class PolicyCompositionEngine {
  private compositions: Map<string, PolicyComposition> = new Map();
  private conflicts: Map<string, PolicyConflict[]> = new Map();

  /**
   * Compose policies from multiple sources
   */
  composePolicy(
    agent_id: string,
    capability_id: string,
    systemPolicy?: any,
    ownerPolicy?: any,
    runtimePolicy?: any,
    temporalPolicies?: any[]
  ): PolicyComposition {
    const composition: PolicyComposition = {
      composition_id: crypto.randomUUID(),
      agent_id,
      capability_id,
      timestamp: new Date().toISOString(),
      system_policy: systemPolicy,
      owner_policy: ownerPolicy,
      runtime_policy: runtimePolicy,
      temporal_policies: temporalPolicies,
      effective_policy: {},
      conflicts_detected: [],
      resolution_method: "system-wins",
      is_valid: true,
      affected_permissions: [],
      evidence_hash: "",
    };

    // Detect conflicts
    const conflicts = this.detectConflicts(
      systemPolicy,
      ownerPolicy,
      runtimePolicy
    );
    composition.conflicts_detected = conflicts;

    // Resolve conflicts
    if (conflicts.length > 0) {
      composition.is_valid = conflicts.some(
        (c) => c.severity === "critical"
      )
        ? false
        : true;
    }

    // Merge policies (system > owner > runtime)
    composition.effective_policy = this.mergePolicy(
      systemPolicy,
      ownerPolicy,
      runtimePolicy
    );

    // Calculate evidence hash
    composition.evidence_hash = crypto
      .createHash("sha256")
      .update(JSON.stringify(composition.effective_policy))
      .digest("base64");

    this.compositions.set(composition.composition_id, composition);
    return composition;
  }

  /**
   * Detect conflicts between policies
   */
  private detectConflicts(
    systemPolicy?: any,
    ownerPolicy?: any,
    runtimePolicy?: any
  ): PolicyConflict[] {
    const conflicts: PolicyConflict[] = [];

    // Check system vs owner
    if (systemPolicy && ownerPolicy) {
      if (systemPolicy.rules && ownerPolicy.rules) {
        const sysAllow = systemPolicy.rules.some(
          (r: any) => r.effect === "allow"
        );
        const ownerAllow = ownerPolicy.rules.some(
          (r: any) => r.effect === "allow"
        );

        if (sysAllow && !ownerAllow) {
          conflicts.push({
            conflict_id: crypto.randomUUID(),
            conflict_type: "allow-deny",
            source1: systemPolicy.policy_id,
            source2: ownerPolicy.policy_id,
            conflicting_field: "effect",
            value1: "allow",
            value2: "deny",
            severity: "high",
            resolution: "System policy takes precedence",
            requires_admin_review: true,
            evidence_hash: crypto
              .createHash("sha256")
              .update(JSON.stringify({ systemPolicy, ownerPolicy }))
              .digest("base64"),
          });
        }
      }

      // Check rate limits
      if (systemPolicy.metadata?.rate_limit && ownerPolicy.metadata?.rate_limit) {
        if (
          systemPolicy.metadata.rate_limit <
          ownerPolicy.metadata.rate_limit
        ) {
          conflicts.push({
            conflict_id: crypto.randomUUID(),
            conflict_type: "rate-limit-mismatch",
            source1: systemPolicy.policy_id,
            source2: ownerPolicy.policy_id,
            conflicting_field: "rate_limit",
            value1: systemPolicy.metadata.rate_limit,
            value2: ownerPolicy.metadata.rate_limit,
            severity: "medium",
            resolution: "Use most restrictive (system)",
            requires_admin_review: false,
            evidence_hash: crypto
              .createHash("sha256")
              .update(JSON.stringify({ systemPolicy, ownerPolicy }))
              .digest("base64"),
          });
        }
      }
    }

    return conflicts;
  }

  /**
   * Merge policies (system > owner > runtime)
   */
  private mergePolicy(
    systemPolicy?: any,
    ownerPolicy?: any,
    runtimePolicy?: any
  ): any {
    const merged: any = {};

    // Start with runtime (base)
    if (runtimePolicy) {
      Object.assign(merged, runtimePolicy);
    }

    // Override with owner
    if (ownerPolicy) {
      merged.rules = [
        ...(merged.rules || []),
        ...(ownerPolicy.rules || []),
      ];
      merged.metadata = {
        ...merged.metadata,
        ...(ownerPolicy.metadata || {}),
      };
    }

    // Override with system (most restrictive)
    if (systemPolicy) {
      merged.rules = [
        ...(merged.rules || []),
        ...(systemPolicy.rules || []),
      ];
      merged.metadata = {
        ...merged.metadata,
        ...(systemPolicy.metadata || {}),
      };
      merged.immutable = true; // system policies are immutable
    }

    return merged;
  }

  /**
   * Get composition for agent/capability
   */
  getComposition(
    agent_id: string,
    capability_id: string
  ): PolicyComposition | null {
    const compositions = Array.from(this.compositions.values()).filter(
      (c) => c.agent_id === agent_id && c.capability_id === capability_id
    );

    // Return most recent
    return compositions.length > 0
      ? compositions.sort((a, b) =>
          new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
        )[0]
      : null;
  }

  /**
   * Get all conflicts
   */
  getConflicts(): PolicyConflict[] {
    return Array.from(this.conflicts.values()).flat();
  }

  /**
   * Get conflicts requiring review
   */
  getConflictsRequiringReview(): PolicyConflict[] {
    return this.getConflicts().filter((c) => c.requires_admin_review);
  }
}

// ============================================================================
// TEMPORAL POLICY LAYER
// ============================================================================

export class TemporalPolicyEngine {
  private temporalPolicies: Map<string, TemporalPolicyLayer> = new Map();

  /**
   * Register temporal policy with time windows
   */
  registerTemporalPolicy(
    policy_id: string,
    timeWindows: Array<{
      window_name: string;
      start: string;
      end: string;
      policy: any;
      rate_limit?: number;
      trust_required?: number;
      requires_approval?: boolean;
    }>
  ): TemporalPolicyLayer {
    const temporal: TemporalPolicyLayer = {
      policy_id,
      time_windows: timeWindows,
      holiday_adjustments: new Map(),
      peak_hour_adjustments: new Map(),
      seasonal_swaps: new Map(),
    };

    this.temporalPolicies.set(policy_id, temporal);
    return temporal;
  }

  /**
   * Add holiday adjustment
   */
  addHolidayAdjustment(
    policy_id: string,
    date: string, // YYYY-MM-DD
    specialPolicy: any
  ): void {
    const temporal = this.temporalPolicies.get(policy_id);
    if (temporal) {
      temporal.holiday_adjustments!.set(date, specialPolicy);
    }
  }

  /**
   * Add peak hour adjustment
   */
  addPeakHourAdjustment(policy_id: string, hour: number, policy: any): void {
    const temporal = this.temporalPolicies.get(policy_id);
    if (temporal) {
      temporal.peak_hour_adjustments!.set(hour, policy);
    }
  }

  /**
   * Get effective policy for current time
   */
  getEffectivePolicyForNow(policy_id: string): any {
    const now = new Date();
    const hour = now.getHours();
    const dateStr = now.toISOString().split("T")[0];

    const temporal = this.temporalPolicies.get(policy_id);
    if (!temporal) return null;

    // Check holiday first
    const holidayPolicy = temporal.holiday_adjustments?.get(dateStr);
    if (holidayPolicy) return holidayPolicy;

    // Check peak hour
    const peakPolicy = temporal.peak_hour_adjustments?.get(hour);
    if (peakPolicy) return peakPolicy;

    // Check time windows
    for (const window of temporal.time_windows) {
      const start = new Date(window.start);
      const end = new Date(window.end);
      if (now >= start && now <= end) {
        return window.policy;
      }
    }

    // Default: most restrictive window
    return temporal.time_windows[0]?.policy || null;
  }

  /**
   * Get policy for specific time
   */
  getPolicyForTime(policy_id: string, time: Date): any {
    const temporal = this.temporalPolicies.get(policy_id);
    if (!temporal) return null;

    const hour = time.getHours();
    const dateStr = time.toISOString().split("T")[0];

    // Check holiday
    const holidayPolicy = temporal.holiday_adjustments?.get(dateStr);
    if (holidayPolicy) return holidayPolicy;

    // Check peak hour
    const peakPolicy = temporal.peak_hour_adjustments?.get(hour);
    if (peakPolicy) return peakPolicy;

    // Check time windows
    for (const window of temporal.time_windows) {
      const start = new Date(window.start);
      const end = new Date(window.end);
      if (time >= start && time <= end) {
        return window.policy;
      }
    }

    return null;
  }
}

// ============================================================================
// DELEGATION CHAIN VALIDATOR
// ============================================================================

export class DelegationChainValidator {
  public delegations: Map<string, DelegationChain> = new Map();
  private readonly MAX_DELEGATION_DEPTH = 3;

  /**
   * Create delegation
   */
  createDelegation(
    source_agent: string,
    target_agent: string,
    capability_id: string,
    max_depth: number = this.MAX_DELEGATION_DEPTH,
    trust_multiplier: number = 0.8
  ): DelegationChain {
    const delegation: DelegationChain = {
      delegation_id: crypto.randomUUID(),
      source_agent,
      target_agent,
      capability_id,
      timestamp: new Date().toISOString(),
      depth: 1,
      max_depth,
      trust_multiplier,
      evidence_chain: [],
      is_valid: true,
      is_revoked: false,
      can_further_delegate: max_depth > 1,
    };

    this.delegations.set(delegation.delegation_id, delegation);
    return delegation;
  }

  /**
   * Further delegate capability
   */
  furtherDelegate(
    delegation_id: string,
    next_target: string,
    evidence_hash: string
  ): DelegationChain | null {
    const original = this.delegations.get(delegation_id);
    if (!original || !original.can_further_delegate) {
      return null;
    }

    const newDepth = original.depth + 1;
    if (newDepth > original.max_depth) {
      return null;
    }

    const newDelegation: DelegationChain = {
      delegation_id: crypto.randomUUID(),
      source_agent: original.target_agent,
      target_agent: next_target,
      capability_id: original.capability_id,
      timestamp: new Date().toISOString(),
      depth: newDepth,
      max_depth: original.max_depth,
      trust_multiplier: original.trust_multiplier,
      evidence_chain: [...original.evidence_chain, evidence_hash],
      is_valid: true,
      is_revoked: false,
      can_further_delegate: newDepth < original.max_depth,
    };

    this.delegations.set(newDelegation.delegation_id, newDelegation);
    return newDelegation;
  }

  /**
   * Revoke delegation (cascades to downstream)
   */
  revokeDelegation(delegation_id: string): DelegationChain[] {
    const delegation = this.delegations.get(delegation_id);
    if (!delegation) return [];

    const revoked: DelegationChain[] = [delegation];
    delegation.is_revoked = true;

    // Find and revoke downstream delegations
    this.delegations.forEach((d) => {
      if (
        d.source_agent === delegation.target_agent &&
        d.capability_id === delegation.capability_id
      ) {
        this.revokeDelegation(d.delegation_id);
        revoked.push(d);
      }
    });

    return revoked;
  }

  /**
   * Calculate effective trust with delegation
   */
  calculateEffectiveTrust(
    delegation_id: string,
    baseTrust: number
  ): number {
    const delegation = this.delegations.get(delegation_id);
    if (!delegation || delegation.is_revoked) return 0;

    // Trust degrades per hop
    return baseTrust * Math.pow(delegation.trust_multiplier, delegation.depth);
  }

  /**
   * Validate delegation chain
   */
  validateChain(delegation_id: string): {
    valid: boolean;
    errors: string[];
    warnings: string[];
  } {
    const delegation = this.delegations.get(delegation_id);
    if (!delegation) {
      return {
        valid: false,
        errors: ["Delegation not found"],
        warnings: [],
      };
    }

    const errors: string[] = [];
    const warnings: string[] = [];

    if (delegation.is_revoked) {
      errors.push("Delegation has been revoked");
    }

    if (delegation.depth > delegation.max_depth) {
      errors.push(`Delegation depth ${delegation.depth} exceeds max ${delegation.max_depth}`);
    }

    if (delegation.evidence_chain.length !== delegation.depth - 1) {
      warnings.push(
        "Evidence chain length does not match delegation depth"
      );
    }

    return {
      valid: errors.length === 0,
      errors,
      warnings,
    };
  }

  /**
   * Get delegation for agent/capability
   */
  getDelegation(
    agent_id: string,
    capability_id: string
  ): DelegationChain | null {
    const delegations = Array.from(this.delegations.values()).filter(
      (d) =>
        d.target_agent === agent_id &&
        d.capability_id === capability_id &&
        !d.is_revoked
    );

    return delegations.length > 0
      ? delegations.sort((a, b) =>
          new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
        )[0]
      : null;
  }
}

// ============================================================================
// EFFECTIVE PERMISSIONS CALCULATOR
// ============================================================================

export class EffectivePermissionsCalculator {
  private compositionEngine: PolicyCompositionEngine;
  private temporalEngine: TemporalPolicyEngine;
  private delegationValidator: DelegationChainValidator;

  constructor(
    compositionEngine: PolicyCompositionEngine,
    temporalEngine: TemporalPolicyEngine,
    delegationValidator: DelegationChainValidator
  ) {
    this.compositionEngine = compositionEngine;
    this.temporalEngine = temporalEngine;
    this.delegationValidator = delegationValidator;
  }

  /**
   * Calculate effective permissions
   */
  calculateEffectivePermissions(
    agent_id: string,
    capability_id: string,
    currentTrust: number,
    systemPolicy?: any,
    ownerPolicy?: any,
    runtimePolicy?: any
  ): EffectivePermissions {
    // Compose policies
    const composition = this.compositionEngine.composePolicy(
      agent_id,
      capability_id,
      systemPolicy,
      ownerPolicy,
      runtimePolicy
    );

    // Get temporal policy
    const temporalPolicy = this.temporalEngine.getEffectivePolicyForNow(
      capability_id
    );

    // Merge temporal with composed
    const effectivePolicy = { ...composition.effective_policy, ...temporalPolicy };

    // Check if valid
    const canExecute = composition.is_valid && composition.conflicts_detected.length === 0;

    // Extract rate limit and trust requirement
    const rateLimit = effectivePolicy.metadata?.rate_limit || 100;
    const trustRequired = effectivePolicy.metadata?.trust_minimum || 50;

    const permissions: EffectivePermissions = {
      agent_id,
      capability_id,
      calculated_at: new Date().toISOString(),
      can_execute: canExecute,
      requires_approval: effectivePolicy.metadata?.requires_approval || false,
      approval_path: effectivePolicy.metadata?.approval_path,
      rate_limit: rateLimit,
      trust_required: trustRequired,
      trust_current: currentTrust,
      time_restricted: temporalPolicy !== null,
      delegation_depth: 0,
      confidence_score: composition.is_valid ? 95 : 50,
      evidence_hash: composition.evidence_hash,
    };

    return permissions;
  }

  /**
   * Calculate permissions with delegation
   */
  calculateWithDelegation(
    agent_id: string,
    capability_id: string,
    delegationId: string,
    currentTrust: number
  ): EffectivePermissions | null {
    const delegation = this.delegationValidator.delegations.get(delegationId);
    if (!delegation) return null;

    const basePermissions = this.calculateEffectivePermissions(
      agent_id,
      capability_id,
      currentTrust
    );

    // Adjust for delegation depth
    basePermissions.delegation_depth = delegation.depth;
    basePermissions.trust_current = this.delegationValidator.calculateEffectiveTrust(
      delegationId,
      currentTrust
    );

    // Can't exceed original permissions
    if (basePermissions.trust_current < basePermissions.trust_required) {
      basePermissions.can_execute = false;
    }

    return basePermissions;
  }
}

// ============================================================================
// EXAMPLE USAGE
// ============================================================================

function demonstrateGovernanceLayer() {
  const compositionEngine = new PolicyCompositionEngine();
  const temporalEngine = new TemporalPolicyEngine();
  const delegationValidator = new DelegationChainValidator();
  const permissionsCalc = new EffectivePermissionsCalculator(
    compositionEngine,
    temporalEngine,
    delegationValidator
  );

  // Scenario 1: Policy composition with conflicts
  console.log("=== Scenario 1: Policy Composition ===");

  const systemPolicy = {
    policy_id: "sys-policy-001",
    rules: [
      { effect: "allow", action: "search", trust_minimum: 30 },
    ],
    metadata: { rate_limit: 100, immutable: true },
  };

  const ownerPolicy = {
    policy_id: "owner-policy-001",
    rules: [
      { effect: "allow", action: "search", trust_minimum: 50 },
    ],
    metadata: { rate_limit: 50 },
  };

  const composition = compositionEngine.composePolicy(
    "agent-001",
    "search",
    systemPolicy,
    ownerPolicy
  );

  console.log(`Composition ID: ${composition.composition_id}`);
  console.log(`Conflicts: ${composition.conflicts_detected.length}`);
  console.log(`Is valid: ${composition.is_valid}`);

  // Scenario 2: Temporal policies
  console.log("\n=== Scenario 2: Temporal Policies ===");

  const businessHoursPolicy = {
    effect: "allow",
    rate_limit: 100,
    trust_minimum: 50,
  };

  const afterHoursPolicy = {
    effect: "allow",
    rate_limit: 10,
    trust_minimum: 75,
    requires_approval: true,
  };

  temporalEngine.registerTemporalPolicy("temporal-001", [
    {
      window_name: "Business hours",
      start: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
      end: new Date(Date.now() + 4 * 60 * 60 * 1000).toISOString(),
      policy: businessHoursPolicy,
    },
    {
      window_name: "After hours",
      start: new Date(Date.now() + 4 * 60 * 60 * 1000).toISOString(),
      end: new Date(Date.now() + 12 * 60 * 60 * 1000).toISOString(),
      policy: afterHoursPolicy,
    },
  ]);

  const effectiveNow = temporalEngine.getEffectivePolicyForNow("temporal-001");
  console.log(
    `Effective policy for now: rate_limit=${effectiveNow.rate_limit}, trust=${effectiveNow.trust_minimum}`
  );

  // Scenario 3: Delegation chains
  console.log("\n=== Scenario 3: Delegation Chains ===");

  const delegation1 = delegationValidator.createDelegation(
    "agent-000", // Commander
    "agent-001",
    "search",
    2,
    0.9
  );

  const delegation2 = delegationValidator.furtherDelegate(
    delegation1.delegation_id,
    "agent-002",
    "pgl-hash-001"
  );

  console.log(`Delegation 1 depth: ${delegation1.depth}`);
  console.log(`Delegation 2 depth: ${delegation2?.depth}`);

  // Try to delegate beyond max
  const delegation3 = delegationValidator.furtherDelegate(
    delegation2!.delegation_id,
    "agent-003",
    "pgl-hash-002"
  );
  console.log(`Delegation 3 (should fail): ${delegation3 === null ? "Blocked" : "Created"}`);

  // Scenario 4: Effective permissions
  console.log("\n=== Scenario 4: Effective Permissions ===");

  const perms = permissionsCalc.calculateEffectivePermissions(
    "agent-001",
    "search",
    65, // current trust
    systemPolicy,
    ownerPolicy
  );

  console.log(`Can execute: ${perms.can_execute}`);
  console.log(`Trust required: ${perms.trust_required}`);
  console.log(`Trust current: ${perms.trust_current}`);
  console.log(`Rate limit: ${perms.rate_limit}`);
}

// Uncomment to run:
// demonstrateGovernanceLayer();
