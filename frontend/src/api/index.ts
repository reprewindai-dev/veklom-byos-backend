/**
 * Veklom API client — one module per backend router file.
 *
 * Verified against /tmp/veklom-byos-backend/backend/apps/api/routers/*.py
 * and the canonical API_SURFACE.md / WIRING_CROSS_REFERENCE.md docs.
 *
 * If a method exists here, it maps to a real backend route. Nothing is invented.
 */

export { authApi } from "./auth";
export { aiApi } from "./ai";
export type { AIModelEntry, PredictCostRequest, PredictCostResponse } from "./ai";
export { workspaceApi } from "./workspace";
export { marketplaceApi } from "./marketplace";
export { complianceApi } from "./compliance";
export { auditApi } from "./audit";
export { billingApi } from "./billing";
export { routingApi } from "./routing";
export { monitoringApi } from "./monitoring";
export { securityApi } from "./security";
export { pipelinesApi } from "./pipelines";
export { deploymentsApi } from "./deployments";
export { adminApi } from "./admin";
export { commandCenterApi } from "./commandCenter";
export type { TerminalDescriptor, TerminalEndpoint, CCActivityEvent, CCAlert, CCUserSummary } from "./commandCenter";
export { gpcApi } from "./gpc";
export type { GpcPlan, GpcRun, GpcEvent, DecisionFrame } from "./gpc";
export { agentsApi, copilotApi, repoRiskGateApi } from "./agents";
export * from "./types";
