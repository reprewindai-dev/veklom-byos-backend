// Workspace API client — maps to backend/apps/api/routers/workspace.py
import { http } from '../lib/http';

export interface SpendBreakdownItem {
  label: string;
  amount_usd: number;
  percent: number;
}

export interface RecentRun {
  model?: string;
  route?: string;
  latency_ms?: number;
  tokens?: number;
  cost_usd?: number;
  policy?: string;
  when?: string;
  [k: string]: unknown;
}

export interface FleetModel {
  id: string;
  name: string;
  quant?: string;
  replicas?: number;
  route?: string;
  p50?: number;
}

export interface RoutingHistoryPoint {
  hour: string;
  hetzner: number;
  aws: number;
  [k: string]: string | number;
}

export interface OverviewRouting {
  hetzner_percent: number;
  aws_percent: number;
  primary_region: string;
  burst_region: string;
  history: RoutingHistoryPoint[];
  regions: { label: string; value: string; sub: string; route: string }[];
}

// Shape returned by GET /workspace/overview and /workspace/overview/live
export interface OverviewPayload {
  workspace_id: string;
  plan: string;
  members_count: number;
  models_enabled: number;
  total_requests_today: number;
  requests_per_min: number;
  p50_latency_ms: number;
  tokens_per_sec: number;
  spend_today_usd: number;
  spend_cap_usd: number;
  spend_percent: number;
  spend_status: string;
  burn_rate_usd_per_min: number;
  forecast_eod_usd: number;
  spend_breakdown: SpendBreakdownItem[];
  budget_remaining_usd: number;
  active_pipelines: number;
  active_deployments: number;
  active_models: number;
  audit_entries: number;
  recent_runs: RecentRun[];
  policy_events: Record<string, unknown>[];
  alerts: Record<string, unknown>[];
  audit_logs: Record<string, unknown>[];
  fleet: FleetModel[];
  routing: OverviewRouting;
  updated_at: string;
}

export interface WorkspaceModel {
  id: string;
  display_name: string;
  provider: string;
  model_name: string;
  cost_per_1k_input: number;
  is_enabled: boolean;
  [k: string]: unknown;
}

export interface WorkspaceApiKey {
  id: string;
  name: string;
  key_prefix: string;
  is_active: boolean;
  key?: string;
  [k: string]: unknown;
}

export interface WorkspaceMember {
  id?: string;
  email: string;
  role: string;
  mfa_enabled?: boolean;
  last_active?: string;
  [k: string]: unknown;
}

export const workspaceApi = {
  overview: () => http.get<OverviewPayload>('/workspace/overview'),
  overviewLive: () => http.get<OverviewPayload>('/workspace/overview/live'),
  get: () => http.get('/workspace'),
  observability: () => http.get('/workspace/observability'),

  models: (provider?: string) =>
    http.get<WorkspaceModel[]>('/workspace/models', provider ? { provider } : undefined),
  setModelEnabled: (id: string, is_enabled: boolean) =>
    http.patch<WorkspaceModel>(`/workspace/models/${id}`, { is_enabled }),

  settings: () => http.get('/workspace/settings'),
  updateSettings: (body: Record<string, unknown>) => http.patch('/workspace/settings', body),

  routing: () => http.get('/workspace/routing'),
  updateRouting: (body: Record<string, unknown>) => http.patch('/workspace/routing', body),

  apiKeys: () => http.get<WorkspaceApiKey[]>('/workspace/api-keys'),
  createApiKey: (name: string) => http.post<WorkspaceApiKey>('/workspace/api-keys', { name }),
  deleteApiKey: (id: string) => http.del(`/workspace/api-keys/${id}`),

  members: () => http.get<WorkspaceMember[]>('/workspace/members'),

  auditLogs: (limit = 20, offset = 0) => http.get('/workspace/audit/logs', { limit, offset }),
  billingBreakdown: () => http.get('/workspace/billing/breakdown'),
  securityAlerts: (limit = 10) => http.get('/workspace/security/alerts', { limit }),
  search: (q: string) => http.get('/workspace/search', { q }),
};
