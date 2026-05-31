/**
 * Monitoring, platform pulse, insights, telemetry.
 * Sources: backend/apps/api/routers/{monitoring,system,health}.py
 */
import { http } from "@/lib/http";

export type PulseSnapshot = {
  requests_per_min?: number;
  tokens_per_sec?: number;
  p50_latency_ms?: number;
  p95_latency_ms?: number;
  gpu_util_pct?: number;
  error_rate_pct?: number;
  spend_today_usd?: number;
  active_models?: number;
  audit_entries_total?: number;
  [k: string]: unknown;
};

export const monitoringApi = {
  health: () => http.get<{ status: string; version?: string; timestamp?: string }>("/health"),
  status: () => http.get<{ platform: string; status: string }>("/status"),
  pulse: () => http.get<PulseSnapshot>("/platform/pulse"),
  pulseStreamUrl: () => http.url("/api/v1/platform/pulse/stream"),
  monitoring: {
    health: () => http.get<unknown>("/monitoring/health"),
    events: (q: { limit?: number } = {}) =>
      http.get<{ items: { id: string; type: string; severity: string; message: string; created_at: string }[] }>(
        "/monitoring/events",
        { query: q },
      ),
  },
  insights: {
    summary: () => http.get<{ savings_usd?: number; suggestions?: { id: string; title: string }[] }>(
      "/insights/summary",
    ),
  },
  telemetry: (body: { event: string; payload?: Record<string, unknown> }) =>
    http.post<void>("/telemetry", body),
};
