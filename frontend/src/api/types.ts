/** Shared shapes used by multiple API modules. */

export type PaginatedQuery = {
  limit?: number;
  offset?: number;
};

export type ID = string;

/** Marketplace listing — superset of /marketplace/listings and public /marketplace. */
export type MarketplaceListing = {
  id: ID;
  /** Public marketplace also returns "name" instead of "title". */
  title?: string;
  name?: string;
  type?: string;
  category?: string;
  provider?: string;
  description?: string;
  pricing?: { type?: string; amount?: number; currency?: string };
  url?: string;
  status?: string;
  badges?: string[];
  compliance?: string[];
  rating?: number;
  installs?: number;
  install?: string;
  target?: string[];
  featured?: boolean;
  created_at?: string;
};

export type AuthUser = {
  id: string;
  email: string;
  name?: string;
  workspace_id?: string;
  role?: string;
  github_connected?: boolean;
};

export type AuditLog = {
  id: string;
  workspace_id: string;
  user_id: string;
  operation_type: string;
  provider: string;
  model: string;
  cost?: string | number;
  tokens_input?: number | null;
  tokens_output?: number | null;
  created_at: string;
  log_hash: string;
  previous_log_hash?: string | null;
};

export type ApiKeyRow = {
  id: string;
  name: string;
  prefix: string;
  scopes: string[];
  created_at: string;
  last_used_at: string | null;
};

export type AICompleteRequest = {
  model: string;
  prompt: string;
  max_tokens?: number;
};

export type AICompleteResponse = {
  response_text: string;
  model: string;
  bedrock_model_id?: string;
  tokens_deducted: number;
  output_tokens: number;
  wallet_balance?: number;
  timestamp: string;
};
