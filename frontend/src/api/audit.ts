/**
 * Audit logs — /api/v1/audit/*
 * Source: backend/apps/api/routers/security.py + audit.py
 */
import { http } from "@/lib/http";
import type { AuditLog, PaginatedQuery } from "./types";

export const auditApi = {
  logs: (q: PaginatedQuery = {}) =>
    http.get<{ items: AuditLog[]; total: number }>("/audit/logs", {
      query: { limit: q.limit, offset: q.offset },
    }),
  log: (id: string) => http.get<AuditLog>(`/audit/logs/${encodeURIComponent(id)}`),
  verify: (id: string) => http.get<{ valid: boolean; chain_intact: boolean }>(
    `/audit/verify/${encodeURIComponent(id)}`,
  ),
};
