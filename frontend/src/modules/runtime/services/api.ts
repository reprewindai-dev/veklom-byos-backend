import { 
  Agent, 
  Policy, 
  LedgerBlock, 
  HealthStatus, 
  UserMe, 
  ApiKey, 
  WorkspaceOverview, 
  WorkspaceModel, 
  WorkspaceMember, 
  BudgetRule, 
  SecurityEvent, 
  ThreatStats, 
  Pipeline, 
  RoutingRule, 
  GpcPlan, 
  GpcRun,
  ByosConfig
} from "../types";

// ==========================================
// VEKLOM SOVEREIGN HUB API SERVICE INTERFACE
// ==========================================

export const api = {
  // --- HEALTH & GENERAL STATUS ---
  getHealth: async (): Promise<{ status: string; service: string; version: string }> => {
    const res = await fetch("/health");
    return res.json();
  },

  getHealthDetailed: async (): Promise<HealthStatus> => {
    const res = await fetch("/health/detailed");
    return res.json();
  },

  getStatus: async (): Promise<{ platform: string; firewall: string; emergencyKillSwitch: string; blockchainHeight: number; activeSensors: number }> => {
    const res = await fetch("/status");
    return res.json();
  },

  // --- AUTHENTICATION & IDENTITY ---
  register: async (email: string, name: string): Promise<{ success: boolean; user: UserMe }> => {
    const res = await fetch("/api/v1/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, name })
    });
    return res.json();
  },

  login: async (email: string): Promise<{ success: boolean; token: string; user: UserMe }> => {
    const res = await fetch("/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email })
    });
    return res.json();
  },

  logout: async (): Promise<{ success: boolean; message: string }> => {
    const res = await fetch("/api/v1/auth/logout", { method: "POST" });
    return res.json();
  },

  getMe: async (): Promise<UserMe> => {
    const res = await fetch("/api/v1/auth/me");
    return res.json();
  },

  updateMe: async (data: { name?: string; mfaEnabled?: boolean }): Promise<UserMe> => {
    const res = await fetch("/api/v1/auth/me", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    });
    return res.json();
  },

  setupMfa: async (): Promise<{ secret: string; qrCodeMock: string; backupCodes: string[] }> => {
    const res = await fetch("/api/v1/auth/mfa/setup", { method: "POST" });
    return res.json();
  },

  verifyMfa: async (code: string): Promise<{ success: boolean; message: string }> => {
    const res = await fetch("/api/v1/auth/mfa/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code })
    });
    return res.json();
  },

  disableMfa: async (): Promise<{ success: boolean; message: string }> => {
    const res = await fetch("/api/v1/auth/mfa/disable", { method: "POST" });
    return res.json();
  },

  getApiKeys: async (): Promise<ApiKey[]> => {
    const res = await fetch("/api/v1/auth/api-keys");
    return res.json();
  },

  createApiKey: async (name: string, scope: string): Promise<ApiKey> => {
    const res = await fetch("/api/v1/auth/api-keys", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, scope })
    });
    return res.json();
  },

  revokeApiKey: async (id: string): Promise<{ success: boolean; message: string }> => {
    const res = await fetch(`/api/v1/auth/api-keys/${id}`, { method: "DELETE" });
    return res.json();
  },

  getConnectedAccounts: async (): Promise<string[]> => {
    const res = await fetch("/api/v1/auth/connected-accounts");
    return res.json();
  },

  revokeAllSessions: async (): Promise<{ success: boolean; message: string }> => {
    const res = await fetch("/api/v1/auth/sessions/revoke", { method: "DELETE" });
    return res.json();
  },

  // --- WORKSPACE ---
  getWorkspace: async (): Promise<WorkspaceOverview> => {
    const res = await fetch("/api/v1/workspace");
    return res.json();
  },

  getWorkspaceOverview: async (): Promise<{ workspace: WorkspaceOverview; nodesConnected: number; threatsScannedToday: number; budgetUtilizationPercent: number }> => {
    const res = await fetch("/api/v1/workspace/overview");
    return res.json();
  },

  getLivePulse: async (): Promise<{ timestamp: string; signals: { cpuPercent: number; memoryMb: number; concurrencyGauge: number }; runningPipelines: number }> => {
    const res = await fetch("/api/v1/workspace/overview/live");
    return res.json();
  },

  updateWorkspaceName: async (name: string): Promise<WorkspaceOverview> => {
    const res = await fetch("/api/v1/workspace/settings", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name })
    });
    return res.json();
  },

  getWorkspaceModels: async (): Promise<WorkspaceModel[]> => {
    const res = await fetch("/api/v1/workspace/models");
    return res.json();
  },

  toggleWorkspaceModel: async (modelId: string): Promise<WorkspaceModel[]> => {
    const res = await fetch(`/api/v1/workspace/models/${modelId}`, { method: "PATCH" });
    return res.json();
  },

  getWorkspaceApiKeys: async (): Promise<{ id: string; name: string; prefix: string; scope: string; createdAt: string }[]> => {
    const res = await fetch("/api/v1/workspace/api-keys");
    return res.json();
  },

  createWorkspaceApiKey: async (name: string): Promise<{ id: string; name: string; prefix: string; scope: string; createdAt: string }> => {
    const res = await fetch("/api/v1/workspace/api-keys", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name })
    });
    return res.json();
  },

  deleteWorkspaceApiKey: async (id: string): Promise<{ success: boolean }> => {
    const res = await fetch(`/api/v1/workspace/api-keys/${id}`, { method: "DELETE" });
    return res.json();
  },

  getMembers: async (): Promise<WorkspaceMember[]> => {
    const res = await fetch("/api/v1/workspace/members");
    return res.json();
  },

  inviteMember: async (email: string, role: string): Promise<WorkspaceMember> => {
    const res = await fetch("/api/v1/workspace/members/invite", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, role })
    });
    return res.json();
  },

  getBudgetCostSummary: async (): Promise<{ totalLimitUsd: number; totalSpentUsd: number; categories: Record<string, number> }> => {
    const res = await fetch("/api/v1/workspace/cost-budget");
    return res.json();
  },

  getWorkspaceBudget: async (): Promise<BudgetRule[]> => {
    const res = await fetch("/api/v1/workspace/budget");
    return res.json();
  },

  // --- SOVEREIGN CODES & COMPREHENSIVE AI ---
  getUacpAgents: async (): Promise<Agent[]> => {
    const res = await fetch("/api/uacp/agents");
    return res.json();
  },

  getUacpPolicies: async (): Promise<Policy[]> => {
    const res = await fetch("/api/uacp/policies");
    return res.json();
  },

  saveUacpPolicy: async (policyData: Partial<Policy>): Promise<{ success: boolean; policy: Policy }> => {
    const res = await fetch("/api/uacp/policies", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(policyData)
    });
    return res.json();
  },

  getUacpLedger: async (): Promise<LedgerBlock[]> => {
    const res = await fetch("/api/uacp/ledger");
    return res.json();
  },

  clearUacpLedger: async (): Promise<{ success: boolean; message: string }> => {
    const res = await fetch("/api/uacp/clear-ledger", { method: "POST" });
    return res.json();
  },

  executeUacpQuery: async (citizenEmail: string, agentId: string, query: string, useMemori?: boolean): Promise<{ success: boolean; block: LedgerBlock; memoriMetrics?: any }> => {
    const res = await fetch("/api/uacp/execute", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ citizenEmail, agentId, query, useMemori })
    });
    return res.json();
  },

  aiComplete: async (prompt: string, modelId: string, citizenEmail: string): Promise<{ success: boolean; block: LedgerBlock }> => {
    const res = await fetch("/api/v1/ai/complete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, modelId, citizenEmail })
    });
    return res.json();
  },

  predictCost: async (prompt: string, modelId: string): Promise<{ promptTokens: number; completionTokens: number; estimatedCostUsd: number }> => {
    const res = await fetch("/api/v1/ai/predict-cost", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, modelId })
    });
    return res.json();
  },

  // --- BILLING WALLET ---
  getWalletBalance: async (): Promise<{ balanceUsd: number }> => {
    const res = await fetch("/api/v1/wallet/balance");
    return res.json();
  },

  getWalletTransactions: async (): Promise<{ id: string; type: string; amountUsd: number; timestamp: string; label: string }[]> => {
    const res = await fetch("/api/v1/wallet/transactions");
    return res.json();
  },

  topupCheckoutSimulate: async (amount: number): Promise<{ checkoutUrl: string; newBalance: number }> => {
    const res = await fetch("/api/v1/wallet/topup/checkout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ amount })
    });
    return res.json();
  },

  getCostHistory: async (): Promise<{ month: string; compute: number; security: number }[]> => {
    const res = await fetch("/api/v1/cost/history");
    return res.json();
  },

  // --- SECURITY CONTROL CENTER ---
  getSecurityDashboard: async (): Promise<{ events: SecurityEvent[]; threatStats: ThreatStats; sandboxControlsActive: boolean; firewallRulesCount: number }> => {
    const res = await fetch("/api/v1/security/dashboard");
    return res.json();
  },

  getKillSwitchStatus: async (): Promise<{ active: boolean }> => {
    const res = await fetch("/api/v1/kill-switch/status");
    return res.json();
  },

  activateKillSwitch: async (): Promise<{ success: boolean; active: boolean; message: string }> => {
    const res = await fetch("/api/v1/kill-switch/activate", { method: "POST" });
    return res.json();
  },

  deactivateKillSwitch: async (): Promise<{ success: boolean; active: boolean; message: string }> => {
    const res = await fetch("/api/v1/kill-switch/deactivate", { method: "POST" });
    return res.json();
  },

  // --- COMPLIANCE & SHIELD ---
  getRegulations: async (): Promise<{ id: string; name: string; status: string; score: number }[]> => {
    const res = await fetch("/api/v1/compliance/regulations");
    return res.json();
  },

  runComplianceCheck: async (): Promise<{ timestamp: string; violationsCount: number; complianceLevel: string; details: string }> => {
    const res = await fetch("/api/v1/compliance/check", { method: "POST" });
    return res.json();
  },

  maskPii: async (text: string): Promise<{ maskedText: string }> => {
    const res = await fetch("/api/v1/privacy/mask-pii", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text })
    });
    return res.json();
  },

  detectPii: async (text: string): Promise<{ piiDetected: boolean; matches: { type: string; value: string }[] }> => {
    const res = await fetch("/api/v1/privacy/detect-pii", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text })
    });
    return res.json();
  },

  getAuditLogs: async (): Promise<LedgerBlock[]> => {
    const res = await fetch("/api/v1/audit/logs");
    return res.json();
  },

  verifyAuditLog: async (id: number): Promise<{ success: boolean; Verified: boolean; blockIndex: string; validatedAt: string }> => {
    const res = await fetch(`/api/v1/audit/verify/${id}`);
    return res.json();
  },

  getComplianceReportSummary: async (): Promise<{ generalComplianceScore: number; gdpr: string; auditLogCryptographicProof: string; v6SignaturesCheckPassed: boolean }> => {
    const res = await fetch("/api/v1/audit/compliance-report");
    return res.json();
  },

  // --- PIPELINES & EDGE CANARY ---
  getPipelines: async (): Promise<Pipeline[]> => {
    const res = await fetch("/api/v1/pipelines");
    return res.json();
  },

  createPipeline: async (name: string, trigger: string): Promise<Pipeline> => {
    const res = await fetch("/api/v1/pipelines", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, trigger })
    });
    return res.json();
  },

  triggerPipelineRun: async (id: string): Promise<{ success: boolean; pipeline: Pipeline }> => {
    const res = await fetch(`/api/v1/pipelines/${id}/run`, { method: "POST" });
    return res.json();
  },

  promoteCanary: async (pipelineId: string): Promise<{ success: boolean }> => {
    const res = await fetch("/api/v1/edge/canary/promote", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pipelineId })
    });
    return res.json();
  },

  getRoutingRules: async (): Promise<RoutingRule[]> => {
    const res = await fetch("/api/v1/routing");
    return res.json();
  },

  createRoutingRule: async (rule: Partial<RoutingRule>): Promise<RoutingRule> => {
    const res = await fetch("/api/v1/routing", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(rule)
    });
    return res.json();
  },

  // --- GPC CONTROLLER ---
  getGpcPlans: async (): Promise<GpcPlan[]> => {
    const res = await fetch("/api/v1/gpc/plans");
    return res.json();
  },

  createGpcPlan: async (name: string, maxRuns: number): Promise<GpcPlan> => {
    const res = await fetch("/api/v1/gpc/plans", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, maxRuns })
    });
    return res.json();
  },

  getGpcRuns: async (): Promise<GpcRun[]> => {
    const res = await fetch("/api/v1/gpc/runs");
    return res.json();
  },

  startGpcRun: async (planId: string): Promise<GpcRun> => {
    const res = await fetch("/api/v1/gpc/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ planId })
    });
    return res.json();
  },

  // --- BYOS BACKEND ALIGNMENT HANDSHAKE ---
  getByosConfig: async (): Promise<ByosConfig> => {
    const res = await fetch("/api/v1/byos/config");
    return res.json();
  },

  performByosHandshake: async (url: string, apiToken?: string): Promise<{ success: boolean; config: ByosConfig; message?: string; error?: string }> => {
    const res = await fetch("/api/v1/byos/handshake", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, apiToken })
    });
    return res.json();
  },

  disconnectByos: async (): Promise<{ success: boolean }> => {
    const res = await fetch("/api/v1/byos/disconnect", { method: "POST" });
    return res.json();
  },

  // --- MEMORI PERSISTENT MEMORY CONTEXT ---
  getMemoriStats: async (): Promise<{ totalQueriesOptimized: number; accumulatedTokensOriginal: number; accumulatedTokensOptimized: number; savedTokensTotal: number; savedPenniesTotal: number }> => {
    const res = await fetch("/api/v1/memori/stats");
    return res.json();
  },

  getMemoriDb: async (): Promise<{ triples: any[]; summaries: any[] }> => {
    const res = await fetch("/api/v1/memori/db");
    return res.json();
  },

  addMemoriTriple: async (triple: { subject: string; predicate: string; object: string; conversationId?: string }): Promise<any> => {
    const res = await fetch("/api/v1/memori/triples", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(triple)
    });
    return res.json();
  },

  deleteMemoriTriple: async (id: string): Promise<any> => {
    const res = await fetch(`/api/v1/memori/triples/${id}`, {
      method: "DELETE"
    });
    return res.json();
  },

  resetMemori: async (): Promise<any> => {
    const res = await fetch("/api/v1/memori/reset", {
      method: "POST"
    });
    return res.json();
  }
};
