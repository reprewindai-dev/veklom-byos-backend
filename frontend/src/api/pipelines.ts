/**
 * Pipelines + playground sessions.
 * Sources: backend/apps/api/routers/{pipelines,playground}.py
 */
import { http } from "@/lib/http";

export type Pipeline = {
  id: string;
  name: string;
  description?: string;
  nodes?: number;
  template?: string;
  vector_store?: string;
  status?: "draft" | "deployed" | string;
  invocations?: number;
  last_run?: string;
};

export const pipelinesApi = {
  list: () => http.get<{ items: Pipeline[] }>("/pipelines"),
  get: (id: string) => http.get<Pipeline>(`/pipelines/${encodeURIComponent(id)}`),
  create: (body: Partial<Pipeline>) => http.post<Pipeline>("/pipelines", body),
  update: (id: string, body: Partial<Pipeline>) =>
    http.patch<Pipeline>(`/pipelines/${encodeURIComponent(id)}`, body),
  remove: (id: string) => http.delete<void>(`/pipelines/${encodeURIComponent(id)}`),
  run: (id: string, body: Record<string, unknown> = {}) =>
    http.post<{ run_id: string }>(`/pipelines/${encodeURIComponent(id)}/run`, body),
  interactiveSession: () => http.get<{ session_id: string; ws_url?: string }>("/pipeline/interactive/session"),
  demoRun: (body: Record<string, unknown> = {}) =>
    http.post<{ trace: unknown }>("/demo/pipeline/run", body),
};
