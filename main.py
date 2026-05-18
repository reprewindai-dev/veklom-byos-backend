from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Veklom BYOS Backend</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a0f; color: #e2e8f0; line-height: 1.6; }
  .hero { background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%); padding: 80px 40px; text-align: center; border-bottom: 1px solid #1e293b; }
  .badge { display: inline-block; background: #1e3a5f; color: #60a5fa; font-size: 12px; font-weight: 600; padding: 4px 12px; border-radius: 20px; margin-bottom: 24px; letter-spacing: 0.05em; text-transform: uppercase; border: 1px solid #2563eb44; }
  h1 { font-size: 3rem; font-weight: 800; background: linear-gradient(135deg, #e2e8f0, #94a3b8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin-bottom: 16px; }
  .tagline { font-size: 1.2rem; color: #94a3b8; max-width: 600px; margin: 0 auto 40px; }
  .cta { display: inline-block; background: #2563eb; color: white; padding: 12px 28px; border-radius: 8px; font-weight: 600; text-decoration: none; margin: 0 8px; transition: background 0.2s; }
  .cta:hover { background: #1d4ed8; }
  .cta.secondary { background: transparent; border: 1px solid #334155; color: #94a3b8; }
  .cta.secondary:hover { background: #1e293b; }
  .container { max-width: 1100px; margin: 0 auto; padding: 60px 40px; }
  .section-title { font-size: 1.5rem; font-weight: 700; color: #e2e8f0; margin-bottom: 8px; }
  .section-sub { color: #64748b; margin-bottom: 32px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-bottom: 60px; }
  .card { background: #0f172a; border: 1px solid #1e293b; border-radius: 12px; padding: 24px; transition: border-color 0.2s; }
  .card:hover { border-color: #334155; }
  .card-icon { font-size: 1.8rem; margin-bottom: 12px; }
  .card h3 { font-size: 1rem; font-weight: 600; color: #e2e8f0; margin-bottom: 8px; }
  .card p { font-size: 0.875rem; color: #64748b; }
  .notice { background: #0f2744; border: 1px solid #1e3a5f; border-radius: 12px; padding: 24px 28px; margin-bottom: 48px; }
  .notice h3 { color: #60a5fa; font-size: 1rem; margin-bottom: 8px; }
  .notice p { color: #94a3b8; font-size: 0.9rem; }
  .notice code { background: #1e293b; padding: 2px 6px; border-radius: 4px; font-family: monospace; color: #7dd3fc; }
  table { width: 100%; border-collapse: collapse; margin-bottom: 32px; font-size: 0.875rem; }
  th { background: #0f172a; color: #94a3b8; font-weight: 600; text-align: left; padding: 10px 14px; border: 1px solid #1e293b; }
  td { padding: 10px 14px; border: 1px solid #1e293b; color: #cbd5e1; }
  td code { background: #1e293b; padding: 2px 6px; border-radius: 3px; font-family: monospace; color: #7dd3fc; font-size: 0.8rem; }
  tr:hover td { background: #0f172a44; }
  .section { margin-bottom: 56px; }
  .tag { display: inline-block; font-size: 0.7rem; font-weight: 600; padding: 2px 8px; border-radius: 10px; margin-right: 4px; }
  .tag-public { background: #14532d44; color: #4ade80; border: 1px solid #16a34a44; }
  .tag-auth { background: #1e3a5f44; color: #60a5fa; border: 1px solid #2563eb44; }
  .tag-admin { background: #4c1d9544; color: #c084fc; border: 1px solid #7c3aed44; }
  footer { border-top: 1px solid #1e293b; padding: 32px 40px; text-align: center; color: #475569; font-size: 0.875rem; }
</style>
</head>
<body>
<div class="hero">
  <div class="badge">Enterprise AI Infrastructure</div>
  <h1>Veklom BYOS Backend</h1>
  <p class="tagline">Private governed AI backend — run on your own infrastructure with policy enforcement, cost controls, and tamper-evident audit logs.</p>
  <a href="#features" class="cta">Explore Features</a>
  <a href="#api" class="cta secondary">API Reference</a>
</div>

<div class="container">

  <div class="notice">
    <h3>Documentation Package</h3>
    <p>This is the Veklom BYOS Backend documentation and buyer package. The full source code is delivered to buyers via a private GitHub repository. See <code>BUYER_PACKAGE.md</code> for details on what is included with purchase, or contact <strong>support@veklom.com</strong>.</p>
  </div>

  <div id="features" class="section">
    <div class="section-title">Core Capabilities</div>
    <div class="section-sub">Enterprise-grade AI governance for security-conscious organizations</div>
    <div class="grid">
      <div class="card">
        <div class="card-icon">🛡️</div>
        <h3>Policy Enforcement</h3>
        <p>Content safety scoring, PII/PHI detection and redaction, HIPAA/GDPR/SOC2 compliance checks on every request.</p>
      </div>
      <div class="card">
        <div class="card-icon">🔀</div>
        <h3>Intelligent Routing</h3>
        <p>Autonomous model selection by cost, quality, and risk. Fallback chains across OpenAI, Anthropic, vLLM, and Ollama.</p>
      </div>
      <div class="card">
        <div class="card-icon">💰</div>
        <h3>Cost Controls</h3>
        <p>Token wallet with prepaid credits, budget rules with hard/soft limits, real-time spend tracking and Stripe billing.</p>
      </div>
      <div class="card">
        <div class="card-icon">🔍</div>
        <h3>Audit & Evidence</h3>
        <p>Tamper-evident SHA hash chain audit logs, hash verification endpoints, and complete request traceability.</p>
      </div>
      <div class="card">
        <div class="card-icon">🔑</div>
        <h3>API Key Management</h3>
        <p>Scoped API keys with per-key usage tracking, kill switch for instant revocation of all AI access.</p>
      </div>
      <div class="card">
        <div class="card-icon">🏢</div>
        <h3>Multi-Tenant Isolation</h3>
        <p>Full workspace isolation with role-based access (owner, admin, member, viewer) and per-tenant model configs.</p>
      </div>
      <div class="card">
        <div class="card-icon">🔐</div>
        <h3>Security</h3>
        <p>JWT authentication, optional MFA (TOTP), locker isolation, and security event log.</p>
      </div>
      <div class="card">
        <div class="card-icon">⚡</div>
        <h3>Streaming Inference</h3>
        <p>SSE streaming via OpenAI-compatible interface. Connect your own vLLM, Ollama, or any compatible endpoint.</p>
      </div>
    </div>
  </div>

  <div id="api" class="section">
    <div class="section-title">API Surface</div>
    <div class="section-sub">43 route modules — base URL: <code style="background:#1e293b;padding:2px 8px;border-radius:4px;color:#7dd3fc">https://your-domain.com/api/v1</code></div>

    <h3 style="color:#94a3b8;font-size:0.85rem;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:12px">Health &amp; Status</h3>
    <table>
      <tr><th>Method</th><th>Path</th><th>Auth</th><th>Description</th></tr>
      <tr><td>GET</td><td><code>/health</code></td><td><span class="tag tag-public">Public</span></td><td>Health check — returns status, version, timestamp</td></tr>
      <tr><td>GET</td><td><code>/status</code></td><td><span class="tag tag-public">Public</span></td><td>Platform status snapshot</td></tr>
      <tr><td>GET</td><td><code>/platform/pulse</code></td><td><span class="tag tag-auth">Auth</span></td><td>Real-time platform metrics</td></tr>
    </table>

    <h3 style="color:#94a3b8;font-size:0.85rem;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:12px">Authentication</h3>
    <table>
      <tr><th>Method</th><th>Path</th><th>Auth</th><th>Description</th></tr>
      <tr><td>POST</td><td><code>/auth/register</code></td><td><span class="tag tag-public">Public</span></td><td>Register new user</td></tr>
      <tr><td>POST</td><td><code>/auth/login</code></td><td><span class="tag tag-public">Public</span></td><td>Login, returns JWT pair</td></tr>
      <tr><td>POST</td><td><code>/auth/refresh</code></td><td><span class="tag tag-public">Public</span></td><td>Refresh access token</td></tr>
      <tr><td>GET</td><td><code>/auth/me</code></td><td><span class="tag tag-auth">Auth</span></td><td>Current user profile</td></tr>
      <tr><td>POST</td><td><code>/auth/mfa/enable</code></td><td><span class="tag tag-auth">Auth</span></td><td>Enable MFA (TOTP)</td></tr>
      <tr><td>GET</td><td><code>/auth/api-keys</code></td><td><span class="tag tag-auth">Auth</span></td><td>List user API keys</td></tr>
      <tr><td>POST</td><td><code>/auth/api-keys</code></td><td><span class="tag tag-auth">Auth</span></td><td>Create API key</td></tr>
    </table>

    <h3 style="color:#94a3b8;font-size:0.85rem;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:12px">AI Execution</h3>
    <table>
      <tr><th>Method</th><th>Path</th><th>Auth</th><th>Description</th></tr>
      <tr><td>POST</td><td><code>/v1/exec</code></td><td><span class="tag tag-auth">Auth</span></td><td>SSE streaming inference (OpenAI-compatible)</td></tr>
      <tr><td>POST</td><td><code>/ai/complete</code></td><td><span class="tag tag-auth">Auth</span></td><td>Non-streaming completion</td></tr>
      <tr><td>GET</td><td><code>/ai/models</code></td><td><span class="tag tag-auth">Auth</span></td><td>List available models</td></tr>
      <tr><td>POST</td><td><code>/ai/predict-cost</code></td><td><span class="tag tag-auth">Auth</span></td><td>Cost prediction before execution</td></tr>
      <tr><td>POST</td><td><code>/ai/transcribe</code></td><td><span class="tag tag-auth">Auth</span></td><td>Audio transcription</td></tr>
    </table>

    <h3 style="color:#94a3b8;font-size:0.85rem;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:12px">Compliance &amp; Governance</h3>
    <table>
      <tr><th>Method</th><th>Path</th><th>Auth</th><th>Description</th></tr>
      <tr><td>POST</td><td><code>/compliance/check</code></td><td><span class="tag tag-auth">Auth</span></td><td>Run compliance check (HIPAA/GDPR/SOC2)</td></tr>
      <tr><td>POST</td><td><code>/privacy/scan</code></td><td><span class="tag tag-auth">Auth</span></td><td>Scan content for PII/PHI</td></tr>
      <tr><td>POST</td><td><code>/content-safety/check</code></td><td><span class="tag tag-auth">Auth</span></td><td>Content safety scoring</td></tr>
      <tr><td>GET</td><td><code>/audit/logs</code></td><td><span class="tag tag-auth">Auth</span></td><td>Paginated audit log</td></tr>
      <tr><td>GET</td><td><code>/audit/verify/{id}</code></td><td><span class="tag tag-auth">Auth</span></td><td>Verify audit log hash integrity</td></tr>
    </table>

    <h3 style="color:#94a3b8;font-size:0.85rem;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:12px">Billing &amp; Cost</h3>
    <table>
      <tr><th>Method</th><th>Path</th><th>Auth</th><th>Description</th></tr>
      <tr><td>GET</td><td><code>/wallet/balance</code></td><td><span class="tag tag-auth">Auth</span></td><td>Token wallet balance</td></tr>
      <tr><td>POST</td><td><code>/wallet/topup/checkout</code></td><td><span class="tag tag-auth">Auth</span></td><td>Stripe topup checkout</td></tr>
      <tr><td>GET</td><td><code>/subscriptions/plans</code></td><td><span class="tag tag-public">Public</span></td><td>Available subscription plans</td></tr>
      <tr><td>GET</td><td><code>/budget/rules</code></td><td><span class="tag tag-auth">Auth</span></td><td>Budget rules list</td></tr>
      <tr><td>POST</td><td><code>/budget/rules</code></td><td><span class="tag tag-auth">Auth</span></td><td>Create budget rule</td></tr>
    </table>

    <h3 style="color:#94a3b8;font-size:0.85rem;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:12px">Security</h3>
    <table>
      <tr><th>Method</th><th>Path</th><th>Auth</th><th>Description</th></tr>
      <tr><td>POST</td><td><code>/kill-switch/activate</code></td><td><span class="tag tag-admin">Admin</span></td><td>Instantly disable all AI access</td></tr>
      <tr><td>GET</td><td><code>/security/events</code></td><td><span class="tag tag-auth">Auth</span></td><td>Security event log</td></tr>
      <tr><td>GET</td><td><code>/admin/users</code></td><td><span class="tag tag-admin">Admin</span></td><td>All users across workspaces</td></tr>
    </table>
  </div>

  <div class="section">
    <div class="section-title">Tech Stack</div>
    <div class="section-sub">Built for production reliability</div>
    <div class="grid">
      <div class="card">
        <h3>Runtime</h3>
        <p>Python 3.11+ · FastAPI 0.110+ · Uvicorn · asyncpg</p>
      </div>
      <div class="card">
        <h3>Data</h3>
        <p>PostgreSQL 14+ · SQLAlchemy 2.x · Alembic migrations · Redis 7+</p>
      </div>
      <div class="card">
        <h3>AI Providers</h3>
        <p>OpenAI · Anthropic · vLLM · Ollama · Any OpenAI-compatible endpoint</p>
      </div>
      <div class="card">
        <h3>Infrastructure</h3>
        <p>Docker · docker-compose · Coolify · Render · Hetzner · Cloudflare Tunnel</p>
      </div>
      <div class="card">
        <h3>Billing</h3>
        <p>Stripe subscriptions · Metered usage · Connect · Topup checkout flow</p>
      </div>
      <div class="card">
        <h3>Monitoring</h3>
        <p>Sentry · Prometheus metrics · Upstash QStash · Resend email</p>
      </div>
    </div>
  </div>

</div>

<footer>
  &copy; 2026 CO2 Router / Veklom. All rights reserved. &nbsp;·&nbsp;
  <a href="mailto:support@veklom.com" style="color:#475569">support@veklom.com</a> &nbsp;·&nbsp;
  <a href="https://veklom.com" style="color:#475569">veklom.com</a>
</footer>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML.encode("utf-8"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"Serving on http://0.0.0.0:{port}")
    server.serve_forever()
