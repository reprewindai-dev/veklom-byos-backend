/**
 * Authentication — /api/v1/auth/*
 * Source: backend/apps/api/routers/auth.py
 */
import { http } from "@/lib/http";
import { setAuth, clearAuth } from "@/lib/auth";
import type { AuthUser } from "./types";

export type LoginRequest = { email: string; password: string };
export type RegisterRequest = { email: string; password: string; name?: string; workspace_name?: string };
export type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in?: number;
  user: AuthUser;
};

export const authApi = {
  async login(body: LoginRequest): Promise<TokenResponse> {
    const res = await http.post<TokenResponse>("/auth/login", body, { unauthenticated: true });
    setAuth({ access_token: res.access_token, refresh_token: res.refresh_token, user: res.user });
    return res;
  },

  async register(body: RegisterRequest): Promise<TokenResponse> {
    const res = await http.post<TokenResponse>("/auth/register", body, { unauthenticated: true });
    setAuth({ access_token: res.access_token, refresh_token: res.refresh_token, user: res.user });
    return res;
  },

  async logout(): Promise<void> {
    try {
      await http.post<void>("/auth/logout");
    } finally {
      clearAuth();
    }
  },

  refresh(refresh_token: string) {
    return http.post<TokenResponse>("/auth/refresh", { refresh_token }, { unauthenticated: true });
  },

  me() {
    return http.get<AuthUser>("/auth/me");
  },

  updateMe(patch: Partial<AuthUser>) {
    return http.patch<AuthUser>("/auth/me", patch);
  },

  mfa: {
    enable: () => http.post<{ secret: string; qr_code?: string }>("/auth/mfa/enable"),
    verify: (code: string) => http.post<{ verified: boolean }>("/auth/mfa/verify", { code }),
  },

  apiKeys: {
    list: () => http.get<unknown[]>("/auth/api-keys"),
    create: (body: { name: string; scopes?: string[]; expires_in_days?: number }) =>
      http.post<{ id: string; key: string; prefix: string; name: string; scopes: string[] }>("/auth/api-keys", body),
    revoke: (id: string) => http.delete<void>(`/auth/api-keys/${encodeURIComponent(id)}`),
  },

  github: {
    /** Browser-redirect to begin the OAuth flow. */
    initiateUrl: () => http.url(`/api/v1/auth/oauth/github`),
  },
};
