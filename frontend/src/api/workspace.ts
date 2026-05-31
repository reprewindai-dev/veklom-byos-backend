/**
 * Workspace + tenant — /api/v1/workspace/*
 * Source: backend/apps/api/routers/workspace.py
 */
import { http } from "@/lib/http";
import type { ApiKeyRow } from "./types";

export type Workspace = {
  id: string;
  slug?: string;
  name?: string;
  region?: string;
  plan?: string;
  budget?: { monthly_cap?: number; current_spend?: number };
  settings?: Record<string, unknown>;
};

export type WorkspaceModel = {
  id: string;
  slug: string;
  enabled: boolean;
  bedrock_model_id?: string;
  connected?: boolean;
  context?: number;
};

export type WorkspaceMember = {
  id: string;
  email: string;
  name?: string;
  role: "Owner" | "Admin" | "Developer" | "Viewer" | "Billing" | string;
  mfa?: boolean;
  last_active?: string | null;
};

export const workspaceApi = {
  current: () => http.get<Workspace>("/workspace"),
  updateSettings: (settings: Record<string, unknown>) =>
    http.patch<Workspace>("/workspace/settings", { settings }),
  models: () => http.get<{ models: WorkspaceModel[] }>("/workspace/models"),
  toggleModel: (id: string, body: Partial<WorkspaceModel>) =>
    http.patch<WorkspaceModel>(`/workspace/models/${encodeURIComponent(id)}`, body),
  apiKeys: () => http.get<{ keys: ApiKeyRow[] }>("/workspace/api-keys"),
  createApiKey: (body: { name: string; scopes?: string[] }) =>
    http.post<{ id: string; key: string; prefix: string }>("/workspace/api-keys", body),
  deleteApiKey: (id: string) => http.delete<void>(`/workspace/api-keys/${encodeURIComponent(id)}`),
  members: () => http.get<{ members: WorkspaceMember[] }>("/workspace/members"),
  inviteMember: (body: { email: string; role: string }) =>
    http.post<WorkspaceMember>("/workspace/members/invite", body),
};
