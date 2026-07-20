# Veklom - Sovereign AI Runtime

Veklom is a sovereign AI runtime your company can trust and control. Install on your own servers in ~30 minutes, connect 160+ systems, and govern agents with policy, audit, and shut-off switches. Start with a 14-day evaluation, then move to team or business plans when you're ready. Bring your workloads; Veklom routes, enforces permissions, and proves what ran—without locking you into our cloud.

## Quick Start

### Install (One-Line)

```bash
curl -fsSL https://get.veklom.com/install.sh | bash && veklom up --connect
```

The installer:
- Verifies GPG signature
- Downloads container bundle
- Brings up services with docker compose

### Configuration

Create `veklom.yaml`:

```yaml
workspace: "acme-core"
connectors:
  - type: "postgres"
    url: "postgres://user:pass@db.acme:5432/core"
    permission: "read"
  - type: "slack"
    token: "${SLACK_BOT_TOKEN}"
    permission: "write"
policies:
  - name: "prod-db-readonly"
    match: { connector: "postgres", env: "prod" }
    allow: ["SELECT"]
  - name: "no_pii_export"
    deny: ["EXPORT_PII", "SEND_PII_EXTERNALLY"]
agents:
  - name: "ops-assistant"
    model: "veklom-llama3-70b"
    tools: ["postgres", "slack"]
```

### First Success

```bash
veklom validate && veklom apply
```

Then open http://localhost:8088 to:
- Add Slack + Postgres connectors
- Run the Ops Assistant
- View audit logs

### Uninstall

```bash
veklom down
```

No data lock-in—your config and data stay with you.

## Pricing

| Plan | What you get | Who it's for | Price |
|------|--------------|--------------|-------|
| **Team** | BYOS install, 10 seats, 10 connectors, basic audit, email support | Small teams piloting | $12,000/mo or $120,000/yr |
| **Business** | Unlimited seats, 50 connectors, advanced policy/audit, SSO, priority support | Departments / scale-up | $35,000/mo or $350,000/yr |
| **Enterprise** | Private terms, on-prem support, custom connectors, dedicated SLA | Regulated / large orgs | Custom |

## Permissions Matrix

| Capability | Team | Business | Enterprise |
|------------|------|----------|------------|
| Policy engine | ✓ | ✓ (advanced rules) | ✓ (custom) |
| Audit timeline | Basic | Advanced (export) | Advanced + immutable log |
| SSO (SAML/OIDC) | — | ✓ | ✓ |
| Private models/endpoints | — | Optional | ✓ |
| On-prem support | — | — | ✓ |

## FAQ

**Where does it run?**
Your servers (BYOS) or private cloud.

**Data egress?**
Off by default; policies control outbound.

**What if billing lapses?**
72-hour grace, then graceful shutdown.

**How long to pilot?**
14 days; keep your config after.

## Demo

Watch the 15-second demo showing:
1. `veklom up` bringing services online
2. Paste `veklom.yaml`, hit Validate → Apply
3. Run "ops-assistant" asking a real question
4. Policy banner pops ("blocked PII export")
5. Open Audit tab showing who/what/when

[![Demo GIF](https://veklom.com/assets/demo.gif)](https://veklom.com/demo)
