/**
 * MCPAPI Intelligence Layer
 * Version: 2.0.0
 *
 * Machine learning & analytics:
 * - Cost attribution & budgeting
 * - Behavioral pattern learning
 * - Risk scoring & anomaly correlation
 * - Predictive threat detection
 */

import * as crypto from "crypto";

// ============================================================================
// INTELLIGENCE LAYER TYPES
// ============================================================================

export interface CostModel {
  capability_id: string;
  cost_per_call: number;
  currency: "credits" | "carbon" | "usd" | "mixed";
  budget_per_agent: number;
  budget_per_day: number;
  budget_per_month: number;
  overage_policy: "deny" | "escalate" | "auto-approve-charge";
  cost_allocation: Map<
    string,
    {
      agent_id: string;
      used: number;
      budget: number;
      remaining: number;
      last_reset: string;
    }
  >;
}

export interface CostAllocationRecord {
  record_id: string;
  agent_id: string;
  capability_id: string;
  timestamp: string;
  cost: number;
  currency: string;
  budget_before: number;
  budget_after: number;
  budget_exceeded: boolean;
  action_taken: "allowed" | "escalated" | "denied" | "auto_charged";
  evidence_hash: string;
}

export interface AgentCostAnalysis {
  agent_id: string;
  period: "daily" | "weekly" | "monthly";
  total_cost: number;
  cost_by_capability: Map<string, number>;
  cost_trend: number; // percentage change from previous period
  anomaly_detected: boolean;
  anomaly_score: number; // 0-100
  highest_cost_capability: string;
  highest_cost_amount: number;
  forecast_next_period: number;
}

export interface BehavioralPattern {
  pattern_id: string;
  agent_id: string;
  pattern_type:
    | "capability_preference"
    | "time_preference"
    | "failure_pattern"
    | "collaboration_pattern";
  pattern_description: string;
  confidence: number; // 0-100
  first_observed: string;
  last_observed: string;
  observation_count: number;
  supports_normal_operation: boolean; // or suggests anomaly?
}

export interface RiskProfile {
  agent_id: string;
  overall_risk_score: number; // 0-100
  risk_factors: Map<
    string,
    {
      factor_name: string;
      contribution: number; // percentage
      severity: "low" | "medium" | "high" | "critical";
      mitigations: string[];
    }
  >;
  threat_level: "green" | "yellow" | "orange" | "red";
  last_assessed: string;
  next_assessment_due: string;
  recommended_actions: string[];
}

export interface CostAnomalyEvent {
  anomaly_id: string;
  agent_id: string;
  detected_at: string;
  anomaly_type:
    | "sudden_spike"
    | "sustained_high_usage"
    | "budget_exceeded"
    | "unusual_capability_mix"
    | "off_pattern_usage";
  baseline_cost: number;
  current_cost: number;
  deviation_percentage: number;
  severity: "low" | "medium" | "high" | "critical";
  recommended_action: "monitor" | "alert" | "escalate" | "deny";
  evidence_hash: string;
}

export interface CorrelationAnalysis {
  analysis_id: string;
  timestamp: string;
  events: string[]; // anomaly_ids
  correlation_score: number; // 0-100, how related?
  pattern: string; // description of correlated pattern
  common_agent?: string;
  common_capability?: string;
  common_time_window?: [number, number];
  suspected_cause: string;
  evidence_hash: string;
}

// ============================================================================
// COST ATTRIBUTION SERVICE
// ============================================================================

export class CostAttributionService {
  public costModels: Map<string, CostModel> = new Map();
  private allocationRecords: CostAllocationRecord[] = [];
  private agentBudgets: Map<string, Map<string, number>> = new Map(); // agent_id -> {daily_budget, monthly_budget}

  /**
   * Register cost model for capability
   */
  registerCostModel(
    capability_id: string,
    cost_per_call: number,
    currency: "credits" | "carbon" | "usd" | "mixed",
    budgetPerAgent: number,
    budgetPerDay: number,
    budgetPerMonth: number,
    overagePolicy: "deny" | "escalate" | "auto-approve-charge"
  ): CostModel {
    const model: CostModel = {
      capability_id,
      cost_per_call,
      currency,
      budget_per_agent: budgetPerAgent,
      budget_per_day: budgetPerDay,
      budget_per_month: budgetPerMonth,
      overage_policy: overagePolicy,
      cost_allocation: new Map(),
    };

    this.costModels.set(capability_id, model);
    return model;
  }

  /**
   * Allocate budget to agent for capability
   */
  allocateBudget(
    agent_id: string,
    capability_id: string,
    monthly_budget: number
  ): void {
    const model = this.costModels.get(capability_id);
    if (!model) return;

    model.cost_allocation.set(agent_id, {
      agent_id,
      used: 0,
      budget: monthly_budget,
      remaining: monthly_budget,
      last_reset: new Date().toISOString(),
    });
  }

  /**
   * Record cost for request
   */
  recordCost(
    agent_id: string,
    capability_id: string,
    cost: number,
    currency: string,
    allowed: boolean
  ): CostAllocationRecord {
    const model = this.costModels.get(capability_id);
    if (!model) {
      throw new Error(`Cost model not found for ${capability_id}`);
    }

    const allocation = model.cost_allocation.get(agent_id) || {
      agent_id,
      used: 0,
      budget: model.budget_per_agent,
      remaining: model.budget_per_agent,
      last_reset: new Date().toISOString(),
    };

    const budgetBefore = allocation.remaining;
    const budgetAfter = allocation.remaining - cost;
    const budgetExceeded = budgetAfter < 0;

    let action: "allowed" | "escalated" | "denied" | "auto_charged" =
      "allowed";

    if (budgetExceeded) {
      if (model.overage_policy === "deny") {
        action = "denied";
      } else if (model.overage_policy === "escalate") {
        action = "escalated";
      } else if (model.overage_policy === "auto-approve-charge") {
        action = "auto_charged";
      }
    }

    if (action !== "denied") {
      allocation.used += cost;
      allocation.remaining = allocation.budget - allocation.used;
      model.cost_allocation.set(agent_id, allocation);
    }

    const record: CostAllocationRecord = {
      record_id: crypto.randomUUID(),
      agent_id,
      capability_id,
      timestamp: new Date().toISOString(),
      cost,
      currency,
      budget_before: budgetBefore,
      budget_after: budgetAfter,
      budget_exceeded: budgetExceeded,
      action_taken: action,
      evidence_hash: crypto
        .createHash("sha256")
        .update(
          JSON.stringify({
            agent_id,
            capability_id,
            cost,
            timestamp: new Date().toISOString(),
          })
        )
        .digest("base64"),
    };

    this.allocationRecords.push(record);
    return record;
  }

  /**
   * Get agent's remaining budget for capability
   */
  getRemainingBudget(agent_id: string, capability_id: string): number {
    const model = this.costModels.get(capability_id);
    if (!model) return 0;

    const allocation = model.cost_allocation.get(agent_id);
    return allocation?.remaining || 0;
  }

  /**
   * Check if agent can afford request
   */
  canAffordRequest(agent_id: string, capability_id: string): boolean {
    const model = this.costModels.get(capability_id);
    if (!model) return true; // Unknown capability, allow

    const cost = model.cost_per_call;
    const remaining = this.getRemainingBudget(agent_id, capability_id);

    return remaining >= cost;
  }

  /**
   * Get cost analysis for agent
   */
  getCostAnalysis(
    agent_id: string,
    period: "daily" | "weekly" | "monthly"
  ): AgentCostAnalysis {
    // Filter records for time period
    const now = Date.now();
    const periodMs =
      period === "daily"
        ? 24 * 60 * 60 * 1000
        : period === "weekly"
          ? 7 * 24 * 60 * 60 * 1000
          : 30 * 24 * 60 * 60 * 1000;

    const cutoff = now - periodMs;
    const relevantRecords = this.allocationRecords.filter(
      (r) =>
        r.agent_id === agent_id &&
        new Date(r.timestamp).getTime() > cutoff
    );

    // Calculate totals
    const totalCost = relevantRecords.reduce((sum, r) => sum + r.cost, 0);
    const costByCapability = new Map<string, number>();

    relevantRecords.forEach((r) => {
      costByCapability.set(
        r.capability_id,
        (costByCapability.get(r.capability_id) || 0) + r.cost
      );
    });

    // Find highest cost
    let highestCapability = "";
    let highestCost = 0;

    costByCapability.forEach((cost, cap) => {
      if (cost > highestCost) {
        highestCost = cost;
        highestCapability = cap;
      }
    });

    // Calculate previous period cost for trend calculation
    const prevCutoff = cutoff - periodMs;
    const prevRecords = this.allocationRecords.filter(
      (r) =>
        r.agent_id === agent_id &&
        new Date(r.timestamp).getTime() > prevCutoff &&
        new Date(r.timestamp).getTime() <= cutoff
    );
    const prevTotalCost = prevRecords.reduce((sum, r) => sum + r.cost, 0);

    let cost_trend = 0;
    if (prevTotalCost > 0) {
      cost_trend = ((totalCost - prevTotalCost) / prevTotalCost) * 100;
    } else if (totalCost > 0) {
      cost_trend = 100;
    }

    // Determine dynamic budget threshold based on all registered capabilities
    let budgetThreshold = 0;
    this.costModels.forEach((model) => {
      const allocation = model.cost_allocation.get(agent_id);
      if (allocation) {
        budgetThreshold += allocation.budget;
      } else {
        budgetThreshold += model.budget_per_agent;
      }
    });

    if (budgetThreshold === 0) {
      budgetThreshold = 1000;
    }

    // Adjust threshold based on period (monthly budget to daily/weekly)
    let adjustedThreshold = budgetThreshold;
    if (period === "daily") {
      adjustedThreshold = budgetThreshold / 30;
    } else if (period === "weekly") {
      adjustedThreshold = (budgetThreshold / 30) * 7;
    }
    adjustedThreshold = Math.max(10, adjustedThreshold);

    const anomaly_detected = totalCost > adjustedThreshold;
    const anomaly_score = Math.min(100, (totalCost / adjustedThreshold) * 100);
    const trendFactor = 1 + (cost_trend / 100);
    const forecast_next_period = Math.max(0, totalCost * trendFactor);

    return {
      agent_id,
      period,
      total_cost: totalCost,
      cost_by_capability: costByCapability,
      cost_trend,
      anomaly_detected,
      anomaly_score,
      highest_cost_capability: highestCapability,
      highest_cost_amount: highestCost,
      forecast_next_period,
    };
  }

  /**
   * Reset budgets (daily/monthly)
   */
  resetBudgets(period: "daily" | "monthly"): void {
    this.costModels.forEach((model) => {
      model.cost_allocation.forEach((allocation) => {
        const resetBudget =
          period === "daily"
            ? model.budget_per_day
            : model.budget_per_month;
        allocation.remaining = resetBudget;
        allocation.last_reset = new Date().toISOString();
      });
    });
  }
}

// ============================================================================
// BEHAVIORAL LEARNING SERVICE
// ============================================================================

export class BehavioralLearningService {
  private patterns: Map<string, BehavioralPattern[]> = new Map();
  private observations: Map<string, any[]> = new Map();

  /**
   * Record behavior observation
   */
  recordBehavior(
    agent_id: string,
    observation: {
      capability_used: string;
      time_of_day: number;
      success: boolean;
      error_type?: string;
      collaboration_with?: string;
    }
  ): void {
    if (!this.observations.has(agent_id)) {
      this.observations.set(agent_id, []);
    }

    this.observations.get(agent_id)!.push({
      ...observation,
      timestamp: new Date().toISOString(),
    });
  }

  /**
   * Learn patterns from observations
   */
  learnPatterns(agent_id: string): BehavioralPattern[] {
    const obs = this.observations.get(agent_id) || [];
    if (obs.length < 10) return []; // Need enough data

    const learnedPatterns: BehavioralPattern[] = [];

    // Pattern 1: Capability preference
    const capabilityFreq = new Map<string, number>();
    obs.forEach((o) => {
      capabilityFreq.set(
        o.capability_used,
        (capabilityFreq.get(o.capability_used) || 0) + 1
      );
    });

    capabilityFreq.forEach((count, cap) => {
      const freq = count / obs.length;
      if (freq > 0.2) {
        learnedPatterns.push({
          pattern_id: crypto.randomUUID(),
          agent_id,
          pattern_type: "capability_preference",
          pattern_description: `Prefers capability: ${cap} (${Math.round(freq * 100)}% of requests)`,
          confidence: Math.min(100, freq * 100),
          first_observed: obs[0].timestamp,
          last_observed: obs[obs.length - 1].timestamp,
          observation_count: count,
          supports_normal_operation: true,
        });
      }
    });

    // Pattern 2: Time preference
    const timeFreq = new Map<number, number>();
    obs.forEach((o) => {
      timeFreq.set(o.time_of_day, (timeFreq.get(o.time_of_day) || 0) + 1);
    });

    const preferredHours = Array.from(timeFreq.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3)
      .map((e) => e[0]);

    if (preferredHours.length > 0) {
      learnedPatterns.push({
        pattern_id: crypto.randomUUID(),
        agent_id,
        pattern_type: "time_preference",
        pattern_description: `Active during hours: ${preferredHours.join(", ")}`,
        confidence: 75,
        first_observed: obs[0].timestamp,
        last_observed: obs[obs.length - 1].timestamp,
        observation_count: obs.length,
        supports_normal_operation: true,
      });
    }

    // Pattern 3: Failure pattern
    const failures = obs.filter((o) => !o.success);
    if (failures.length > obs.length * 0.05) {
      const errorTypes = new Map<string, number>();
      failures.forEach((f) => {
        errorTypes.set(f.error_type, (errorTypes.get(f.error_type) || 0) + 1);
      });

      const topError = Array.from(errorTypes.entries()).sort(
        (a, b) => b[1] - a[1]
      )[0];

      learnedPatterns.push({
        pattern_id: crypto.randomUUID(),
        agent_id,
        pattern_type: "failure_pattern",
        pattern_description: `Recurring failure: ${topError[0]} (${topError[1]} times)`,
        confidence: (failures.length / obs.length) * 100,
        first_observed: obs[0].timestamp,
        last_observed: obs[obs.length - 1].timestamp,
        observation_count: failures.length,
        supports_normal_operation: false,
      });
    }

    this.patterns.set(agent_id, learnedPatterns);
    return learnedPatterns;
  }

  /**
   * Get learned patterns for agent
   */
  getPatterns(agent_id: string): BehavioralPattern[] {
    return this.patterns.get(agent_id) || [];
  }

  /**
   * Check if current behavior matches learned patterns
   */
  matchesPattern(
    agent_id: string,
    current_behavior: {
      capability_used: string;
      time_of_day: number;
    }
  ): boolean {
    const patterns = this.getPatterns(agent_id);
    const capPatterns = patterns.filter((p) =>
      p.pattern_description.includes(current_behavior.capability_used)
    );
    const timePatterns = patterns.filter((p) =>
      p.pattern_description.includes(current_behavior.time_of_day.toString())
    );

    return capPatterns.length > 0 || timePatterns.length > 0;
  }
}

// ============================================================================
// RISK SCORING SERVICE
// ============================================================================

export class RiskScoringService {
  private riskProfiles: Map<string, RiskProfile> = new Map();

  /**
   * Calculate overall risk score
   */
  calculateRiskScore(
    agent_id: string,
    factors: {
      trust_score: number;
      anomaly_score: number;
      cost_anomaly_score: number;
      behavioral_deviation: number;
      failed_requests_percentage: number;
      deactivation_count: number;
      escalation_count: number;
      policy_violations: number;
    }
  ): RiskProfile {
    const riskFactors = new Map<
      string,
      {
        factor_name: string;
        contribution: number;
        severity: "low" | "medium" | "high" | "critical";
        mitigations: string[];
      }
    >();

    // Factor 1: Low trust
    if (factors.trust_score < 50) {
      riskFactors.set("low_trust", {
        factor_name: "Low trust score",
        contribution: 20,
        severity: factors.trust_score < 30 ? "critical" : "high",
        mitigations: ["Require approval", "Increase monitoring"],
      });
    }

    // Factor 2: Anomalies
    if (factors.anomaly_score > 60) {
      riskFactors.set("anomalies", {
        factor_name: "Behavioral anomalies",
        contribution: 25,
        severity: factors.anomaly_score > 80 ? "critical" : "high",
        mitigations: ["Quarantine requests", "Escalate to security"],
      });
    }

    // Factor 3: Cost anomalies
    if (factors.cost_anomaly_score > 50) {
      riskFactors.set("cost_anomaly", {
        factor_name: "Unusual cost pattern",
        contribution: 15,
        severity: factors.cost_anomaly_score > 75 ? "high" : "medium",
        mitigations: ["Cap daily budget", "Require approval for high-cost requests"],
      });
    }

    // Factor 4: Behavioral deviation
    if (factors.behavioral_deviation > 2) {
      riskFactors.set("behavior_deviation", {
        factor_name: "Significant behavioral change",
        contribution: 20,
        severity: "high",
        mitigations: ["Alert admins", "Increase audit logging"],
      });
    }

    // Factor 5: Failed requests
    if (factors.failed_requests_percentage > 10) {
      riskFactors.set("failures", {
        factor_name: "High failure rate",
        contribution: 10,
        severity: "medium",
        mitigations: ["Debug capability integration"],
      });
    }

    // Factor 6: Policy violations
    if (factors.policy_violations > 3) {
      riskFactors.set("violations", {
        factor_name: "Multiple policy violations",
        contribution: 20,
        severity: "critical",
        mitigations: ["Deactivate agent", "Review policies"],
      });
    }

    // Calculate weighted score
    let totalScore = 0;
    let totalWeight = 0;

    riskFactors.forEach((factor) => {
      totalScore += factor.contribution;
      totalWeight += factor.contribution;
    });

    const overallScore = totalWeight > 0 ? totalScore : 0;

    // Determine threat level
    let threatLevel: "green" | "yellow" | "orange" | "red" = "green";
    if (overallScore < 30) threatLevel = "green";
    else if (overallScore < 50) threatLevel = "yellow";
    else if (overallScore < 75) threatLevel = "orange";
    else threatLevel = "red";

    const profile: RiskProfile = {
      agent_id,
      overall_risk_score: Math.min(100, overallScore),
      risk_factors: riskFactors,
      threat_level: threatLevel,
      last_assessed: new Date().toISOString(),
      next_assessment_due: new Date(
        Date.now() + 24 * 60 * 60 * 1000
      ).toISOString(),
      recommended_actions: this.getRecommendedActions(threatLevel),
    };

    this.riskProfiles.set(agent_id, profile);
    return profile;
  }

  private getRecommendedActions(threatLevel: string): string[] {
    switch (threatLevel) {
      case "green":
        return ["Continue normal monitoring"];
      case "yellow":
        return ["Increase audit logging", "Monitor for further anomalies"];
      case "orange":
        return [
          "Enable request quarantine",
          "Require approval for sensitive actions",
          "Alert security team",
        ];
      case "red":
        return [
          "Deactivate agent immediately",
          "Lock all permissions",
          "Initiate security investigation",
          "Notify leadership",
        ];
      default:
        return [];
    }
  }

  /**
   * Get risk profile for agent
   */
  getRiskProfile(agent_id: string): RiskProfile | null {
    return this.riskProfiles.get(agent_id) || null;
  }

  /**
   * Check if agent needs intervention
   */
  needsIntervention(agent_id: string): boolean {
    const profile = this.riskProfiles.get(agent_id);
    if (!profile) return false;
    return profile.threat_level === "orange" || profile.threat_level === "red";
  }
}

// ============================================================================
// CORRELATION ANALYSIS SERVICE
// ============================================================================

export class CorrelationAnalysisService {
  private costAnomalies: CostAnomalyEvent[] = [];
  private correlations: CorrelationAnalysis[] = [];

  /**
   * Detect cost anomalies
   */
  detectCostAnomaly(
    agent_id: string,
    baseline_cost: number,
    current_cost: number
  ): CostAnomalyEvent | null {
    const deviation = ((current_cost - baseline_cost) / baseline_cost) * 100;

    if (deviation < 50) return null; // Not significant

    let anomaly_type: CostAnomalyEvent["anomaly_type"];
    let severity: CostAnomalyEvent["severity"];

    if (deviation > 200) {
      anomaly_type = "sudden_spike";
      severity = "critical";
    } else if (deviation > 100) {
      anomaly_type = "sustained_high_usage";
      severity = "high";
    } else {
      anomaly_type = "unusual_capability_mix";
      severity = "medium";
    }

    const anomaly: CostAnomalyEvent = {
      anomaly_id: crypto.randomUUID(),
      agent_id,
      detected_at: new Date().toISOString(),
      anomaly_type,
      baseline_cost,
      current_cost,
      deviation_percentage: deviation,
      severity,
      recommended_action:
        severity === "critical"
          ? "deny"
          : severity === "high"
            ? "escalate"
            : "alert",
      evidence_hash: crypto
        .createHash("sha256")
        .update(
          JSON.stringify({
            agent_id,
            current_cost,
            timestamp: new Date().toISOString(),
          })
        )
        .digest("base64"),
    };

    this.costAnomalies.push(anomaly);
    return anomaly;
  }

  /**
   * Correlate multiple anomalies
   */
  correlateAnomalies(anomaly_ids: string[]): CorrelationAnalysis | null {
    if (anomaly_ids.length < 2) return null;

    // Find anomalies
    const anomalies = anomaly_ids
      .map((id) => this.costAnomalies.find((a) => a.anomaly_id === id))
      .filter((a) => a !== undefined) as CostAnomalyEvent[];

    if (anomalies.length < 2) return null;

    // Check for common patterns
    const agents = new Set(anomalies.map((a) => a.agent_id));
    const types = new Set(anomalies.map((a) => a.anomaly_type));

    let commonAgent: string | undefined;
    let pattern = "";

    if (agents.size === 1) {
      commonAgent = Array.from(agents)[0];
      pattern = `Agent ${commonAgent} showing multiple cost anomalies`;
    }

    if (types.size === 1) {
      const type = Array.from(types)[0];
      pattern += ` - All ${type}`;
    }

    const correlation: CorrelationAnalysis = {
      analysis_id: crypto.randomUUID(),
      timestamp: new Date().toISOString(),
      events: anomaly_ids,
      correlation_score: Math.min(100, anomalies.length * 30),
      pattern,
      common_agent: commonAgent,
      suspected_cause: "Investigate for coordinated attack or system issue",
      evidence_hash: crypto
        .createHash("sha256")
        .update(JSON.stringify(anomaly_ids))
        .digest("base64"),
    };

    this.correlations.push(correlation);
    return correlation;
  }

  /**
   * Get all cost anomalies
   */
  getCostAnomalies(): CostAnomalyEvent[] {
    return this.costAnomalies;
  }

  /**
   * Get correlations
   */
  getCorrelations(): CorrelationAnalysis[] {
    return this.correlations;
  }
}

// ============================================================================
// EXAMPLE USAGE
// ============================================================================

function demonstrateIntelligenceLayer() {
  const costService = new CostAttributionService();
  const behaviorService = new BehavioralLearningService();
  const riskService = new RiskScoringService();
  const correlationService = new CorrelationAnalysisService();

  // Scenario 1: Cost attribution
  console.log("=== Scenario 1: Cost Attribution ===");

  costService.registerCostModel(
    "search",
    10,
    "credits",
    1000,
    100,
    1000,
    "escalate"
  );
  costService.allocateBudget("agent-001", "search", 500);

  const record1 = costService.recordCost("agent-001", "search", 10, "credits", true);
  console.log(`Cost recorded: ${record1.cost} credits`);
  console.log(`Remaining budget: ${costService.getRemainingBudget("agent-001", "search")}`);

  // Scenario 2: Cost analysis
  console.log("\n=== Scenario 2: Cost Analysis ===");
  const analysis = costService.getCostAnalysis("agent-001", "daily");
  console.log(`Daily cost: ${analysis.total_cost}`);
  console.log(`Anomaly detected: ${analysis.anomaly_detected}`);

  // Scenario 3: Behavioral learning
  console.log("\n=== Scenario 3: Behavioral Learning ===");
  const agent_id = "agent-001";

  for (let i = 0; i < 20; i++) {
    behaviorService.recordBehavior(agent_id, {
      capability_used: i % 2 === 0 ? "search" : "database.read",
      time_of_day: 9 + (i % 8),
      success: i % 20 !== 0,
    });
  }

  const patterns = behaviorService.learnPatterns(agent_id);
  console.log(`Patterns learned: ${patterns.length}`);
  patterns.forEach((p) => {
    console.log(`  - ${p.pattern_description} (confidence: ${p.confidence}%)`);
  });

  // Scenario 4: Risk scoring
  console.log("\n=== Scenario 4: Risk Scoring ===");
  const riskProfile = riskService.calculateRiskScore(agent_id, {
    trust_score: 45,
    anomaly_score: 65,
    cost_anomaly_score: 30,
    behavioral_deviation: 1.5,
    failed_requests_percentage: 5,
    deactivation_count: 0,
    escalation_count: 2,
    policy_violations: 0,
  });

  console.log(`Overall risk score: ${riskProfile.overall_risk_score}`);
  console.log(`Threat level: ${riskProfile.threat_level}`);
  console.log(`Needs intervention: ${riskService.needsIntervention(agent_id)}`);

  // Scenario 5: Cost anomaly correlation
  console.log("\n=== Scenario 5: Cost Anomaly Correlation ===");
  const anomaly1 = correlationService.detectCostAnomaly(
    "agent-001",
    100,
    350
  );
  const anomaly2 = correlationService.detectCostAnomaly(
    "agent-001",
    200,
    700
  );

  if (anomaly1 && anomaly2) {
    const correlation = correlationService.correlateAnomalies([
      anomaly1.anomaly_id,
      anomaly2.anomaly_id,
    ]);
    console.log(`Correlation detected: ${correlation?.pattern}`);
  }
}

// Uncomment to run:
// demonstrateIntelligenceLayer();
