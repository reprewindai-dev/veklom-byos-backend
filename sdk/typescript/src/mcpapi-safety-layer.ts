/**
 * MCPAPI Safety Layer
 * Version: 2.0.0
 *
 * Breach prevention through:
 * - Real-time anomaly detection
 * - Behavioral learning & baselines
 * - Automatic trust suppression
 * - Request quarantine & hold
 * - Approval quorum enforcement
 */

import * as crypto from "crypto";

// ============================================================================
// SAFETY LAYER TYPES
// ============================================================================

export interface BehavioralBaseline {
  agent_id: string;
  observation_window_days: number;
  avg_requests_per_hour: number;
  std_dev_requests_per_hour: number;
  avg_failure_rate: number;
  std_dev_failure_rate: number;
  typical_capabilities: Map<string, number>; // capability_id -> frequency
  typical_time_windows: number[]; // [0-23 hours]
  typical_error_types: Map<string, number>; // error_type -> frequency
  confidence_score: number; // 0-100, how sure is this baseline?
  last_updated: string;
  is_locked: boolean; // after 30 days, lock baseline
}

export interface AnomalyDetection {
  detection_id: string;
  agent_id: string;
  detected_at: string;
  anomaly_type:
    | "request_spike"
    | "failure_spike"
    | "new_capability_access"
    | "off_hours_activity"
    | "unusual_pattern"
    | "capability_mutation"
    | "delegation_chain_exploit";
  baseline: BehavioralBaseline;
  current_metric: {
    requests_per_hour: number;
    failure_rate: number;
    new_capabilities: string[];
    time_of_day: number;
    requests_in_window: number;
  };
  deviation_score: number; // std devs from baseline
  anomaly_score: number; // 0-100
  severity: "low" | "medium" | "high" | "critical";
  recommended_action: "log" | "alert" | "quarantine" | "block";
  evidence_hash: string;
}

export interface QuarantinedRequest {
  quarantine_id: string;
  original_request: any; // MCPAPIRequest
  original_timestamp: string;
  quarantine_reason: string;
  anomalies_detected: AnomalyDetection[];
  trust_suppression_applied: boolean;
  suppressed_trust_score: number;
  approval_required: boolean;
  approvers_required: number;
  approvals_received: string[]; // approver IDs
  approval_deadline: string;
  status: "quarantined" | "approved" | "denied" | "auto_released";
  resolution_timestamp?: string;
  resolution_reason?: string;
}

export interface ApprovalQuorum {
  approval_id: string;
  quarantine_id: string;
  required_approvers: string[]; // who CAN approve
  current_approvals: Map<string, ApprovalSignature>;
  required_count: number; // M-of-N
  threshold_reached: boolean;
  approval_deadline: string;
  escalation_path: string[];
  escalation_triggered: boolean;
}

export interface ApprovalSignature {
  approver_id: string;
  approved_at: string;
  signature: string;
  approval_evidence: string; // video proof, or signed message
  trust_score: number; // approver's trust (can't approve if < 80)
}

export interface ProofDegradationRecord {
  pgl_hash: string;
  committed_at: string;
  last_verified: string;
  verification_status: "verified" | "unverified" | "disputed" | "revoked";
  verification_count: number;
  time_since_last_verification_days: number;
  dispute_evidence?: string[];
  alternative_proofs: string[]; // cross-chain hashes
  confidence_score: number;
  requires_reverification: boolean;
  reverification_deadline?: string;
}

export interface RequestReplayAttempt {
  replay_id: string;
  original_request_id: string;
  original_timestamp: string;
  replay_attempt_timestamp: string;
  original_agent_id: string;
  replay_agent_id: string;
  time_since_original_ms: number;
  signature: string;
  nonce: string;
  detected: boolean;
  blocked: boolean;
  evidence_hash: string;
}

export interface AgentLifecycleEvent {
  event_id: string;
  agent_id: string;
  event_type:
    | "created"
    | "activated"
    | "deactivated"
    | "compromised"
    | "deleted"
    | "archived"
    | "resurrected";
  timestamp: string;
  triggered_by: string; // admin_id
  reason: string;
  permissions_affected: string[];
  successor_agent?: string;
  archive_until?: string;
  evidence_hash: string;
}

// ============================================================================
// BEHAVIORAL BASELINE SERVICE
// ============================================================================

export class BehavioralBaselineService {
  private baselines: Map<string, BehavioralBaseline> = new Map();
  private observations: Map<string, any[]> = new Map(); // agent_id -> [observations]
  private readonly BASELINE_LOCK_DAYS = 30;
  private readonly CONFIDENCE_THRESHOLD = 0.8;

  /**
   * Record observation (called after each request)
   */
  recordObservation(
    agent_id: string,
    observation: {
      timestamp: string;
      requests_in_window: number;
      failure_rate: number;
      capabilities_used: string[];
      error_type?: string;
    }
  ): void {
    if (!this.observations.has(agent_id)) {
      this.observations.set(agent_id, []);
    }

    const obs = this.observations.get(agent_id)!;
    obs.push({
      ...observation,
      recorded_at: new Date().toISOString(),
    });

    // Keep only last 30 days
    const thirtyDaysAgo = Date.now() - 30 * 24 * 60 * 60 * 1000;
    const filtered = obs.filter(
      (o) => new Date(o.timestamp).getTime() > thirtyDaysAgo
    );
    this.observations.set(agent_id, filtered);
  }

  /**
   * Build baseline from observations
   */
  buildBaseline(agent_id: string): BehavioralBaseline {
    const obs = this.observations.get(agent_id) || [];

    if (obs.length < 10) {
      // Not enough data yet
      return {
        agent_id,
        observation_window_days: 0,
        avg_requests_per_hour: 0,
        std_dev_requests_per_hour: 0,
        avg_failure_rate: 0,
        std_dev_failure_rate: 0,
        typical_capabilities: new Map(),
        typical_time_windows: [],
        typical_error_types: new Map(),
        confidence_score: 0,
        last_updated: new Date().toISOString(),
        is_locked: false,
      };
    }

    // Calculate statistics
    const requestsPerHour = obs.map((o) => o.requests_in_window);
    const failureRates = obs.map((o) => o.failure_rate);

    const avgReq = requestsPerHour.reduce((a, b) => a + b) / requestsPerHour.length;
    const stdDevReq = Math.sqrt(
      requestsPerHour.reduce((sum, val) => sum + Math.pow(val - avgReq, 2), 0) /
        requestsPerHour.length
    );

    const avgFail = failureRates.reduce((a, b) => a + b) / failureRates.length;
    const stdDevFail = Math.sqrt(
      failureRates.reduce((sum, val) => sum + Math.pow(val - avgFail, 2), 0) /
        failureRates.length
    );

    // Typical capabilities
    const capabilities = new Map<string, number>();
    obs.forEach((o) => {
      o.capabilities_used?.forEach((cap: string) => {
        capabilities.set(cap, (capabilities.get(cap) || 0) + 1);
      });
    });

    // Typical time windows
    const hours = new Set<number>();
    obs.forEach((o) => {
      const hour = new Date(o.timestamp).getHours();
      hours.add(hour);
    });

    // Error types
    const errorTypes = new Map<string, number>();
    obs.forEach((o) => {
      if (o.error_type) {
        errorTypes.set(o.error_type, (errorTypes.get(o.error_type) || 0) + 1);
      }
    });

    const baseline: BehavioralBaseline = {
      agent_id,
      observation_window_days: 30,
      avg_requests_per_hour: avgReq,
      std_dev_requests_per_hour: stdDevReq,
      avg_failure_rate: avgFail,
      std_dev_failure_rate: stdDevFail,
      typical_capabilities: capabilities,
      typical_time_windows: Array.from(hours),
      typical_error_types: errorTypes,
      confidence_score: Math.min(100, (obs.length / 100) * 100),
      last_updated: new Date().toISOString(),
      is_locked: obs.length >= this.BASELINE_LOCK_DAYS,
    };

    this.baselines.set(agent_id, baseline);
    return baseline;
  }

  /**
   * Get baseline for agent
   */
  getBaseline(agent_id: string): BehavioralBaseline | null {
    return this.baselines.get(agent_id) || null;
  }

  /**
   * Lock baseline (prevent changes after 30 days)
   */
  lockBaseline(agent_id: string): void {
    const baseline = this.baselines.get(agent_id);
    if (baseline) {
      baseline.is_locked = true;
    }
  }
}

// ============================================================================
// ANOMALY DETECTION SERVICE
// ============================================================================

export class AnomalyDetectionService {
  private baselineService: BehavioralBaselineService;
  private anomalies: AnomalyDetection[] = [];
  private readonly ANOMALY_THRESHOLD = 2.0; // std devs from baseline

  constructor(baselineService: BehavioralBaselineService) {
    this.baselineService = baselineService;
  }

  /**
   * Detect anomalies in current request
   */
  detectAnomalies(
    agent_id: string,
    current_metric: {
      requests_per_hour: number;
      failure_rate: number;
      new_capabilities: string[];
      time_of_day: number;
      requests_in_window: number;
    }
  ): AnomalyDetection[] {
    const baseline = this.baselineService.getBaseline(agent_id);
    if (!baseline || baseline.confidence_score < 50) {
      return []; // Not enough baseline data
    }

    const detected: AnomalyDetection[] = [];

    // 1. Request spike detection
    const reqDeviation =
      (current_metric.requests_per_hour - baseline.avg_requests_per_hour) /
      baseline.std_dev_requests_per_hour;

    if (Math.abs(reqDeviation) > this.ANOMALY_THRESHOLD) {
      detected.push(
        this.createAnomaly(
          agent_id,
          "request_spike",
          current_metric,
          baseline,
          Math.abs(reqDeviation)
        )
      );
    }

    // 2. Failure spike detection
    const failDeviation =
      (current_metric.failure_rate - baseline.avg_failure_rate) /
      baseline.std_dev_failure_rate;

    if (Math.abs(failDeviation) > this.ANOMALY_THRESHOLD) {
      detected.push(
        this.createAnomaly(
          agent_id,
          "failure_spike",
          current_metric,
          baseline,
          Math.abs(failDeviation)
        )
      );
    }

    // 3. New capability access
    const newCaps = current_metric.new_capabilities.filter(
      (cap) => !baseline.typical_capabilities.has(cap)
    );

    if (newCaps.length > 0) {
      detected.push(
        this.createAnomaly(
          agent_id,
          "new_capability_access",
          current_metric,
          baseline,
          newCaps.length
        )
      );
    }

    // 4. Off-hours activity
    if (!baseline.typical_time_windows.includes(current_metric.time_of_day)) {
      detected.push(
        this.createAnomaly(
          agent_id,
          "off_hours_activity",
          current_metric,
          baseline,
          1
        )
      );
    }

    this.anomalies.push(...detected);
    return detected;
  }

  private createAnomaly(
    agent_id: string,
    anomaly_type: AnomalyDetection["anomaly_type"],
    current_metric: any,
    baseline: BehavioralBaseline,
    deviation_score: number
  ): AnomalyDetection {
    const anomalyScore = Math.min(
      100,
      (Math.abs(deviation_score) / 5) * 100
    );

    let severity: AnomalyDetection["severity"] = "low";
    let recommended_action: AnomalyDetection["recommended_action"] = "log";

    if (anomalyScore > 80) {
      severity = "critical";
      recommended_action = "block";
    } else if (anomalyScore > 60) {
      severity = "high";
      recommended_action = "quarantine";
    } else if (anomalyScore > 40) {
      severity = "medium";
      recommended_action = "quarantine";
    }

    return {
      detection_id: crypto.randomUUID(),
      agent_id,
      detected_at: new Date().toISOString(),
      anomaly_type,
      baseline,
      current_metric,
      deviation_score: Math.abs(deviation_score),
      anomaly_score: anomalyScore,
      severity,
      recommended_action,
      evidence_hash: crypto
        .createHash("sha256")
        .update(
          JSON.stringify({
            agent_id,
            anomaly_type,
            timestamp: new Date().toISOString(),
          })
        )
        .digest("base64"),
    };
  }

  getAnomalies(): AnomalyDetection[] {
    return this.anomalies;
  }

  getAnomaliesForAgent(agent_id: string): AnomalyDetection[] {
    return this.anomalies.filter((a) => a.agent_id === agent_id);
  }
}

// ============================================================================
// REQUEST QUARANTINE SERVICE
// ============================================================================

export class RequestQuarantineService {
  private quarantined: Map<string, QuarantinedRequest> = new Map();
  private readonly HOLD_DURATION_MS = 60 * 60 * 1000; // 1 hour default
  private readonly DEFAULT_APPROVERS_REQUIRED = 2;

  /**
   * Quarantine a request due to anomalies
   */
  quarantine(
    request: any,
    anomalies: AnomalyDetection[],
    trustSuppression?: { applied: boolean; suppressed_score: number }
  ): QuarantinedRequest {
    const qr: QuarantinedRequest = {
      quarantine_id: crypto.randomUUID(),
      original_request: request,
      original_timestamp: new Date().toISOString(),
      quarantine_reason: `Anomalies detected: ${anomalies.map((a) => a.anomaly_type).join(", ")}`,
      anomalies_detected: anomalies,
      trust_suppression_applied: trustSuppression?.applied || false,
      suppressed_trust_score: trustSuppression?.suppressed_score || 0,
      approval_required: anomalies.some((a) => a.severity === "high" || a.severity === "critical"),
      approvers_required: this.DEFAULT_APPROVERS_REQUIRED,
      approvals_received: [],
      approval_deadline: new Date(
        Date.now() + this.HOLD_DURATION_MS
      ).toISOString(),
      status: "quarantined",
    };

    this.quarantined.set(qr.quarantine_id, qr);
    return qr;
  }

  /**
   * Get quarantined request
   */
  getQuarantined(quarantine_id: string): QuarantinedRequest | null {
    return this.quarantined.get(quarantine_id) || null;
  }

  /**
   * Approve quarantined request
   */
  approve(
    quarantine_id: string,
    approver_id: string,
    signature: string
  ): boolean {
    const qr = this.quarantined.get(quarantine_id);
    if (!qr) return false;

    if (!qr.approvals_received.includes(approver_id)) {
      qr.approvals_received.push(approver_id);
    }

    if (
      qr.approvals_received.length >= qr.approvers_required &&
      qr.approval_required
    ) {
      qr.status = "approved";
      qr.resolution_timestamp = new Date().toISOString();
      qr.resolution_reason = "Quorum of approvers reached";
      return true;
    }

    return false;
  }

  /**
   * Deny quarantined request
   */
  deny(quarantine_id: string, reason: string): boolean {
    const qr = this.quarantined.get(quarantine_id);
    if (!qr) return false;

    qr.status = "denied";
    qr.resolution_timestamp = new Date().toISOString();
    qr.resolution_reason = reason;
    return true;
  }

  /**
   * Check if quarantine expired and auto-release or auto-deny
   */
  processExpiredQuarantines(): QuarantinedRequest[] {
    const now = Date.now();
    const processed: QuarantinedRequest[] = [];

    this.quarantined.forEach((qr) => {
      if (qr.status === "quarantined") {
        const deadline = new Date(qr.approval_deadline).getTime();

        if (now > deadline) {
          // Auto-deny on timeout
          qr.status = "denied";
          qr.resolution_timestamp = new Date().toISOString();
          qr.resolution_reason = "Approval deadline expired";
          processed.push(qr);
        }
      }
    });

    return processed;
  }

  /**
   * Get all quarantined requests
   */
  getAllQuarantined(): QuarantinedRequest[] {
    return Array.from(this.quarantined.values());
  }
}

// ============================================================================
// APPROVAL QUORUM SERVICE
// ============================================================================

export class ApprovalQuorumService {
  private quorums: Map<string, ApprovalQuorum> = new Map();
  private readonly DEFAULT_QUORUM_SIZE = 2; // M-of-N
  private readonly TRUST_THRESHOLD = 80; // approvers must have trust >= 80

  /**
   * Create approval quorum for high-risk request
   */
  createQuorum(
    quarantine_id: string,
    required_approvers: string[],
    requiredCount: number = this.DEFAULT_QUORUM_SIZE,
    escalationPath: string[] = []
  ): ApprovalQuorum {
    const quorum: ApprovalQuorum = {
      approval_id: crypto.randomUUID(),
      quarantine_id,
      required_approvers,
      current_approvals: new Map(),
      required_count: requiredCount,
      threshold_reached: false,
      approval_deadline: new Date(Date.now() + 1 * 60 * 60 * 1000).toISOString(),
      escalation_path: escalationPath,
      escalation_triggered: false,
    };

    this.quorums.set(quorum.approval_id, quorum);
    return quorum;
  }

  /**
   * Record approval signature
   */
  recordApproval(
    approval_id: string,
    approver_id: string,
    signature: string,
    approverTrustScore: number,
    approvalEvidence: string
  ): boolean {
    const quorum = this.quorums.get(approval_id);
    if (!quorum) return false;

    // Check if approver has sufficient trust
    if (approverTrustScore < this.TRUST_THRESHOLD) {
      return false;
    }

    // Check if approver is authorized
    if (!quorum.required_approvers.includes(approver_id)) {
      return false;
    }

    quorum.current_approvals.set(approver_id, {
      approver_id,
      approved_at: new Date().toISOString(),
      signature,
      approval_evidence: approvalEvidence,
      trust_score: approverTrustScore,
    });

    if (quorum.current_approvals.size >= quorum.required_count) {
      quorum.threshold_reached = true;
    }

    return true;
  }

  /**
   * Check if quorum threshold reached
   */
  isThresholdReached(approval_id: string): boolean {
    const quorum = this.quorums.get(approval_id);
    return quorum?.threshold_reached || false;
  }

  /**
   * Trigger escalation (notify supervisors)
   */
  triggerEscalation(approval_id: string): string[] {
    const quorum = this.quorums.get(approval_id);
    if (!quorum) return [];

    quorum.escalation_triggered = true;
    return quorum.escalation_path;
  }

  /**
   * Get quorum details
   */
  getQuorum(approval_id: string): ApprovalQuorum | null {
    return this.quorums.get(approval_id) || null;
  }
}

// ============================================================================
// REPLAY ATTACK PREVENTION SERVICE
// ============================================================================

export class ReplayAttackPreventionService {
  private usedNonces: Set<string> = new Set();
  private requestHashes: Map<string, number> = new Map(); // request_hash -> timestamp
  private readonly NONCE_TTL_MS = 30 * 1000; // 30 seconds
  private readonly DEDUP_WINDOW_MS = 1000; // 1 second

  /**
   * Generate nonce for request
   */
  generateNonce(): string {
    return crypto.randomBytes(32).toString("base64");
  }

  /**
   * Verify nonce (prevent replay)
   */
  verifyNonce(nonce: string): boolean {
    if (this.usedNonces.has(nonce)) {
      return false; // Already used
    }

    this.usedNonces.add(nonce);

    // Cleanup old nonces
    setTimeout(() => {
      this.usedNonces.delete(nonce);
    }, this.NONCE_TTL_MS);

    return true;
  }

  /**
   * Detect request duplication (same request in dedup window)
   */
  checkRequestDuplication(request: any): boolean {
    const requestHash = crypto
      .createHash("sha256")
      .update(JSON.stringify(request))
      .digest("hex");

    const lastSeen = this.requestHashes.get(requestHash);
    const now = Date.now();

    if (lastSeen && now - lastSeen < this.DEDUP_WINDOW_MS) {
      return true; // Duplicate detected
    }

    this.requestHashes.set(requestHash, now);
    return false;
  }

  /**
   * Verify request signature time-locking (signature must be recent)
   */
  verifySignatureAge(signature_timestamp: string, max_age_seconds: number = 30): boolean {
    const sig_time = new Date(signature_timestamp).getTime();
    const now = Date.now();
    const age_ms = now - sig_time;

    return age_ms < max_age_seconds * 1000;
  }

  /**
   * Record replay attempt
   */
  recordReplayAttempt(
    original_request_id: string,
    original_timestamp: string,
    replay_agent_id: string,
    nonce: string,
    signature: string
  ): RequestReplayAttempt {
    return {
      replay_id: crypto.randomUUID(),
      original_request_id,
      original_timestamp,
      replay_attempt_timestamp: new Date().toISOString(),
      original_agent_id: original_request_id.split("-")[0],
      replay_agent_id,
      time_since_original_ms:
        Date.now() - new Date(original_timestamp).getTime(),
      signature,
      nonce,
      detected: true,
      blocked: true,
      evidence_hash: crypto
        .createHash("sha256")
        .update(
          JSON.stringify({
            original_request_id,
            replay_agent_id,
            timestamp: new Date().toISOString(),
          })
        )
        .digest("base64"),
    };
  }
}

// ============================================================================
// PROOF DEGRADATION SERVICE (PGL VERIFICATION)
// ============================================================================

export class ProofDegradationService {
  private proofs: Map<string, ProofDegradationRecord> = new Map();
  private readonly REVERIFICATION_INTERVAL_DAYS = 30;
  private readonly CONFIDENCE_DECAY_PER_DAY = 0.5; // lose 0.5% confidence per day

  /**
   * Register proof in system
   */
  registerProof(pgl_hash: string, alternative_proofs: string[] = []): ProofDegradationRecord {
    const record: ProofDegradationRecord = {
      pgl_hash,
      committed_at: new Date().toISOString(),
      last_verified: new Date().toISOString(),
      verification_status: "unverified",
      verification_count: 0,
      time_since_last_verification_days: 0,
      alternative_proofs,
      confidence_score: 100,
      requires_reverification: false,
    };

    this.proofs.set(pgl_hash, record);
    return record;
  }

  /**
   * Verify proof (increases verification count + resets age)
   */
  verifyProof(pgl_hash: string): boolean {
    const record = this.proofs.get(pgl_hash);
    if (!record) return false;

    record.last_verified = new Date().toISOString();
    record.verification_count++;
    record.time_since_last_verification_days = 0;
    record.verification_status = "verified";

    return true;
  }

  /**
   * Decay confidence over time (called periodically)
   */
  applyConfidenceDecay(): void {
    const now = Date.now();

    this.proofs.forEach((record) => {
      const lastVerified = new Date(record.last_verified).getTime();
      const daysSince = (now - lastVerified) / (1000 * 60 * 60 * 24);

      record.time_since_last_verification_days = daysSince;
      record.confidence_score -= daysSince * this.CONFIDENCE_DECAY_PER_DAY;
      record.confidence_score = Math.max(0, record.confidence_score);

      // Require reverification every 30 days
      if (daysSince > this.REVERIFICATION_INTERVAL_DAYS) {
        record.requires_reverification = true;
        record.reverification_deadline = new Date(
          now + this.REVERIFICATION_INTERVAL_DAYS * 24 * 60 * 60 * 1000
        ).toISOString();
      }
    });
  }

  /**
   * Dispute proof (challenge its validity)
   */
  disputeProof(pgl_hash: string, evidence: string[]): void {
    const record = this.proofs.get(pgl_hash);
    if (!record) return;

    record.verification_status = "disputed";
    record.dispute_evidence = evidence;
    record.confidence_score = Math.max(0, record.confidence_score - 50);
  }

  /**
   * Revoke proof (declare invalid)
   */
  revokeProof(pgl_hash: string, reason: string): void {
    const record = this.proofs.get(pgl_hash);
    if (!record) return;

    record.verification_status = "revoked";
    record.confidence_score = 0;
  }

  /**
   * Get proof record
   */
  getProof(pgl_hash: string): ProofDegradationRecord | null {
    return this.proofs.get(pgl_hash) || null;
  }

  /**
   * Get proofs requiring reverification
   */
  getProofsRequiringReverification(): ProofDegradationRecord[] {
    return Array.from(this.proofs.values()).filter(
      (p) => p.requires_reverification
    );
  }
}

// ============================================================================
// AGENT LIFECYCLE SERVICE
// ============================================================================

export class AgentLifecycleService {
  private lifecycleEvents: AgentLifecycleEvent[] = [];
  private agentStates: Map<
    string,
    {
      state: "created" | "active" | "deactivated" | "archived" | "deleted";
      successor?: string;
      archived_until?: string;
      permissions_frozen?: boolean;
    }
  > = new Map();

  /**
   * Create agent (birth event)
   */
  createAgent(agent_id: string, created_by: string): AgentLifecycleEvent {
    const event: AgentLifecycleEvent = {
      event_id: crypto.randomUUID(),
      agent_id,
      event_type: "created",
      timestamp: new Date().toISOString(),
      triggered_by: created_by,
      reason: "Agent instantiation",
      permissions_affected: [],
      evidence_hash: crypto
        .createHash("sha256")
        .update(
          JSON.stringify({
            agent_id,
            event_type: "created",
            timestamp: new Date().toISOString(),
          })
        )
        .digest("base64"),
    };

    this.lifecycleEvents.push(event);
    this.agentStates.set(agent_id, { state: "active" });
    return event;
  }

  /**
   * Deactivate agent (soft freeze, keep evidence)
   */
  deactivateAgent(
    agent_id: string,
    deactivated_by: string,
    reason: string,
    permissions_affected: string[]
  ): AgentLifecycleEvent {
    const event: AgentLifecycleEvent = {
      event_id: crypto.randomUUID(),
      agent_id,
      event_type: "deactivated",
      timestamp: new Date().toISOString(),
      triggered_by: deactivated_by,
      reason,
      permissions_affected,
      evidence_hash: crypto
        .createHash("sha256")
        .update(
          JSON.stringify({
            agent_id,
            event_type: "deactivated",
            timestamp: new Date().toISOString(),
          })
        )
        .digest("base64"),
    };

    this.lifecycleEvents.push(event);
    const state = this.agentStates.get(agent_id) || { state: "active" };
    state.state = "deactivated";
    state.permissions_frozen = true;
    this.agentStates.set(agent_id, state);

    return event;
  }

  /**
   * Delete agent (hard delete, archive evidence for 7 years)
   */
  deleteAgent(
    agent_id: string,
    deleted_by: string,
    reason: string
  ): AgentLifecycleEvent {
    const event: AgentLifecycleEvent = {
      event_id: crypto.randomUUID(),
      agent_id,
      event_type: "deleted",
      timestamp: new Date().toISOString(),
      triggered_by: deleted_by,
      reason,
      permissions_affected: ["*"], // all permissions revoked
      archive_until: new Date(
        Date.now() + 7 * 365 * 24 * 60 * 60 * 1000
      ).toISOString(),
      evidence_hash: crypto
        .createHash("sha256")
        .update(
          JSON.stringify({
            agent_id,
            event_type: "deleted",
            timestamp: new Date().toISOString(),
          })
        )
        .digest("base64"),
    };

    this.lifecycleEvents.push(event);
    const state = this.agentStates.get(agent_id) || { state: "active" };
    state.state = "deleted";
    state.archived_until = event.archive_until;
    this.agentStates.set(agent_id, state);

    return event;
  }

  /**
   * Archive agent (save state, prevent resurrection)
   */
  archiveAgent(
    agent_id: string,
    archived_by: string,
    archive_until: string
  ): AgentLifecycleEvent {
    const event: AgentLifecycleEvent = {
      event_id: crypto.randomUUID(),
      agent_id,
      event_type: "archived",
      timestamp: new Date().toISOString(),
      triggered_by: archived_by,
      reason: "Agent archived",
      permissions_affected: ["*"],
      archive_until,
      evidence_hash: crypto
        .createHash("sha256")
        .update(
          JSON.stringify({
            agent_id,
            event_type: "archived",
            timestamp: new Date().toISOString(),
          })
        )
        .digest("base64"),
    };

    this.lifecycleEvents.push(event);
    const state = this.agentStates.get(agent_id) || { state: "active" };
    state.state = "archived";
    state.archived_until = archive_until;
    this.agentStates.set(agent_id, state);

    return event;
  }

  /**
   * Delegate agent permissions (succession)
   */
  delegatePermissions(
    agent_id: string,
    successor_id: string,
    delegated_by: string,
    permissions: string[]
  ): AgentLifecycleEvent {
    const event: AgentLifecycleEvent = {
      event_id: crypto.randomUUID(),
      agent_id,
      event_type: "deactivated",
      timestamp: new Date().toISOString(),
      triggered_by: delegated_by,
      reason: `Permissions delegated to ${successor_id}`,
      successor_agent: successor_id,
      permissions_affected: permissions,
      evidence_hash: crypto
        .createHash("sha256")
        .update(
          JSON.stringify({
            agent_id,
            successor_id,
            timestamp: new Date().toISOString(),
          })
        )
        .digest("base64"),
    };

    this.lifecycleEvents.push(event);
    const state = this.agentStates.get(agent_id) || { state: "active" };
    state.successor = successor_id;
    this.agentStates.set(agent_id, state);

    return event;
  }

  /**
   * Get agent current state
   */
  getAgentState(
    agent_id: string
  ): {
    state: "created" | "active" | "deactivated" | "archived" | "deleted";
    successor?: string;
    archived_until?: string;
    permissions_frozen?: boolean;
  } | null {
    return this.agentStates.get(agent_id) || null;
  }

  /**
   * Get agent lifecycle events
   */
  getAgentLifecycle(agent_id: string): AgentLifecycleEvent[] {
    return this.lifecycleEvents.filter((e) => e.agent_id === agent_id);
  }

  /**
   * Verify agent can execute (not deleted/archived)
   */
  canAgentExecute(agent_id: string): boolean {
    const state = this.agentStates.get(agent_id);
    if (!state) return true; // New agent, can execute
    return state.state === "active";
  }

  /**
   * Record agent action in lifecycle log
   */
  recordAgentAction(
    agent_id: string,
    capability_id: string,
    action: string,
    result: "success" | "denied" | "error",
    evidence_hash: string,
    trust_delta: number
  ): void {
    const event: AgentLifecycleEvent = {
      event_id: crypto.randomUUID(),
      agent_id,
      event_type: result === "success" ? "activated" : "deactivated",
      timestamp: new Date().toISOString(),
      triggered_by: "system",
      reason: `Action: ${action} on capability: ${capability_id} with status: ${result}`,
      permissions_affected: [],
      evidence_hash,
    };
    this.lifecycleEvents.push(event);
  }
}

// ============================================================================
// EXAMPLE USAGE
// ============================================================================

function demonstrateSafetyLayer() {
  // Initialize services
  const baselineService = new BehavioralBaselineService();
  const anomalyService = new AnomalyDetectionService(baselineService);
  const quarantineService = new RequestQuarantineService();
  const quorumService = new ApprovalQuorumService();
  const replayService = new ReplayAttackPreventionService();
  const proofService = new ProofDegradationService();
  const lifecycleService = new AgentLifecycleService();

  // Scenario 1: Normal agent behavior
  console.log("=== Scenario 1: Normal Behavior ===");
  const agent_id = "agent-001";

  for (let i = 0; i < 20; i++) {
    baselineService.recordObservation(agent_id, {
      timestamp: new Date().toISOString(),
      requests_in_window: 10 + Math.random() * 5, // 10-15 req/hour
      failure_rate: 0.01 + Math.random() * 0.01, // 1-2% failure
      capabilities_used: ["search", "database.read"],
    });
  }

  baselineService.buildBaseline(agent_id);
  console.log("Baseline built for agent");

  // Scenario 2: Anomaly detection
  console.log("\n=== Scenario 2: Anomaly Detected ===");
  const anomalies = anomalyService.detectAnomalies(agent_id, {
    requests_per_hour: 500, // SPIKE!
    failure_rate: 0.5, // High failures
    new_capabilities: ["database.delete", "user.update"],
    time_of_day: 3, // 3 AM
    requests_in_window: 500,
  });

  console.log(`Anomalies detected: ${anomalies.length}`);
  anomalies.forEach((a) => {
    console.log(`  - ${a.anomaly_type} (severity: ${a.severity})`);
  });

  // Scenario 3: Request quarantine
  console.log("\n=== Scenario 3: Request Quarantined ===");
  const mockRequest = {
    connection_id: "conn-123",
    agent_id,
    capability_id: "database.delete",
    action: "execute",
  };

  const quarantine = quarantineService.quarantine(mockRequest, anomalies, {
    applied: true,
    suppressed_score: 20,
  });

  console.log(`Quarantine ID: ${quarantine.quarantine_id}`);
  console.log(`Status: ${quarantine.status}`);
  console.log(`Requires approval: ${quarantine.approval_required}`);
  console.log(`Approvers needed: ${quarantine.approvers_required}`);

  // Scenario 4: Approval quorum
  console.log("\n=== Scenario 4: Approval Quorum ===");
  const quorum = quorumService.createQuorum(quarantine.quarantine_id, [
    "admin-001",
    "admin-002",
    "security-lead",
  ]);

  quorumService.recordApproval(
    quorum.approval_id,
    "admin-001",
    "sig-001",
    85,
    "approved-video-proof"
  );
  quorumService.recordApproval(
    quorum.approval_id,
    "admin-002",
    "sig-002",
    92,
    "approved-email-confirmation"
  );

  console.log(
    `Threshold reached: ${quorumService.isThresholdReached(quorum.approval_id)}`
  );

  // Scenario 5: Proof degradation
  console.log("\n=== Scenario 5: Proof Degradation ===");
  const proof = proofService.registerProof("pgl-hash-123", [
    "blockchain-hash-456",
  ]);
  console.log(`Proof registered. Confidence: ${proof.confidence_score}%`);

  proofService.verifyProof("pgl-hash-123");
  console.log("Proof verified");

  // Scenario 6: Agent lifecycle
  console.log("\n=== Scenario 6: Agent Lifecycle ===");
  lifecycleService.createAgent("agent-new", "admin-001");
  console.log("Agent created");

  const deactivation = lifecycleService.deactivateAgent(
    "agent-new",
    "security-lead",
    "Suspected compromise",
    ["*"]
  );
  console.log(`Agent deactivated: ${deactivation.event_type}`);

  const canExecute = lifecycleService.canAgentExecute("agent-new");
  console.log(`Can agent execute? ${canExecute}`);

  // Scenario 7: Replay attack prevention
  console.log("\n=== Scenario 7: Replay Attack Prevention ===");
  const nonce = replayService.generateNonce();
  console.log(`Nonce generated: ${nonce.substring(0, 20)}...`);

  const nonceValid1 = replayService.verifyNonce(nonce);
  const nonceValid2 = replayService.verifyNonce(nonce);

  console.log(`First use valid: ${nonceValid1}`);
  console.log(`Second use valid (replay attempt): ${nonceValid2}`);
}

// Uncomment to run:
// demonstrateSafetyLayer();
