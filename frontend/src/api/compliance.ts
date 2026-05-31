/**
 * Compliance, privacy, content-safety, explainability.
 * Sources: backend/apps/api/routers/{compliance,security,exec_router}.py
 */
import { http } from "@/lib/http";

export type ComplianceFramework = {
  id: string;
  name: string;
  coverage_pct?: number;
  controls_total?: number;
  state?: "Audit-ready" | "Continuous" | "In-progress" | string;
  evidence_rows?: number | string;
};

export const complianceApi = {
  regulations: () => http.get<{ regulations: ComplianceFramework[] }>("/compliance/regulations"),
  check: (body: { regulation: string; payload: unknown }) =>
    http.post<{ passed: boolean; findings: unknown[] }>("/compliance/check", body),
  privacyStatus: () => http.get<{ pii_detected: boolean; phi_detected: boolean; last_scan?: string }>(
    "/privacy/status",
  ),
  privacyScan: (body: { text: string }) =>
    http.post<{ pii: string[]; phi: string[]; redacted: string }>("/privacy/scan", body),
  contentSafety: (body: { text: string }) =>
    http.post<{ flagged: boolean; categories: Record<string, number> }>("/content-safety/check", body),
  explain: (request_id: string) => http.get<{ steps: unknown[]; trace: unknown }>(
    `/explainability/${encodeURIComponent(request_id)}`,
  ),
};
