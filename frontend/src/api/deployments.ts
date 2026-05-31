/**
 * Deployments + edge canary.
 * Sources: backend/apps/api/routers/{deployments,edge_canary}.py
 */
import { http } from "@/lib/http";

export type Deployment = {
  id: string;
  name: string;
  type: "chat" | "completion" | "embedding" | "pipeline" | "batch" | string;
  endpoint?: string;
  auth?: "api-key" | "jwt" | "ip-allowlist" | string;
  model?: string;
  region?: string;
  rate_limit?: string;
  status: "live" | "draft" | "paused" | string;
  rps?: number;
  error_rate?: number;
};

export const deploymentsApi = {
  list: () => http.get<{ items: Deployment[] }>("/deployments"),
  create: (body: Partial<Deployment>) => http.post<Deployment>("/deployments", body),
  update: (id: string, body: Partial<Deployment>) =>
    http.patch<Deployment>(`/deployments/${encodeURIComponent(id)}`, body),
  remove: (id: string) => http.delete<void>(`/deployments/${encodeURIComponent(id)}`),
  edge: {
    canaryStatus: () => http.get<{ ready: boolean; pct: number }>("/edge/canary/status"),
    canaryPromote: () => http.post<{ promoted: boolean }>("/edge/canary/promote"),
  },
};
