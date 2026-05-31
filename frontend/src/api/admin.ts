/**
 * Admin + internal (UACP, operators, source-of-truth).
 * Sources: backend/apps/api/routers/{admin,internal_uacp,internal_operators}.py
 */
import { http } from "@/lib/http";

export const adminApi = {
  users: () => http.get<{ items: { id: string; email: string; workspace_id: string }[] }>("/admin/users"),
  updateUser: (id: string, body: Record<string, unknown>) =>
    http.patch<unknown>(`/admin/users/${encodeURIComponent(id)}`, body),
  deleteUser: (id: string) => http.delete<void>(`/admin/users/${encodeURIComponent(id)}`),
  workspaces: () => http.get<{ items: { id: string; name?: string; slug?: string }[] }>("/admin/workspaces"),
  uacp: {
    status: () => http.get<{ ready: boolean; operators: number }>("/internal/uacp/status"),
    command: (body: { command: string; args?: unknown }) =>
      http.post<{ accepted: boolean }>("/internal/uacp/command", body),
  },
  operators: {
    list: () => http.get<{ items: { id: string; name: string; tier: string }[] }>("/internal/operators"),
    register: (body: { name: string; tier?: string }) =>
      http.post<{ id: string }>("/internal/operators", body),
  },
  sourceOfTruth: {
    snapshot: () => http.get<unknown>("/source-of-truth/snapshot"),
    sync: () => http.post<{ ok: boolean }>("/source-of-truth/sync"),
  },
};
