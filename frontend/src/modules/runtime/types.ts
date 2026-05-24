export interface Agent {
  id: string;
  name: string;
  scope: string;
  description: string;
  trustScore: number;
  icon: string;
  dataset: string;
}

export interface Policy {
  id: string;
  citizenEmail: string;
  agentId: string;
  action: string;
  status: "granted" | "revoked";
  validUntil: string;
}

export interface GateResult {
  passed: boolean;
  details: string;
  costUsd?: number;
  blockHash?: string;
}

export interface GatesResult {
  gate1_signature: GateResult;
  gate2_consent: GateResult;
  gate3_boundary: GateResult;
  gate4_quota: GateResult;
  gate5_ledger: GateResult;
}

export interface LedgerBlock {
  index: number;
  timestamp: string;
  citizenEmail: string;
  agentId: string;
  query: string;
  signature: string;
  gatesResult: GatesResult;
  response: string;
  previousHash: string;
  hash: string;
}

export interface ExecutionReport {
  success: boolean;
  block: LedgerBlock;
}

// ==========================================
// VEKLOM SOVEREIGN AI HUB SPECIFIC SCHEMAS
// ==========================================

export interface HealthStatus {
  status: string;
  version: string;
  timestamp: string;
  uptimeSeconds: number;
  environment: string;
  database: "connected" | "disconnected" | "simulated";
  redis: "connected" | "simulated";
  sovereignNodes: {
    active: number;
    quarantined: number;
    avgLatencyMs: number;
  };
}

export interface UserMe {
  email: string;
  name: string;
  role: string;
  mfaEnabled: boolean;
  mfaVerified: boolean;
  connectedAccounts: string[];
  registeredAt: string;
}

export interface ApiKey {
  id: string;
  name: string;
  prefix: string;
  scope: string;
  createdAt: string;
  expiresAt: string;
  lastUsedAt: string | null;
}

export interface WorkspaceOverview {
  workspaceId: string;
  name: string;
  owner: string;
  created_at: string;
  modelsCount: number;
  tokensMonth: number;
  avgLatencyMs: number;
  killSwitchStatus: boolean;
  observabilitySignals: {
    cpuPercent: number;
    memoryMb: number;
    concurrencyGauge: number;
  };
}

export interface WorkspaceModel {
  id: string;
  name: string;
  provider: string;
  version: string;
  type: string;
  contextLength: number;
  active: boolean;
  costPer1kInput: number;
  costPer1kOutput: number;
}

export interface WorkspaceMember {
  id: string;
  email: string;
  role: "admin" | "operator" | "viewer";
  status: "active" | "invited";
  joinedAt: string;
}

export interface BudgetRule {
  id: string;
  name: string;
  limitUsd: number;
  spentUsd: number;
  interval: "daily" | "weekly" | "monthly";
  action: "alert" | "block_all";
}

export interface SecurityEvent {
  id: string;
  timestamp: string;
  severity: "info" | "warning" | "critical";
  category: "authentication" | "boundary_breach" | "pii_leak" | "rate_limit" | "firewall";
  message: string;
  metadata: Record<string, string>;
  blocked: boolean;
}

export interface ThreatStats {
  totalScanned: number;
  blockedIncidents: number;
  piiMaskedCount: number;
  sandboxViolationsResolved: number;
}

export interface Pipeline {
  id: string;
  name: string;
  status: "active" | "draft" | "running" | "failed" | "completed";
  trigger: "manual" | "cron" | "event";
  canaryTarget: number;
  canaryPromoted: boolean;
  createdAt: string;
  lastRunAt: string | null;
}

export interface RoutingRule {
  id: string;
  path: string;
  modelId: string;
  fallbackModelId: string;
  policy: "cost_optimized" | "latency_optimized" | "integrity_max";
}

export interface GpcPlan {
  id: string;
  name: string;
  status: "draft" | "active" | "archived";
  maxRuns: number;
  created_at: string;
}

export interface GpcRun {
  id: string;
  planId: string;
  status: "idle" | "running" | "completed" | "failed";
  progressPercentage: number;
  tokensConsumed: number;
  eventSummary: string;
  timestamp: string;
}

export interface ByosConfig {
  byosBackendUrl: string;
  byosConnected: boolean;
  byosHandshakeDetails: any;
  usingByos: boolean;
  cacheStats?: {
    hits: number;
    misses: number;
    latencySavedMs: number;
    estimatedComputeSavedPennies: number;
    currentCacheSize: number;
  };
}

