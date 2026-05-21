# Zero-Trust Security & Perimeter Architecture

Veklom BYOS Backend implements a zero-trust security model. Every request is authenticated and authorized before any data is touched. No implicit trust exists anywhere in the stack.

## Authentication

### JWT Tokens
- Short-lived access tokens (default: 30 minutes)
- Long-lived refresh tokens (default: 30 days)
- Token payload includes: `user_id`, `workspace_id`, `role`
- Algorithm: HS256 (configurable via `ALGORITHM` env var)

### API Keys
- Format: `byos_<random-hex>`
- Stored as SHA-256 hash in Postgres — **never the raw key**
- Scoped per workspace
- Optional expiry (`expires_at`)
- Revocable instantly via `DELETE /api/v1/auth/api-keys/{id}`
- Seeded dev key generated automatically by `start.ps1`

### MFA (TOTP)
- **Setup:** `POST /api/v1/auth/mfa/setup` → returns QR code URL + secret
- Works with any TOTP app (Google Authenticator, Authy, 1Password)
- Once enabled, `mfa_code` is required on every login
- **Verify setup:** `POST /api/v1/auth/mfa/verify` with a valid 6-digit code

## Zero-Trust Dependencies
Our `Depends(get_current_user)` and underlying guards run on every protected route:
1. Extract `Authorization: Bearer <token>` or `X-API-Key: byos_...`
2. Validate signature / hash against database
3. Resolve workspace and user from token
4. Check user status is active (not suspended or deleted)
5. Attach workspace context to request context
6. Reject with 401/403 on any failure — no partial results

## Perimeter Security
Veklom uses layered perimeter controls before route logic is allowed to matter:
1. **Cloudflare/WAF** blocks commodity scans, bot floods, suspicious countries/ASNs, and known exploit payloads at the edge.
2. **Coolify/Traefik** or the deployment proxy terminates traffic and forwards only HTTPS traffic to the application container.
3. **LockerSecurityMiddleware** applies IDS signatures, per-IP rate limiting, security headers, and security-event logging.
4. **RequestSecurityMiddleware** applies request IDs, auth brute-force blocking, and clean audit correlation.

### Trusted Proxy Rules
Forwarded client-IP headers are never trusted from direct internet callers. By default, only loopback and private proxy networks are trusted:
- `127.0.0.0/8`
- `::1/128`
- `10.0.0.0/8`
- `172.16.0.0/12`
- `192.168.0.0/16`

## Role-Based Access Control (RBAC)
| Role | Capabilities |
|------|--------------|
| `admin` | Full access including user management, workspace config, admin panel |
| `member` | Use AI endpoints, manage own API keys, view own logs |
| `viewer` | Read-only: logs, dashboards, audit records |

## Encryption
### At Rest
- AES-256-GCM
- Field-level encryption for sensitive database columns (e.g., API keys, Plugin configurations)
- Separate `ENCRYPTION_KEY` environment variable (must differ from `SECRET_KEY`)

### In Transit
- All production traffic via HTTPS (Nginx + Certbot, or Caddy)
- TLS 1.2 minimum, TLS 1.3 preferred
- HTTP→HTTPS redirect enforced

## Security Events
All security-relevant events are logged to the `security_events` table with:
- Event type and threat classification
- IP address, user agent, timestamp
- AI confidence score (0–1) for automated detection
- Resolution status and notes

### Tracked Event Types
- `brute_force`: Repeated failed login attempts
- `suspicious_login`: Login from unusual location/device
- `unauthorized_access`: Request to resource without permission
- `rate_limit_abuse`: Excessive request volume
- `sql_injection`: SQL injection pattern detected in input
- `xss`: Cross-site scripting pattern detected
- `data_exfiltration`: Unusual bulk data export
- `anomaly`: ML-detected behavioural anomaly
