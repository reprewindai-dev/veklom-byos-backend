/**
 * Agent workforce + HRM tiers.
 * Sources: backend/apps/api/routers/{agents,hrm,copilot,repo_risk_gate}.py
 */
import { http } from "@/lib/http";

export type AgentRecord = {
  id?: string;
  agent_number?: number;
  name?: string;
  tier?: string;
  squad_id?: string;
  capabilities?: string[];
  status?: string;
};

export type AgentRun = {
  id: string;
  agent_number?: number;
  status: string;
  started_at?: string;
  finished_at?: string;
};

export const agentsApi = {
  law: () => http.get<{ articles: { id: string; title: string; body: string }[] }>("/agents/law"),
  registry: () => http.get<{ items: AgentRecord[] }>("/agents/registry"),
  list: () => http.get<{ items: AgentRecord[] }>("/agents/"),
  get: (n: string | number) => http.get<AgentRecord>(`/agents/registry/${n}`),
  fleet: () => http.get<{ active: number; idle: number; failed: number }>("/agents/fleet"),
  runs: () => http.get<{ items: AgentRun[] }>("/agents/runs"),
  startRun: (body: { agent_number: number; input?: Record<string, unknown> }) =>
    http.post<AgentRun>("/agents/runs", body),
  completeRun: (id: string, body: Record<string, unknown> = {}) =>
    http.patch<AgentRun>(`/agents/runs/${encodeURIComponent(id)}/complete`, body),
  decisionFrames: () => http.get<{ items: unknown[] }>("/agents/decision-frames"),
  signals: () => http.get<{ items: unknown[] }>("/agents/signals"),
  violations: () => http.get<{ items: unknown[] }>("/agents/violations"),
  evidence: () => http.get<{ items: unknown[] }>("/agents/evidence"),
  monthlyReport: () => http.get<unknown>("/agents/monthly-report"),
  guardrails: () => http.get<{ items: { id: string; rule: string; severity: string }[] }>("/agents/guardrails"),
  skills: () => http.get<{ items: { id: string; name: string; description?: string }[] }>("/agents/skills"),
  skill: (id: string) => http.get<unknown>(`/agents/skills/${encodeURIComponent(id)}`),
  invokeSkill: (id: string, body: Record<string, unknown> = {}) =>
    http.post<{ run_id: string }>(`/agents/skills/${encodeURIComponent(id)}/invoke`, body),

  hrm: {
    audit: () => http.get<{ items: unknown[] }>("/agents/hrm/audit"),
    agent: (n: string | number) => http.get<AgentRecord>(`/agents/hrm/agents/${n}`),
    monitors: () => http.get<{ items: unknown[] }>("/agents/hrm/monitors"),
    telemetry: () => http.get<unknown>("/agents/hrm/sync/telemetry"),
    zeno: (agent_id: string) =>
      http.post<{ result: unknown }>(`/agents/hrm/${encodeURIComponent(agent_id)}/zeno-interrogation`),
    register: (body: Record<string, unknown>) =>
      http.post<AgentRecord>("/agents/hrm/register", body),
    setStatus: (agent_id: string, body: { status: string }) =>
      http.patch<AgentRecord>(`/agents/hrm/${encodeURIComponent(agent_id)}/status`, body),
  },
};

export const copilotApi = {
  registry: () => http.get<{ items: { id: string; name: string }[] }>("/copilot/registry"),
  recentDecisions: () => http.get<{ items: unknown[] }>("/copilot/recent-decisions"),
  copilot: (id: string) => http.get<unknown>(`/copilot/registry/${encodeURIComponent(id)}`),
  suggestions: (body: { context?: string; intent?: string }) =>
    http.post<{ items: { id: string; title: string; rationale?: string }[] }>(
      "/copilot/suggestions",
      body,
    ),
  moneySavingTips: () =>
    http.get<{ items: { id: string; title: string; impact_usd?: number }[] }>(
      "/copilot/money-saving-tips",
    ),
};

export type RiskGateRun = {
  id: string;
  repo: string;
  ref?: string;
  status: "queued" | "scanning" | "passed" | "blocked" | "failed" | string;
  created_at: string;
};

export const repoRiskGateApi = {
  startRun: (body: { repo: string; ref?: string }) =>
    http.post<RiskGateRun>("/repo-risk-gate/runs", body),
  runs: () => http.get<{ items: RiskGateRun[] }>("/repo-risk-gate/runs"),
  run: (id: string) => http.get<RiskGateRun>(`/repo-risk-gate/runs/${encodeURIComponent(id)}`),
  events: (id: string) =>
    http.get<{ items: { id: string; type: string; message: string; created_at: string }[] }>(
      `/repo-risk-gate/runs/${encodeURIComponent(id)}/events`,
    ),
  decision: (id: string, body: { decision: "allow" | "block"; note?: string }) =>
    http.post<RiskGateRun>(`/repo-risk-gate/runs/${encodeURIComponent(id)}/decision`, body),
  ledger: (id: string) => http.get<unknown>(`/repo-risk-gate/runs/${encodeURIComponent(id)}/ledger`),
};
