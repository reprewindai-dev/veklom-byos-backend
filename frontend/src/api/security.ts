/**
 * Security, kill switch, locker.
 * Sources: backend/apps/api/routers/security.py + locker_*
 */
import { http } from "@/lib/http";

export type SecurityEvent = {
  id: string;
  type: string;
  severity: "info" | "warn" | "critical" | string;
  message: string;
  created_at: string;
  resolved?: boolean;
};

export const securityApi = {
  events: (q: { limit?: number } = {}) =>
    http.get<{ items: SecurityEvent[] }>("/security/events", { query: q }),
  killSwitch: {
    status: () => http.get<{ enabled: boolean; activated_at?: string; reason?: string }>("/kill-switch/status"),
    activate: (body: { reason?: string } = {}) => http.post<{ enabled: true }>("/kill-switch/activate", body),
    deactivate: () => http.post<{ enabled: false }>("/kill-switch/deactivate"),
  },
  locker: {
    users: () => http.get<{ users: { id: string; email: string; isolated: boolean }[] }>("/locker/users"),
    security: () => http.get<{ events: SecurityEvent[] }>("/locker/security"),
    monitoring: () => http.get<unknown>("/locker/monitoring"),
  },
};
