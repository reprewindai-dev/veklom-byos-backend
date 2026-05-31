/**
 * Routing, autonomous, deterministic substrate.
 * Sources: backend/apps/api/routers/{routing,autonomous}.py
 */
import { http } from "@/lib/http";

export type RoutingTopology = {
  classes: string[];
  substrate: { name: string; version?: string };
  description?: string;
};

export type RoutingDecision = {
  request_id?: string;
  workload_class: string;
  route: string;
  rationale?: string;
};

export const routingApi = {
  contract: () => http.get<unknown>("/routing"),
  topology: () => http.get<RoutingTopology>("/routing/topology"),
  economics: () => http.get<{ token_model: unknown; latency_model: unknown }>("/routing/economics"),
  operationalRuntime: () => http.get<unknown>("/routing/operational-runtime"),
  stack: () => http.get<unknown>("/routing/stack"),
  decide: (body: { prompt?: string; tags?: string[]; meta?: Record<string, unknown> }) =>
    http.post<RoutingDecision>("/routing/decision", body),
  autonomous: {
    decisions: () => http.get<{ items: RoutingDecision[] }>("/autonomous/decisions"),
    override: (body: { request_id: string; route: string; reason?: string }) =>
      http.post<{ accepted: boolean }>("/autonomous/override", body),
  },
};
