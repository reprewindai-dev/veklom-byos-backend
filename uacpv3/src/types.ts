export type SurfaceId = "deterministic-engine" | "sunnyvale" | "silicon-valley" | "archives" | "status";

export type PlanStatus = "draft" | "review" | "approved" | "active" | "completed";
export type RunStatus = "queued" | "executing" | "completed" | "blocked" | "failed";
export type SkillStatus = "approved" | "review" | "quarantined";
export type RiskTier = "low" | "medium" | "high" | "critical";
export type VoteDirection = "approve" | "challenge" | "veto";
export type ResearchSourceHealth = "online" | "degraded" | "offline";
export type RunStageStatus = "completed" | "failed";
export type GovernanceProposalType = "committee" | "skill" | "workflow";
export type GovernanceProposalStatus = "proposed";
export type OperatorRunStatus = "queued" | "running" | "completed" | "failed" | "paused" | "escalated";
export type WorkerRuntimeStatus = "idle" | "running" | "paused" | "error";
export type BackendEventSeverity = "info" | "warning" | "critical";
export type ModelProviderId = "groq" | "huggingface" | "ollama" | "gemini" | "deterministic";
export type ModelProviderHealth = "ready" | "degraded" | "missing" | "disabled";
export type OutboundContactKind = "customer" | "vendor";
export type OutboundContactStatus = "queued" | "sent" | "failed" | "suppressed";
export type OutboundMessageStatus = "queued" | "sent" | "failed";

export interface PlanNode {
  id: string;
  label: string;
  stage: "intent" | "reasoning" | "governance" | "execution" | "evidence" | "continuity";
  ownerCommitteeId: string;
  pillarIds: string[];
  summary: string;
  latencyMs: number;
}

export interface PlanEdge {
  from: string;
  to: string;
}

export interface CommitteeVote {
  member: string;
  model: string;
  vote: VoteDirection;
  rationale: string;
}

export interface InstitutionalPlan {
  id: string;
  title: string;
  intent: string;
  objective: string;
  pricingModel: string;
  payingUser: string;
  status: PlanStatus;
  revision: number;
  riskTier: RiskTier;
  pillars: string[];
  committeeIds: string[];
  workflowIds: string[];
  skillIds: string[];
  escalationRuleIds: string[];
  graph: {
    nodes: PlanNode[];
    edges: PlanEdge[];
  };
  votes: CommitteeVote[];
  guardrails: string[];
  successMetrics: string[];
  researchQuery?: string;
  researchReferences?: CompiledArtifactReference[];
  proposals?: GovernanceProposal[];
  createdAt: string;
}

export interface GovernedRun {
  id: string;
  planId: string;
  status: RunStatus;
  currentStage: string;
  progress: number;
  approvals: number;
  evidenceCount: number;
  startedAt: string;
  completedAt?: string;
  output?: string;
  stages?: RunStageRecord[];
  artifact?: CompiledArtifact;
  errors?: string[];
}

export interface EventItem {
  id: string;
  type: string;
  timestamp: string;
  message: string;
  surface: SurfaceId;
  metadata?: Record<string, unknown>;
  previousHash?: string;
  recordHash?: string;
}

export interface Pillar {
  id: string;
  name: string;
  mandate: string;
  kpi: string;
}

export interface Committee {
  id: string;
  name: string;
  purpose: string;
  authority: string;
  chair: string;
  members: string[];
  escalation: string;
  allowedActions: string[];
  vetoConditions: string[];
  pillarIds: string[];
}

export interface EscalationRule {
  id: string;
  name: string;
  description: string;
  trigger: string;
  route: string[];
  severity: RiskTier;
  ownerCommitteeId: string;
  pillarIds: string[];
}

export interface OperatorCommittee {
  id: string;
  name: string;
  purpose: string;
  pillarIds: string[];
  workerIds: string[];
  chair?: string;
  sponsor?: string;
  decisionFramework?: "RACI" | "DACI" | "RAPID";
  cadencePerDay?: number;
  regroupIntervalMinutes?: number;
  successMetrics?: string[];
}

export interface SkillArtifact {
  id: string;
  name: string;
  category: string;
  description: string;
  allowedTools: string[];
  source: string;
  ref: string;
  treeSha: string;
  status: SkillStatus;
  pillarIds: string[];
  governingCommitteeId?: string;
  usableByCommitteeIds?: string[];
  requiredEvidence?: string[];
  publishRisk?: RiskTier;
  inputType?: string;
  outputType?: string;
  sla?: string;
  revisionHistory?: string[];
}

export interface WorkflowArtifact {
  id: string;
  name: string;
  category: string;
  description: string;
  outcome: string;
  pillarIds: string[];
}

export interface ArchiveEntry {
  id: string;
  title: string;
  category: "plan" | "run" | "policy" | "override" | "research";
  summary: string;
  createdAt: string;
  lineage: string[];
  metadata?: Record<string, unknown>;
  previousHash?: string;
  recordHash?: string;
}

export interface GovernanceProposal {
  id: string;
  type: GovernanceProposalType;
  name: string;
  rationale: string;
  status: GovernanceProposalStatus;
}

export interface ResearchSignal {
  id: string;
  source: string;
  title: string;
  category: string;
  strength: number;
  publishedAt: string;
  url?: string;
  abstract?: string;
  authors?: string[];
  doi?: string;
}

export interface ResearchSourceStatus {
  id: string;
  name: string;
  status: ResearchSourceHealth;
  lastSyncAt?: string;
  lastLatencyMs?: number;
  itemCount: number;
  error?: string;
}

export interface RunStageRecord {
  stage: string;
  status: RunStageStatus;
  startedAt: string;
  completedAt: string;
  summary: string;
  sourceCount?: number;
}

export interface CompiledArtifactPhaseOutput {
  stage: string;
  summary: string;
}

export interface CompiledArtifactReference {
  title: string;
  source: string;
  url?: string;
  publishedAt?: string;
}

export interface CompiledArtifact {
  id: string;
  title: string;
  objective: string;
  summary: string;
  sourceCount: number;
  signalSources: string[];
  workflowIds: string[];
  skillIds: string[];
  governanceSummary: string;
  nextAction: string;
  archiveRecordIds: string[];
  phaseOutputs: CompiledArtifactPhaseOutput[];
  references: CompiledArtifactReference[];
  createdAt: string;
}

export interface TelemetryMetric {
  label: string;
  value: number;
  unit: string;
  trend: "up" | "down" | "stable";
}

export interface ControlTelemetry {
  latencyMs: number;
  determinismScore: number;
  committeeHealth: number;
  policyAlignment: number;
  archiveCoverage: number;
  sourceHealth: number;
  activeRunCount: number;
  totalSignals: number;
  lastResearchSyncAt?: string;
  metrics: TelemetryMetric[];
}

export interface StatusHistoryDay {
  date: string;
  status: "operational" | "degraded" | "incident";
  incidentCount: number;
  runCount: number;
  archiveCount: number;
}

export interface StatusIncident {
  id: string;
  type: string;
  status: "investigating" | "resolved" | "monitoring";
  severity: "info" | "warning" | "critical";
  title: string;
  summary: string;
  startedAt: string;
  resolvedAt?: string;
  evidenceRefs: string[];
}

export interface StatusPageSnapshot {
  generatedAt: string;
  service: {
    name: string;
    status: "operational" | "degraded" | "incident";
    uptimeObservedSeconds: number;
    publicUrl?: string;
  };
  stats: {
    observedUptimePercent: number;
    runSuccessRate: number;
    archiveProofCoverage: number;
    policyAlignment: number;
    determinismScore: number;
    activeRunCount: number;
    totalRuns: number;
    completedRuns: number;
    incidentCount14d: number;
    evidenceExports: number;
    providerReadyCount: number;
    providerConfiguredCount: number;
    redisBackedEventStream: boolean;
  };
  components: Array<{
    id: string;
    name: string;
    status: "operational" | "degraded" | "incident";
    detail: string;
  }>;
  history: StatusHistoryDay[];
  incidents: StatusIncident[];
}

export interface BootstrapPayload {
  system: string;
  version: string;
  thesis: string;
  surfaces: Array<{ id: SurfaceId; name: string; purpose: string }>;
  doctrines: string[];
  status?: string;
  identity?: string;
  userEmail?: string;
}

export interface ModelProviderStatus {
  id: Exclude<ModelProviderId, "deterministic">;
  label: string;
  health: ModelProviderHealth;
  configured: boolean;
  active: boolean;
  model?: string;
  baseUrl?: string;
  detail: string;
}

export interface ModelProviderSnapshot {
  defaultProvider: ModelProviderId;
  activeProvider: ModelProviderId;
  allowGeminiFallback: boolean;
  updatedAt: string;
  statuses: ModelProviderStatus[];
}

export interface GovernanceRegistry {
  version: string;
  updatedAt: string;
  updatedBy: string;
  pillars: Pillar[];
  committees: Committee[];
  skills: SkillArtifact[];
  workflows: WorkflowArtifact[];
  escalationRules: EscalationRule[];
  operatorCommittees: OperatorCommittee[];
  workers: OperatorWorker[];
  minimumLiveWorkerIds: string[];
}

export interface CanonicalPlanTemplate {
  id: string;
  name: string;
  objective: string;
  ownerCouncil: string;
  payingUser: string;
  pricingModel: string;
  executionWindow: string;
  committeeRoute: string[];
  requiredSkillIds: string[];
  workflowIds: string[];
  admissionRules: string[];
  vetoRules: string[];
  successMetrics: string[];
}

export interface EnterpriseCouncilView {
  id: string;
  name: string;
  purpose: string;
  powers: string[];
  escalationRule: string;
  mappedOperatorCommitteeIds: string[];
  workerCount: number;
  skillCount: number;
}

export interface EnterpriseCheckView {
  id: "pulse" | "mirror" | "sentinel";
  name: string;
  ownerWorkerId: string;
  ownerCommitteeId: string;
  status: "pass" | "watch" | "fail";
  summary: string;
  purpose: string;
  passCondition: string;
  failCondition: string;
  metric: number;
  lastCheckedAt: string;
}

export interface OperatorWorker {
  id: string;
  displayName: string;
  committeeId: string;
  primaryPillar: string;
  secondaryPillars: string[];
  purpose: string;
  schedule: string;
  intervalMinutes: number;
  inputSources: string[];
  allowedActions: string[];
  forbiddenActions: string[];
  outputArtifact: string;
  archiveEventType: string;
  escalationRuleId: string;
  statusFields: string[];
  requiredSecrets: string[];
}

export interface WorkerRuntimeState {
  workerId: string;
  status: WorkerRuntimeStatus;
  paused: boolean;
  lastHeartbeatAt?: string;
  lastRunAt?: string;
  lastRunId?: string;
  nextRunAt?: string;
  lastError?: string;
}

export interface OperatorRun {
  id: string;
  workerId: string;
  committeeId: string;
  pillarId: string;
  startedAt: string;
  completedAt?: string;
  status: OperatorRunStatus;
  inputs: string[];
  actionsTaken: string[];
  evidenceCreated: string[];
  archiveRef?: string;
  escalations: string[];
  errors: string[];
  nextRecommendation: string;
}

export interface OutboundContact {
  id: string;
  kind: OutboundContactKind;
  email: string;
  accountLabel: string;
  company?: string;
  workspaceId?: string;
  sourceEventIds: string[];
  assignedWorkerId: string;
  status: OutboundContactStatus;
  createdAt: string;
  updatedAt: string;
  lastActivityAt?: string;
  lastAttemptAt?: string;
  lastSentAt?: string;
  lastMessageId?: string;
  attemptCount: number;
  metadata?: Record<string, unknown>;
}

export interface OutboundMessage {
  id: string;
  contactId: string;
  workerId: string;
  provider: "resend";
  subject: string;
  body: string;
  status: OutboundMessageStatus;
  createdAt: string;
  sentAt?: string;
  providerMessageId?: string;
  error?: string;
  archiveRef?: string;
}

export interface OutboundRuntimeSnapshot {
  enabled: boolean;
  provider: "resend" | "disabled";
  fromConfigured: boolean;
  queuedContacts: number;
  sentMessages: number;
  failedMessages: number;
  customerQueue: number;
  vendorQueue: number;
}

export interface OperatorCommitteeRuntimeView {
  id: string;
  name: string;
  purpose: string;
  chair?: string;
  sponsor?: string;
  decisionFramework?: "RACI" | "DACI" | "RAPID";
  cadencePerDay: number;
  regroupIntervalMinutes: number;
  lastRegroupAt?: string;
  nextRegroupAt: string;
  regroupsToday: number;
  workerCount: number;
  activeWorkerCount: number;
  queuedWorkerCount: number;
  backlog: string[];
  activeExecutionWindow: {
    id: string;
    label: string;
    objective: string;
  };
  benefitSummary: string;
  successMetrics: string[];
}

export interface BackendProductEvent {
  eventId: string;
  eventType: string;
  source: "backend";
  workspaceId?: string;
  tenantId?: string;
  userId?: string;
  entityType: string;
  entityId: string;
  severity: BackendEventSeverity;
  status: string;
  timestamp: string;
  payload: Record<string, unknown>;
  pillarIds: string[];
  committeeIds: string[];
  workerIds: string[];
  archiveId?: string;
}

export interface BackendTruthSummary {
  liveUsers: number;
  signups: number;
  evaluationsStarted: number;
  runsCompleted: number;
  pipelineTests: number;
  endpointCalls: number;
  failedRoutes: number;
  reserveBalance: number;
  revenue: number;
  evidenceExports: number;
  mfaEvents: number;
  marketplaceInstalls: number;
  lastEventAt?: string;
}

export interface CommandCenterSnapshot {
  backend: BackendTruthSummary;
  institution: {
    workerCount: number;
    activeWorkerCount: number;
    pausedWorkerCount: number;
    operatorRunCount: number;
    openEscalations: number;
    archiveCount: number;
    planCount: number;
    governedRunCount: number;
  };
  governance?: {
    councilCount: number;
    canonicalPlanCount: number;
    enterpriseCheckCount: number;
    passingEnterpriseChecks: number;
  };
}

export type OperatingSignalKind = "evaluation" | "growth" | "field-intelligence";
export type OperatingSignalStatus = "open" | "watch" | "escalated" | "ready";
export type SunnyvaleDataMode = "live" | "research-only" | "waiting";

export interface OperatingSignal {
  id: string;
  kind: OperatingSignalKind;
  title: string;
  summary: string;
  category: string;
  accountLabel: string;
  workspaceId?: string;
  tier?: string;
  evaluationStage?: string;
  lastActivityAt?: string;
  runsUsed?: number;
  runsLimit?: number;
  endpointStatus?: string;
  evidenceActivity?: string;
  billingState?: string;
  reserveState?: string;
  mfaState?: string;
  errorsCount?: number;
  score: number;
  riskScore: number;
  confidence: number;
  evidence: string[];
  recommendedAction: string;
  assignedWorkerIds: string[];
  committeeId?: string;
  pillarIds: string[];
  archiveRef?: string;
  status: OperatingSignalStatus;
  sourceEventIds: string[];
}

export interface SunnyvaleOverview {
  totalSignals: number;
  activeEvaluations: number;
  seriousSignals: number;
  reserveBalance: number;
  workerConfidence: number;
  liveWorkers: number;
  failedRoutes: number;
  evidenceExports: number;
  lastBackendEventAt?: string;
}

export interface SunnyvaleInternalSnapshot {
  mode: SunnyvaleDataMode;
  asOf: string;
  source?: "backend-truth" | "local-fallback";
  bridgeStatus?: {
    enabled: boolean;
    baseUrlConfigured: boolean;
    internalKeyConfigured: boolean;
    lastError?: string;
  };
  overview: SunnyvaleOverview;
  evaluationSignals: OperatingSignal[];
  growthOpportunities: OperatingSignal[];
  fieldIntelligence: OperatingSignal[];
}

export interface EngineSignal {
  id: string;
  title: string;
  strength: number;
  timestamp: string;
  category: string;
}

export interface EngineConvergenceMetric {
  label: string;
  value: string;
  description: string;
  progress: number;
}

export interface HorowitzSignal {
  id: string;
  value: number;
  trend: "up" | "down" | "stable";
  history?: number[];
}

export interface EngineObservability {
  quantum_coherence: number;
  classical_latency: number;
  uacp_pressure: number;
  gopher_policy_alignment: number;
  market_convergence: EngineConvergenceMetric[];
  horowitz_signals: HorowitzSignal[];
}

export type VeklomPillarId =
  | "governance-policy"
  | "sovereignty-infrastructure"
  | "model-tool-governance"
  | "execution-runtime-safety"
  | "evidence-audit-archives"
  | "tenant-experience-integration"
  | "economics-operating-reserve"
  | "compliance-risk-legal"
  | "research-knowledge-learning";

export type CommitteeAuthorityLevel = "advisory" | "operational" | "approval" | "veto" | "constitutional";
export type WorkerArchetype = "arbiter" | "sheriff" | "gauge" | "switchman" | "curator" | "builder" | "scout" | "steward" | "treasurer";
export type SkillBindingState = "proposed" | "reviewing" | "approved" | "pinned" | "quarantined" | "revoked";
export type V3PlanStatus = "draft" | "under_review" | "approved" | "rejected" | "queued" | "executing" | "completed" | "failed" | "archived";
export type V3RunStatus = "pending" | "admission_review" | "approved" | "queued" | "executing" | "paused" | "blocked" | "completed" | "failed" | "cancelled" | "replaying";
export type V3DecisionStatus = "approved" | "blocked" | "needs_founder_review";
export type ReplayMode = "audit_only" | "simulate" | "full_replay";
export type RegistryRouteStage = "Research" | "Product" | "Governance" | "Marketplace/Growth" | "Finance" | "Archive";
export type WorkerRegistryStatus =
  | "ready"
  | "active"
  | "blocked"
  | "paused"
  | "review"
  | "blocked_invalid_registry";
export type WorkerLastRunResult = "success" | "partial_success" | "failure" | "blocked" | "none";
export type V3EventType =
  | "run_submitted"
  | "run_admitted"
  | "run_started"
  | "worker_assigned"
  | "skill_invoked"
  | "policy_checked"
  | "approval_requested"
  | "approval_granted"
  | "approval_rejected"
  | "artifact_created"
  | "archive_written"
  | "run_completed"
  | "run_failed"
  | "run_replayed"
  | "event_correction";

export type V3EventActorType = "system" | "committee" | "worker" | "skill" | "policy_engine" | "archive_service" | "human";

export interface VeklomPillar {
  id: VeklomPillarId;
  name: string;
  purpose: string;
  successMetric: string;
}

export interface SkillBinding {
  id: string;
  name: string;
  state: SkillBindingState;
  governingCommitteeId: string;
  pillarIds: VeklomPillarId[];
  purpose: string;
  pinned: boolean;
  sourceRepo?: string;
  sourceRef?: string;
  sourceTreeSha?: string;
  allowedTools: string[];
}

export interface WorkerRegistryEntry {
  id: string;
  name: string;
  archetype: WorkerArchetype;
  pillarId: VeklomPillarId;
  committeeId: string;
  authorityLevel: CommitteeAuthorityLevel;
  allowedSkillIds: string[];
  forbiddenActions: string[];
  requiredOutput: string;
  reviewer: string;
  archivePath: string;
  requiredEnvKeys: string[];
  status: "ready" | "paused" | "blocked";
  promotionMetric: string;
  demotionTrigger: string;
  currentJob: string;
  lastRunResult?: string;
}

export interface WorkerRegistryRecord {
  worker_id: string;
  worker_name: string;
  pillar_id: string;
  pillar_name: string;
  committee_id: string;
  committee_name: string;
  job: string;
  authority_level: CommitteeAuthorityLevel;
  allowed_skills: string[];
  forbidden_actions: string[];
  keys_envs_required: string[];
  current_status: WorkerRegistryStatus;
  required_output: string;
  reviewer: string;
  promotion_metric: string;
  demotion_trigger: string;
  archive_path: string;
  plan_id: string;
  last_run_id?: string;
  last_run_result?: WorkerLastRunResult;
  last_run_summary?: string;
  last_run_at?: string;
}

export interface WorkerRegistryValidation {
  worker_id: string;
  valid: boolean;
  current_status: WorkerRegistryStatus;
  missing_fields: string[];
  resolved: {
    pillar: boolean;
    committee: boolean;
    plan: boolean;
    archive_path: boolean;
    reviewer: boolean;
    required_output: boolean;
    authority_level: boolean;
  };
}

export interface RoutedIntentStep {
  stage: RegistryRouteStage;
  worker_name: string;
  status: "completed" | "blocked" | "skipped";
  output?: string;
  reviewer?: string;
  archive_path?: string;
  reason?: string;
}

export interface RoutedIntentResult {
  intent: string;
  route: RegistryRouteStage[];
  status: "completed" | "blocked";
  blocked_reason?: string;
  plan_id: string;
  steps: RoutedIntentStep[];
}

export interface PlanRegistryProof {
  plan_id: string;
  valid: boolean;
  worker_records: WorkerRegistryRecord[];
  validations: WorkerRegistryValidation[];
  archive_record_id?: string;
  run_id?: string;
  issues: string[];
}

export interface V3Committee {
  id: string;
  name: string;
  purpose: string;
  pillarIds: VeklomPillarId[];
  authorityLevel: CommitteeAuthorityLevel;
  workerIds: string[];
  allowedActions: string[];
  escalationTarget?: string;
}

export interface V3Plan {
  id: string;
  title: string;
  intent: string;
  status: V3PlanStatus;
  revision: number;
  revisionHash: string;
  frozenAt: string;
  tenantId?: string;
  createdAt: string;
  updatedAt: string;
  pillars: VeklomPillarId[];
  committeeIds: string[];
  workerIds: string[];
  skillIds: string[];
  route: VeklomPillarId[];
  requiredOutputs: string[];
  approvalPath: string[];
  runtimePolicies: string[];
  evidenceCapture: string[];
  archivePath: string;
}

export interface V3Run {
  id: string;
  planId: string;
  planRevision: number;
  planRevisionHash: string;
  status: V3RunStatus;
  decisionStatus?: V3DecisionStatus;
  submittedAt: string;
  startedAt?: string;
  completedAt?: string;
  replayOfRunId?: string;
  workerIds: string[];
  committeeIds: string[];
  skillIds: string[];
  approvalPath: string[];
  runtimePolicies: string[];
  evidenceCapture: string[];
  currentStep?: string;
  artifact?: Record<string, unknown>;
  archiveRecordId?: string;
  integrityStatus?: "ok" | "integrity_failed";
  summary?: string;
  errors: string[];
}

export interface V3Event {
  id: string;
  runId: string;
  planId: string;
  planRevision: number;
  seq: number;
  type: V3EventType;
  at: string;
  actorType: V3EventActorType;
  actorId: string;
  committeeId?: string;
  workerId?: string;
  skillId?: string;
  surface?: SurfaceId;
  pillarIds: VeklomPillarId[];
  message: string;
  payload?: Record<string, unknown>;
  policyRefs?: string[];
  evidenceRefs?: string[];
  prevEventHash?: string;
  eventHash: string;
  hashAlgorithm: "sha256";
  schemaVersion: string;
  replayable: boolean;
}

export interface ArchiveRecord {
  id: string;
  runId: string;
  planId: string;
  planRevision: number;
  archivePath: string;
  type: "plan_snapshot" | "run_bundle" | "replay_bundle" | "commercial_decision";
  summary: string;
  createdAt: string;
  createdBy: string;
  decisionStatus: V3DecisionStatus;
  artifact: Record<string, unknown>;
  eventIds: string[];
  bundleHash: string;
  hashAlgorithm: "sha256";
  signer: string;
  signedAt: string;
  sourceEventRange?: {
    startSeq: number;
    endSeq: number;
  };
  lineage?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
  replayable: boolean;
}

export interface ReplayRequest {
  id: string;
  runId: string;
  requestedBy: string;
  requestedAt: string;
  mode: ReplayMode;
  reason: string;
}

export interface ReplayResult {
  id: string;
  sourceRunId: string;
  replayRunId?: string;
  mode: ReplayMode;
  status: "completed" | "failed";
  summary: string;
  archiveRecordId?: string;
  replayArchiveId?: string;
  sourceUnchanged?: boolean;
  eventChainIntegrity?: {
    chainValid: boolean;
    checkedEventCount: number;
    firstBrokenSeq?: number;
    reason?: string;
  };
  divergenceNotes?: string[];
}

export type CommercialArtifactType =
  | "buyer_facing_offer"
  | "founder_review_claim"
  | "competitor_positioning"
  | "vendor_lead"
  | "tool_package_candidate"
  | "outreach_asset";

export type FounderReviewStatus =
  | "pending_founder_review"
  | "approved"
  | "rejected"
  | "needs_revision";

export interface FounderReviewLane {
  status: FounderReviewStatus;
  reason: string;
  riskNotes: string[];
  approvedCopy?: string;
  rejectedClaims: string[];
  archiveReference?: string;
  reviewedAt?: string;
  reviewedBy?: string;
}

export interface CommercialArtifact {
  id: string;
  type: CommercialArtifactType;
  title: string;
  summary: string;
  sourceCommercialArtifactId?: string;
  sourcePlanId: string;
  sourceRunId: string;
  sourceArchiveRecordId: string;
  replayArchiveRecordId?: string;
  sourceReplayResultId?: string;
  buyerFacing: boolean;
  positioningUse: boolean;
  highRisk: boolean;
  evidenceBacked: boolean;
  copy: {
    headline: string;
    subheadline: string;
    body: string[];
    cta?: string;
  };
  founderReview: FounderReviewLane;
  archiveReference: string;
  createdAt: string;
  updatedAt: string;
}

export interface CommercialScorecard {
  qualifiedEvaluationConversations: number;
  privateBackendAccessRequests: number;
  vendorToolConversations: number;
  approvedPackageConcepts: number;
  founderApprovedCommunityInteractions: number;
  blockedUnsafeClaims: number;
  archiveRecordsWritten: number;
  directReplayChecksCompleted: number;
  replayLinkedArtifacts: number;
  lastUpdatedAt: string;
}
