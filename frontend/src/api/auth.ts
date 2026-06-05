// Auth API client — maps 1:1 to backend/apps/api/routers/auth.py
import { http, setSession, clearSession } from '../lib/http';

export interface AuthUser {
  id: string;
  email: string;
  full_name?: string;
  role?: string;
  workspace_id?: string;
  workspace_name?: string;
  github_username?: string;
  github_connected?: boolean;
  created_at?: string | null;
  plan?: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: AuthUser;
  is_eval?: boolean;
  plan?: string;
}

export interface WorkspaceSummary {
  id?: string;
  name?: string;
  plan?: string;
  [k: string]: unknown;
}

export interface MeResponse extends AuthUser {
  workspace?: WorkspaceSummary;
  capabilities?: Record<string, boolean>;
}

// POST /auth/login
export async function login(email: string, password: string): Promise<TokenPair> {
  const res = await http.post<TokenPair>('/auth/login', { email, password });
  setSession(res.access_token, res.refresh_token, res.user);
  return res;
}

// POST /auth/register
export async function register(payload: {
  email: string;
  password: string;
  full_name?: string;
  workspace_name?: string;
}): Promise<TokenPair> {
  const res = await http.post<TokenPair>('/auth/register', payload);
  setSession(res.access_token, res.refresh_token, res.user);
  return res;
}

// POST /auth/eval-session — free evaluation session (no credentials)
export async function startEvalSession(fingerprint?: string): Promise<TokenPair> {
  const res = await http.post<TokenPair>('/auth/eval-session', {
    fingerprint: fingerprint || `web_${Math.random().toString(36).slice(2)}`,
  });
  setSession(res.access_token, res.refresh_token, res.user);
  return res;
}

// GET /auth/me
export function me(): Promise<MeResponse> {
  return http.get<MeResponse>('/auth/me');
}

// POST /auth/logout
export async function logout(): Promise<void> {
  try {
    await http.post('/auth/logout');
  } finally {
    clearSession();
  }
}
