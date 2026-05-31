/**
 * Command Center — super-user operations dashboard + terminals.
 * Source: backend/apps/api/routers/command_center.py (prefix /command-center)
 */
import { http } from "@/lib/http";

export type TerminalEndpoint = {
  label: string;
  method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  path: string;
  body?: Record<string, unknown>;
};
export type TerminalDescriptor = {
  name: string;
  version: string;
  auth_required: boolean;
  endpoints: TerminalEndpoint[];
};

export type CCOverview = {
  workspace_count?: number;
  active_users?: number;
  errors_24h?: number;
  spend_today_usd?: number;
  health?: string;
  [k: string]: unknown;
};

export type CCUserSummary = {
  id: string;
  email: string;
  workspace_id?: string;
  role?: string;
  last_active?: string;
  online?: boolean;
};

export type CCActivityEvent = {
  id: string;
  type: string;
  actor?: string;
  target?: string;
  message: string;
  created_at: string;
};

export type CCAlert = {
  id: string;
  severity: "info" | "warn" | "critical" | string;
  title: string;
  source?: string;
  created_at: string;
};

export const commandCenterApi = {
  overview: () => http.get<CCOverview>("/command-center/overview"),
  auditLog: (q: { limit?: number } = {}) =>
    http.get<{ items: unknown[] }>("/command-center/audit-log", { query: q }),
  users: () => http.get<{ items: CCUserSummary[] }>("/command-center/users"),
  user: (id: string) => http.get<CCUserSummary>(`/command-center/users/${encodeURIComponent(id)}`),
  userActivity: (id: string) =>
    http.get<{ items: CCActivityEvent[] }>(
      `/command-center/users/${encodeURIComponent(id)}/activity`,
    ),
  userSessions: (id: string) =>
    http.get<{ items: { id: string; created_at: string; ip?: string }[] }>(
      `/command-center/users/${encodeURIComponent(id)}/sessions`,
    ),
  operations: {
    health: () => http.get<{ status: string; checks: Record<string, unknown> }>("/command-center/operations/health"),
    alerts: () => http.get<{ items: CCAlert[] }>("/command-center/operations/alerts"),
    errors: () => http.get<{ items: { id: string; message: string; created_at: string; level: string }[] }>(
      "/command-center/operations/errors",
    ),
  },
  business: {
    billing: () => http.get<{
      mrr_usd?: number;
      arr_usd?: number;
      open_invoices?: number;
      collected_30d_usd?: number;
    }>("/command-center/business/billing"),
  },
  activityFeed: (q: { limit?: number } = {}) =>
    http.get<{ items: CCActivityEvent[] }>("/command-center/activity-feed", { query: q }),
  usersSummary: () =>
    http.get<{ total: number; active: number; new_24h: number }>("/command-center/users/summary"),
  usersOnline: () => http.get<{ items: CCUserSummary[] }>("/command-center/users/online"),
  usersRecent: () => http.get<{ items: CCUserSummary[] }>("/command-center/users/recent"),
  liveUsers: () => http.get<{ items: CCUserSummary[] }>("/command-center/live-users"),
  sessions: () =>
    http.get<{ items: { id: string; user_id: string; created_at: string; ip?: string }[] }>(
      "/command-center/sessions",
    ),
  funnels: () => http.get<{ stages: { name: string; count: number }[] }>("/command-center/funnels"),

  terminals: {
    quantum: () => http.get<TerminalDescriptor>("/command-center/terminals/quantum"),
    veklom: () => http.get<TerminalDescriptor>("/command-center/terminals/veklom"),
  },
};
