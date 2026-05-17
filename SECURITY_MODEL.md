# SECURITY_MODEL.md — Security Architecture

## Authentication Flow

1. Client posts credentials to `POST /api/v1/auth/login`
2. Server validates credentials, checks MFA if enabled
3. Returns short-lived access token (JWT, default 30 min) + long-lived refresh token
4. Client includes `Authorization: Bearer <access_token>` on all subsequent requests
5. Client uses refresh token at `POST /api/v1/auth/refresh` before expiry

## JWT Tokens

- Algorithm: `HS256` (configurable via `JWT_ALGORITHM`)
- Access token expiry: 30 minutes (configurable)
- Refresh token expiry: 30 days (configurable)
- Secret: `JWT_SECRET_KEY` — must be a random 32+ byte hex string
- Generate: `openssl rand -hex 32`

## API Key Authentication

- API keys are an alternative to JWT for programmatic access
- Scoped per workspace or per user
- Each key has configurable permissions (read, write, admin)
- Usage tracked per key
- Kill switch instantly revokes all keys for a workspace
- Keys stored as SHA-256 hashes — plaintext never stored after creation

## Tenant Isolation

- All database queries are scoped by `workspace_id`
- Middleware injects workspace context from JWT claims
- Cross-workspace data access is impossible at the query layer
- Admin routes require elevated JWT claim (`role: admin`)

## Kill Switch

- `POST /api/v1/kill-switch/activate` sets a global flag in Redis
- All AI execution routes (`/exec`, `/ai/*`) check this flag before processing
- Activation is logged to immutable audit trail
- Deactivation requires admin role

## Audit Log Integrity

- Every audit log entry is hashed using SHA-256
- Each hash includes the previous entry's hash (chain)
- `GET /api/v1/audit/verify/{id}` recomputes and validates the chain
- Tampering with any entry breaks all subsequent hashes

## Secrets Management

- All secrets loaded from environment variables — never hardcoded
- `.env` files excluded from version control via `.gitignore`
- Production: use Coolify/Render secret management or Vault
- Rotate `JWT_SECRET_KEY` will invalidate all active sessions
- Rotate `LICENSE_PRIVATE_KEY` requires buyer re-activation

## Transport Security

- All production traffic must use HTTPS/TLS
- CORS restricted to `CORS_ORIGINS` environment variable
- Cloudflare Tunnel recommended for BYOS deployments (no exposed ports)

## Content Security

- Every AI request passes through content safety scoring
- PII/PHI detection runs before data reaches external AI providers
- Configurable redaction: replace, mask, or block
- All policy decisions logged to audit trail
