/**
 * GPC — Governed Process Control plane.
 * Source: backend/apps/api/routers/gpc.py (prefix /gpc)
 * Companion: backend/apps/api/routers/decision_frames.py (prefix /decision-frames)
 */
import { http } from "@/lib/http";

export type GpcPlan = {
  id: string;
  name?: string;
  intent?: string;
  steps?: { id: string; label: string }[];
  status?: string;
  created_at?: string;
};

export type GpcRun = {
  id: string;
  plan_id?: string;
  status: "queued" | "running" | "succeeded" | "failed" | "halted" | string;
  started_at?: string;
  finished_at?: string;
  decision_frame_id?: string;
};

export type GpcEvent = {
  id: string;
  type: string;
  run_id?: string;
  message: string;
  severity?: string;
  created_at: string;
};

export type GpcBootstrap = {
  ready: boolean;
  endpoints?: string[];
  controls?: string[];
};

export type DecisionFrame = {
  id: string;
  plan_id?: string;
  status: "pending" | "approved" | "rejected" | string;
  rationale?: string;
  approver?: string;
  created_at: string;
};

export const gpcApi = {
  bootstrap: () => http.get<GpcBootstrap>("/gpc/bootstrap"),
  plans: () => http.get<{ items: GpcPlan[] }>("/gpc/plans"),
  createPlan: (body: { intent: string; meta?: Record<string, unknown> }) =>
    http.post<GpcPlan>("/gpc/plans", body),
  compile: (body: { plan_id?: string; intent?: string }) =>
    http.post<{ compiled: unknown; tokens?: number }>("/gpc/compile", body),
  intentToPlan: (body: { intent: string }) =>
    http.post<{ compiled: unknown; plan?: GpcPlan }>("/gpc/intent-to-plan", body),
  runs: (q: { limit?: number } = {}) =>
    http.get<{ items: GpcRun[] }>("/gpc/runs", { query: q }),
  createRun: (body: { plan_id: string; input?: Record<string, unknown> }) =>
    http.post<GpcRun>("/gpc/runs", body),
  events: (q: { run_id?: string; limit?: number } = {}) =>
    http.get<{ items: GpcEvent[] }>("/gpc/events", { query: q }),
  ssrnSignals: () => http.get<{ items: unknown[] }>("/gpc/ssrn-signals"),
  observability: () => http.get<{ items: unknown[] }>("/gpc/observability/signals"),
  stats: () =>
    http.get<{ plans: number; runs: number; pending_frames: number; success_rate?: number }>(
      "/gpc/stats",
    ),

  decisionFrames: {
    list: (q: { limit?: number; status?: string } = {}) =>
      http.get<{ items: DecisionFrame[] }>("/decision-frames", { query: q }),
    stats: () =>
      http.get<{ pending: number; approved: number; rejected: number }>("/decision-frames/stats"),
    get: (id: string) => http.get<DecisionFrame>(`/decision-frames/${encodeURIComponent(id)}`),
    approve: (id: string, body: { note?: string } = {}) =>
      http.post<DecisionFrame>(`/decision-frames/${encodeURIComponent(id)}/approve`, body),
    replay: (id: string) =>
      http.get<{ trace: unknown[] }>(`/decision-frames/${encodeURIComponent(id)}/replay`),
  },
};
