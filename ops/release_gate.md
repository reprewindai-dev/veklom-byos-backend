# Cross-functional release gate and rollback runbook

Here's a one-page, copy-pasteable release day runbook you can use to greenlight or abort a Veklom release—with hard gates, exact rollback commands, and a 3-step on-call triage checklist.

## Veklom Release Gate: Ship or Roll Back

**How to use this**

Run each gate in order. If any gate fails, STOP and go to Rollback. If all gates pass, you're clear to proceed.

### Gate 1 — Artifact & Integrity (must PASS)

```bash
# Image signature
cosign verify ghcr.io/ORG/REPO:${TAG} || exit 1

# SBOM present
syft ghcr.io/ORG/REPO:${TAG} -o syft-json > sbom.json || exit 1

# Vulnerability scan (no HIGH/CRITICAL; exit-code 0)
trivy image --exit-code 1 --severity HIGH,CRITICAL ghcr.io/ORG/REPO:${TAG}; test $? -eq 0
```

### Gate 2 — Infra Health (must PASS)

```bash
# Core health
curl -fsS https://veklom.com/health >/dev/null || exit 1

# Auth'd JSON smoke (expects .status=="ok")
curl -fsS https://veklom.com/api/v1/smoke/eval-token \
  -H "Authorization: Bearer $SMOKE_TOKEN" | jq '.status=="ok"' | grep true >/dev/null || exit 1
```

### Gate 3 — Observability: Funnel Events (must PASS)

```bash
# Must return an event within last 10 minutes
curl -s -H "Authorization: Bearer $POSTHOG_API_KEY" \
"https://app.posthog.com/api/projects/$PH_PROJECT/events/?event=demo_request&limit=1" | \
jq -e '(.results | length) >= 1 and ((.results[0].timestamp | fromdateiso8601) > (now - 600))' >/dev/null || exit 1
```

### Gate 4 — DSA / Legal (must PASS)

```bash
# Public EU/DSA notice reachable and contains contact/complaint keywords
curl -fsS https://veklom.com/dsa -o - | grep -Ei 'complaint|contact' >/dev/null || exit 1

# Complaint endpoint accepts POST and acknowledges (200/202)
code=$(curl -s -o /tmp/dsa.json -w "%{http_code}" -X POST https://veklom.com/dsa/complaint \
  -H 'Content-Type: application/json' \
  -d '{"email":"ops@veklom.com","url":"https://veklom.com/","description":"smoke test"}')
test "$code" = "200" -o "$code" = "202" || exit 1
jq -e '. | length >= 1' /tmp/dsa.json >/dev/null || exit 1
```

### Gate 5 — Payments (fiat sandbox + on-chain) (must PASS)

```bash
# Stripe sandbox PI creation (requires_payment_method or succeeded acceptable)
stripe_status=$(curl -s -u $STRIPE_KEY: https://api.stripe.com/v1/payment_intents \
  -d amount=100 -d currency=usd -d payment_method_types[]=card | jq -r .status)
echo "$stripe_status" | grep -E 'requires_payment_method|succeeded' >/dev/null || exit 1

# On-chain quick balance check (EVM)
bal_hex=$(curl -s -X POST -H 'Content-Type: application/json' "$ETH_RPC_URL" \
  --data '{"jsonrpc":"2.0","method":"eth_getBalance","params":["'"$HOT_WALLET_ADDRESS"'","latest"],"id":1}' \
  | jq -r .result)
# ensure balance > gas_threshold (example: 0.01 ETH)
python3 - <<'PY'
import sys,decimal
wei=int(sys.argv[1],16)
eth=decimal.Decimal(wei)/decimal.Decimal(10**18)
assert eth > decimal.Decimal("0.01")
PY "$bal_hex" || exit 1

# If webhooks are part of the payments route, simulate:
# stripe trigger payment_intent.succeeded
# or POST a signed webhook to your endpoint and verify PostHog event emission
```

### Gate 6 — Latency & Errors (must PASS)

- 95th percentile latency < 800ms over rolling 5m
- 5xx rate < 1% over rolling 5m

(Use your existing health/monitor dashboards; if thresholds exceeded → fail.)

## Immediate Rollback Triggers (any one ⇒ rollback NOW)

- Health endpoint non-200 for >3 consecutive checks OR any paging alert from health monitor
- 5xx rate >5% sustained for 3 minutes
- PostHog funnel event drop >90% vs baseline in last 10 minutes
- Any payment end-to-end failure affecting >1% of sandbox attempts or webhook delivery failures

## Exact Rollback Commands (copy-paste)

### Kubernetes (primary)

```bash
kubectl -n prod rollout undo deployment/veklom-backend \
  --to-revision=$(kubectl -n prod rollout history deploy/veklom-backend --revision=1 | tail -n1 | awk '{print $1}')
kubectl -n prod rollout status deploy/veklom-backend --watch
```

### Docker Host (fallback)

```bash
docker pull ghcr.io/ORG/REPO:previous_tag && \
docker stop veklom || true && docker rm veklom || true && \
docker run -d --name veklom -p 8080:8080 ghcr.io/ORG/REPO:previous_tag --env-file /etc/veklom/env
```

### Veklom Coolify/Hetzner (current deployment)

```bash
ssh -i ~/.ssh/veklom-deploy root@5.78.135.11
cd /data/coolify/applications/n13gp1nhrcdp0hvazvbnlxru
git log --oneline -5  # Find previous commit
git checkout <previous_commit_sha>
docker build -t veklom-local:latest .
docker stop n13gp1nhrcdp0hvazvbnlxru-083606963671 || true
docker rm n13gp1nhrcdp0hvazvbnlxru-083606963671 || true
docker run -d \
  --name n13gp1nhrcdp0hvazvbnlxru-083606963671 \
  --network coolify \
  --env-file /data/coolify/applications/n13gp1nhrcdp0hvazvbnlxru/.env \
  --restart unless-stopped \
  -p 80:80 \
  veklom-local:latest
curl -s http://localhost:80/health
curl -sk -H "Host: veklom.com" https://localhost/health
```

### Git Revert (if deploys track main)

```bash
git revert --no-edit <bad_commit_sha> && git push origin main && ./scripts/deploy.sh prod
```

### DB Migration Quick Rollback

```bash
# Alembic
alembic downgrade -1

# or Knex
npx knex migrate:down --knexfile ./knexfile.js
```

### Confirm Post-Rollback

```bash
curl -fsS https://veklom.com/health || exit 2
curl -s -H "Authorization: Bearer $POSTHOG_API_KEY" \
"https://app.posthog.com/api/projects/$PH_PROJECT/events/?event=demo_request&limit=1" | jq -e '(.results | length) >= 1'
```

## Minimal On-Call Triage (A-B-C)

### A) Page & label

Open an incident, tag release-rollback.
If payments impacted, notify legal@veklom + finance@veklom.

### B) Collect

```bash
kubectl -n prod logs -l app=veklom-backend --since=10m > /tmp/veklom-k8s-logs.txt
journalctl -u docker -n 500 > /tmp/docker-host-logs.txt
# (or fetch container logs from your cloud provider)
```

Attach artifacts to the incident.

### C) Act

Execute the Rollback above.
Re-check health + PostHog events.
Post an incident update with timeline and create a follow-up ticket for root cause + a preventative test.

## Notes

Treat this playbook as the single source of truth for go/no-go.
Keep placeholders filled by CI/on-call env: `$POSTHOG_API_KEY`, `previous_tag`, `<bad_commit_sha>`, `$HOT_WALLET_ADDRESS`, `$ETH_RPC_URL`, `$STRIPE_KEY`, `$SMOKE_TOKEN`, `$PH_PROJECT`, `${TAG}`.

If a gate is flaky, it's a fail until proven otherwise.
