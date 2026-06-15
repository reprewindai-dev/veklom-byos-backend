# MCPAPI Operations & Deployment Guide

**Version:** 1.0.0  
**Status:** Production Ready  
**Last Updated:** June 12, 2026

---

## Quick Start

### Local Development

```bash
# Clone and setup
git clone https://github.com/reprewindai-dev/mcpapi.git
cd mcpapi
npm install

# Start PostgreSQL and Redis
docker-compose up -d

# Run migrations
npm run migrate:up

# Start runtime
npm run dev

# Run tests
npm test

# Start API server (http://localhost:3000)
npm start
```

### Docker Quick Start

```bash
# Build image
docker build -t mcpapi-runtime:1.0.0 .

# Run container
docker run -d \
  -e DATABASE_URL=postgresql://localhost/mcpapi \
  -e REDIS_URL=redis://localhost:6379 \
  -p 3000:3000 \
  mcpapi-runtime:1.0.0
```

---

## Architecture Decisions

### Database Choice: PostgreSQL

**Why:**
- ACID compliance for identity + policy consistency
- JSON support for flexible metadata
- Proven track record for ledger-like systems
- Full-text search for audit logs
- Replication for HA

**Schema:**
```sql
-- Core tables
CREATE TABLE identities (...)
CREATE TABLE policies (...)
CREATE TABLE trust_scores (...)
CREATE TABLE evidence (...)
CREATE TABLE audit_log (...)

-- Indexes for performance
CREATE INDEX idx_identities_entity_id ON identities(entity_id);
CREATE INDEX idx_policies_policy_id ON policies(policy_id);
CREATE INDEX idx_evidence_pgl_hash ON evidence(pgl_hash);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at);
```

### Cache Choice: Redis

**Why:**
- Sub-millisecond identity lookups
- Rate limiting state (sliding windows)
- Trust score caching (TLL: 5 minutes)
- Session management for approval workflows

**Keys:**
- `identity:{entity_id}` → AgentIdentity (TTL: 1 hour)
- `policy:{policy_id}` → Policy (TTL: 1 hour)
- `trust:{agent_id}` → TrustScore (TTL: 5 minutes)
- `rate_limit:{agent_id}` → counter (TTL: 60s)

### PGL Integration Choice

**Why PGL:**
- Immutable proof of interaction
- Agent birth certificates
- Compliance audit trail
- Non-repudiation

**Flow:**
```
MCPAPI generates evidence
    ↓
Commits to PGL ledger
    ↓
Gets immutable hash
    ↓
Stores hash in local evidence table
```

---

## Deployment Topologies

### Single-Node (Development)

```
┌─────────────────────┐
│   MCPAPI Runtime    │
├─────────────────────┤
│ - Request handler   │
│ - Policy engine     │
│ - Trust engine      │
│ - Evidence gen      │
│ - Audit log         │
└─────────┬───────────┘
          │
    ┌─────┴──────┬──────────┬──────────┐
    │             │          │          │
┌───▼──┐    ┌────▼───┐ ┌────▼───┐ ┌───▼──┐
│ PG   │    │ Redis  │ │  PGL   │ │ MCP  │
│ 5432 │    │ 6379   │ │ ledger │ │srvrs │
└──────┘    └────────┘ └────────┘ └──────┘
```

**Use case:** Local dev, testing, PoC

**Deployment:**
```bash
docker-compose up
```

---

### High-Availability (Production)

```
                    ┌────────────────┐
                    │  Load Balancer │
                    │  (Nginx/HAProxy)│
                    └────────┬────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
     ┌────▼──────┐     ┌────▼──────┐    ┌─────▼─────┐
     │  MCPAPI   │     │  MCPAPI   │    │  MCPAPI   │
     │ Instance1 │     │ Instance2 │    │ Instance3 │
     └────┬──────┘     └────┬──────┘    └─────┬─────┘
          │                  │                  │
          └──────────────────┼──────────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
     ┌────▼──────┐     ┌────▼──────┐    ┌──────▼────┐
     │   PG HA   │     │ Redis HA  │    │  PGL Sync │
     │  Primary  │     │ Cluster   │    │  Endpoint │
     │+ Replicas │     │ + Sentinel│    │           │
     └───────────┘     └───────────┘    └───────────┘
```

**Use case:** Production environments, SLA requirements

**Deployment:** See Kubernetes section below

---

### Edge Deployment (Local Runtime)

```
┌─────────────────────────────────────────┐
│  Local/Edge MCPAPI Runtime              │
├─────────────────────────────────────────┤
│ - In-memory identity cache              │
│ - SQLite (offline policies)             │
│ - Local MCP servers only                │
│ - PGL sync on connectivity              │
└──────────────────┬──────────────────────┘
                   │
              ┌────▼──────┐
              │  SQLite   │
              │ (offline) │
              └───────────┘
```

**Use case:** Edge agents, offline-first scenarios

**Configuration:**
```json
{
  "mode": "local",
  "storage": {
    "type": "sqlite",
    "path": "./local.db"
  },
  "sync": {
    "enabled": true,
    "pgl_endpoint": "https://pgl.example.com"
  }
}
```

---

## Kubernetes Deployment

### Prerequisites

- Kubernetes 1.24+
- Helm 3.0+
- PostgreSQL operator (or managed PostgreSQL)
- Redis operator (or managed Redis)
- Istio (optional, for advanced routing)

### Install via Helm

```bash
# Add Veklom Helm repo
helm repo add veklom https://charts.veklom.io
helm repo update

# Install MCPAPI
helm install mcpapi veklom/mcpapi \
  --namespace mcpapi \
  --create-namespace \
  --values values-prod.yaml
```

### Helm Values (Production)

```yaml
# values-prod.yaml
replicaCount: 3

image:
  repository: mcpapi-runtime
  tag: 1.0.0
  pullPolicy: IfNotPresent

resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "1Gi"
    cpu: "1000m"

postgresql:
  enabled: true
  auth:
    username: mcpapi
    password: <CHANGEME>
  primary:
    persistence:
      size: 20Gi
  metrics:
    enabled: true

redis:
  enabled: true
  auth:
    enabled: true
    password: <CHANGEME>
  master:
    persistence:
      size: 10Gi

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: mcpapi.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: mcpapi-tls
      hosts:
        - mcpapi.example.com

monitoring:
  enabled: true
  prometheus:
    enabled: true
    interval: 30s
  alerts:
    enabled: true
```

### Manual Deployment (If Not Using Helm)

```bash
# 1. Create namespace
kubectl create namespace mcpapi

# 2. Create secrets
kubectl create secret generic mcpapi-secrets \
  --from-literal=database-url=postgresql://... \
  --from-literal=redis-url=redis://... \
  -n mcpapi

# 3. Create ConfigMap
kubectl create configmap mcpapi-config \
  --from-file=config.json \
  -n mcpapi

# 4. Deploy
kubectl apply -f k8s/deployment.yaml -n mcpapi
kubectl apply -f k8s/service.yaml -n mcpapi
kubectl apply -f k8s/ingress.yaml -n mcpapi
kubectl apply -f k8s/hpa.yaml -n mcpapi

# 5. Verify
kubectl get pods -n mcpapi
kubectl logs -f deployment/mcpapi-runtime -n mcpapi
```

### Horizontal Pod Autoscaling

```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: mcpapi-hpa
  namespace: mcpapi
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: mcpapi-runtime
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 30
      - type: Pods
        value: 1
        periodSeconds: 30
      selectPolicy: Max
```

---

## Monitoring & Observability

### Prometheus Metrics

```yaml
# monitoring/prometheus-config.yml
global:
  scrape_interval: 30s
  evaluation_interval: 30s

scrape_configs:
- job_name: 'mcpapi'
  static_configs:
    - targets: ['localhost:3000']
  metrics_path: '/metrics'
```

### Key Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `mcpapi_requests_total` | Counter | status, capability | Total requests processed |
| `mcpapi_request_duration_ms` | Histogram | capability | Request latency |
| `mcpapi_trust_score` | Gauge | agent_id | Agent trust scores |
| `mcpapi_policy_violations_total` | Counter | policy_id | Policy violations |
| `mcpapi_evidence_registered_total` | Counter | - | Evidence committed to PGL |
| `mcpapi_cache_hits_total` | Counter | cache_type | Cache hit rate |
| `mcpapi_active_requests` | Gauge | - | Concurrent requests |

### Grafana Dashboards

**Pre-built dashboards available in `monitoring/dashboards/`:**
- `mcpapi-overview.json` — System health overview
- `mcpapi-requests.json` — Request metrics
- `mcpapi-trust.json` — Trust score trends
- `mcpapi-compliance.json` — Audit & compliance

### Logging

**Log Levels:**
- `ERROR` — Request failures, auth errors
- `WARN` — Policy denials, unusual patterns
- `INFO` — Request accepted, status changes
- `DEBUG` — Full request/response payloads (development only)

**Log Shipping:**
```bash
# Example: ELK Stack
input {
  file {
    path => "/var/log/mcpapi/*.log"
    start_position => "beginning"
    codec => json
  }
}

filter {
  if [type] == "mcpapi-request" {
    mutate {
      add_field => { "[@metadata][index_name]" => "mcpapi-requests" }
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "%{[@metadata][index_name]}-%{+YYYY.MM.dd}"
  }
}
```

### Alerting Rules

```yaml
# monitoring/alert-rules.yaml
groups:
- name: MCPAPI Alerts
  interval: 30s
  rules:
  
  # High error rate
  - alert: HighErrorRate
    expr: |
      (
        rate(mcpapi_requests_total{status="error"}[5m]) /
        rate(mcpapi_requests_total[5m])
      ) > 0.05
    for: 5m
    annotations:
      severity: critical
      summary: "MCPAPI error rate > 5%"
      runbook: "https://runbooks.example.com/mcpapi-high-error-rate"
  
  # High policy violation rate
  - alert: HighPolicyViolationRate
    expr: rate(mcpapi_policy_violations_total[5m]) > 0.1
    for: 5m
    annotations:
      severity: warning
      summary: "Policy violation rate > 0.1/sec"
  
  # Agent trust degradation
  - alert: LowAgentTrust
    expr: mcpapi_trust_score < 30
    for: 10m
    annotations:
      severity: warning
      summary: "Agent {{ $labels.agent_id }} trust score < 30"
  
  # Database connection issues
  - alert: DatabaseConnectionError
    expr: mcpapi_db_connection_errors_total > 5
    for: 2m
    annotations:
      severity: critical
      summary: "Database connection errors detected"
  
  # Slow requests
  - alert: SlowRequests
    expr: |
      histogram_quantile(0.95, rate(mcpapi_request_duration_ms_bucket[5m])) > 5000
    for: 5m
    annotations:
      severity: warning
      summary: "P95 latency > 5 seconds"
```

---

## Runbooks

### Runbook: High Error Rate

**Alert:** `HighErrorRate`

**Steps:**

1. **Check application logs**
   ```bash
   kubectl logs -f deployment/mcpapi-runtime -n mcpapi | grep ERROR
   ```

2. **Identify error type**
   ```bash
   # Query recent errors
   curl http://mcpapi.example.com/debug/recent-errors?limit=100
   ```

3. **Common causes:**
   - Database connection pooling exhausted → Increase `DB_POOL_SIZE`
   - Policy evaluation timeout → Review complex policies
   - Capability endpoint unreachable → Check MCP server health
   - Memory pressure → Scale up resource limits

4. **Resolution:**
   ```bash
   # Option 1: Restart pods
   kubectl rollout restart deployment/mcpapi-runtime -n mcpapi
   
   # Option 2: Scale up
   kubectl patch hpa mcpapi-hpa -p '{"spec":{"minReplicas":5}}' -n mcpapi
   
   # Option 3: Roll back
   kubectl rollout undo deployment/mcpapi-runtime -n mcpapi
   ```

5. **Verify**
   ```bash
   # Check error rate dropped
   curl http://prometheus:9090/api/v1/query?query=rate(mcpapi_requests_total{status=\"error\"}[5m])
   ```

---

### Runbook: Database Connection Issues

**Alert:** `DatabaseConnectionError`

**Steps:**

1. **Check database connectivity**
   ```bash
   # Test from pod
   kubectl exec -it pod/mcpapi-runtime-xxx -n mcpapi -- \
     psql -h pg.mcpapi.svc -U mcpapi -d mcpapi
   ```

2. **Check connection pool status**
   ```bash
   curl http://mcpapi.example.com/debug/db-pool
   ```

3. **Increase pool size (if needed)**
   ```yaml
   # Update deployment
   env:
   - name: DB_POOL_SIZE
     value: "50"  # increase from 20
   ```

4. **Restart affected pods**
   ```bash
   kubectl rollout restart deployment/mcpapi-runtime -n mcpapi
   ```

5. **Monitor recovery**
   ```bash
   kubectl logs -f deployment/mcpapi-runtime -n mcpapi | grep "pool"
   ```

---

### Runbook: Low Agent Trust Score

**Alert:** `LowAgentTrust`

**Steps:**

1. **Identify affected agent**
   ```bash
   # Get agent details from alert
   AGENT_ID=$(alert.labels.agent_id)
   curl http://mcpapi.example.com/agents/$AGENT_ID
   ```

2. **Review recent denials**
   ```bash
   curl http://mcpapi.example.com/audit/log?agent_id=$AGENT_ID&status=denied
   ```

3. **Analyze pattern**
   ```bash
   # Check if policy changed
   curl http://mcpapi.example.com/policies
   
   # Check if agent behavior changed
   curl http://mcpapi.example.com/audit/log?agent_id=$AGENT_ID&limit=50
   ```

4. **Take action**
   - If legitimate: Approve requests via governance API
   - If compromised: Suspend agent + rotate keys
   - If misconfigured: Update policy + re-enable

5. **Restore trust (if appropriate)**
   ```bash
   curl -X POST http://mcpapi.example.com/trust/$AGENT_ID/restore \
     -H "X-Commander-Id: agent-000" \
     -d '{"reason": "policy-change-approved"}'
   ```

---

### Runbook: PGL Ledger Sync Failure

**Alert:** `PGLSyncError`

**Steps:**

1. **Check PGL connectivity**
   ```bash
   curl https://pgl.example.com/health
   ```

2. **Check unsync'd evidence backlog**
   ```bash
   curl http://mcpapi.example.com/debug/pending-evidence
   ```

3. **If PGL is down:**
   - MCPAPI continues processing (evidence stored locally)
   - Automatic sync retry every 30 seconds
   - Monitor `mcpapi_pgl_sync_pending` metric

4. **If persistent:**
   - Check PGL server logs
   - Verify network connectivity
   - Escalate to PGL ops team

5. **Recovery**
   ```bash
   # Manual sync when PGL recovers
   curl -X POST http://mcpapi.example.com/admin/sync-pending
   ```

---

## Backup & Disaster Recovery

### Backup Strategy

**Daily backup schedule:**
```bash
# Database backup
pg_dump mcpapi > backup-$(date +%Y%m%d-%H%M%S).sql.gz

# S3 replication
aws s3 cp backup-*.sql.gz s3://mcpapi-backups/

# Retention: 30 days
aws s3api delete-object --bucket mcpapi-backups --key <30-day-old-backup>
```

### Recovery Procedure

```bash
# 1. Stop MCPAPI
kubectl scale deployment mcpapi-runtime --replicas=0 -n mcpapi

# 2. Restore database
psql mcpapi < backup-20260612-120000.sql

# 3. Verify integrity
psql -c "SELECT COUNT(*) FROM evidence;"
psql -c "SELECT COUNT(*) FROM audit_log;"

# 4. Restart MCPAPI
kubectl scale deployment mcpapi-runtime --replicas=3 -n mcpapi

# 5. Verify connectivity
curl http://mcpapi.example.com/health
```

---

## Security Hardening

### Network Policies

```yaml
# k8s/network-policies.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: mcpapi-netpol
  namespace: mcpapi
spec:
  podSelector:
    matchLabels:
      app: mcpapi
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 3000
  egress:
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: TCP
      port: 5432  # PostgreSQL
    - protocol: TCP
      port: 6379  # Redis
  - to:
    - podSelector: {}
    ports:
    - protocol: TCP
      port: 443   # HTTPS for PGL
```

### RBAC

```yaml
# k8s/rbac.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: mcpapi
  namespace: mcpapi
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: mcpapi-role
  namespace: mcpapi
rules:
- apiGroups: [""]
  resources: ["configmaps"]
  verbs: ["get", "watch", "list"]
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["get"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: mcpapi-rolebinding
  namespace: mcpapi
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: mcpapi-role
subjects:
- kind: ServiceAccount
  name: mcpapi
  namespace: mcpapi
```

### TLS/mTLS

```yaml
# k8s/cert-manager.yaml
apiVersion: cert-manager.io/v1
kind: Issuer
metadata:
  name: letsencrypt-prod
  namespace: mcpapi
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: ops@veklom.io
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
```

---

## Performance Tuning

### Database Optimization

```sql
-- Connection pooling
-- Use PgBouncer or built-in pool manager
-- Min: 10, Max: 50 per MCPAPI instance

-- Index optimization
CREATE INDEX CONCURRENTLY idx_evidence_agent_created 
  ON evidence(agent_id, created_at DESC);

CREATE INDEX CONCURRENTLY idx_audit_log_capability_created 
  ON audit_log(capability_id, created_at DESC);

-- Query optimization
ANALYZE identities;
ANALYZE policies;
ANALYZE evidence;
ANALYZE audit_log;

-- Statistics
SELECT schemaname, tablename, 
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Redis Optimization

```bash
# Memory usage
redis-cli INFO memory

# Eviction policy (if memory-constrained)
redis-cli CONFIG SET maxmemory-policy allkeys-lru

# Persistence (balance durability vs performance)
redis-cli CONFIG SET save "900 1 300 10 60 10000"
```

### Request Processing Optimization

| Step | Target | Current | Optimization |
|------|--------|---------|--------------|
| Identity resolve | < 5ms | 8ms | Cache in Redis (TTL: 1h) |
| Policy evaluate | < 10ms | 15ms | Compile policies to bytecode |
| Trust compute | < 2ms | 3ms | Cache scores (TTL: 5m) |
| Capability route | < 100ms | 120ms | Connection pooling to MCP |
| Evidence gen | < 5ms | 6ms | Pre-allocate buffers |

---

## Compliance & Audit

### Data Retention Policy

| Data Type | Retention | Location |
|-----------|-----------|----------|
| Audit logs | 1 year | PostgreSQL + S3 archive |
| Evidence | 7 years | PGL ledger (immutable) |
| Policy changes | 7 years | PostgreSQL |
| Trust scores | 90 days | PostgreSQL (historical snapshots) |

### Export for Compliance

```bash
# Monthly compliance export
curl -X POST http://mcpapi.example.com/admin/export \
  -d '{
    "start_date": "2026-06-01",
    "end_date": "2026-06-30",
    "data_types": ["audit_log", "evidence", "policy_changes"],
    "format": "csv"
  }' \
  -o compliance-report-2026-06.csv
```

---

## Scaling Considerations

### Vertical Scaling

Increase resources per pod:
```yaml
resources:
  limits:
    memory: "2Gi"    # up from 1Gi
    cpu: "2000m"     # up from 1000m
```

### Horizontal Scaling

Increase replica count:
```bash
kubectl scale deployment mcpapi-runtime --replicas=10 -n mcpapi
```

### Throughput Estimates

| Component | Capacity | Limiting Factor |
|-----------|----------|-----------------|
| Single pod | 1000 req/s | CPU + memory |
| 3-pod cluster | 3000 req/s | Network |
| 10-pod cluster | 10000 req/s | Database |
| Max cluster | 50000 req/s | PGL ledger sync |

---

## Incident Response

### Classification

| Severity | SLA | Response |
|----------|-----|----------|
| P1 (Critical) | 15 min | On-call + escalate |
| P2 (High) | 1 hour | On-call response |
| P3 (Medium) | 4 hours | Next business day |
| P4 (Low) | 24 hours | Backlog |

### Incident Response Plan

1. **Detect** → Alert fires
2. **Alert** → Notify on-call
3. **Assess** → Determine severity
4. **Respond** → Follow runbook
5. **Recover** → Restore service
6. **Document** → Post-mortem
7. **Improve** → Update runbooks

---

## Support & Resources

- **Documentation:** https://docs.mcpapi.io
- **GitHub:** https://github.com/reprewindai-dev/mcpapi
- **Issues:** https://github.com/reprewindai-dev/mcpapi/issues
- **Slack:** #mcpapi-ops
- **On-call:** oncall@veklom.io

