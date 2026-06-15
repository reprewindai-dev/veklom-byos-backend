# MCPAPI v2.0 Production Deployment Package

**Version:** 2.0.0  
**Status:** Production Ready  
**Date:** June 12, 2026

---

## Docker Setup

### Dockerfile (Multi-stage)

```dockerfile
# Stage 1: Builder
FROM node:18-alpine AS builder

WORKDIR /build

COPY package*.json ./
RUN npm install --production

COPY tsconfig.json ./
COPY src/ ./src/

RUN npm run build

# Stage 2: Runtime
FROM node:18-alpine

WORKDIR /app

# Copy runtime dependencies only
COPY --from=builder /build/node_modules ./node_modules
COPY --from=builder /build/dist ./dist
COPY package*.json ./

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3000/health', (r) => {if (r.statusCode !== 200) throw new Error(r.statusCode)})"

EXPOSE 3000

ENV NODE_ENV=production
ENV LOG_LEVEL=info

CMD ["node", "dist/server.js"]
```

### docker-compose.yml (Development)

```yaml
version: '3.8'

services:
  mcpapi:
    build: .
    ports:
      - "3000:3000"
    environment:
      DATABASE_URL: postgresql://mcpapi:mcpapi@postgres:5432/mcpapi
      REDIS_URL: redis://redis:6379
      PGL_ENDPOINT: http://pgl:4000
      VEKLOM_ENDPOINT: http://veklom:5000
      LOG_LEVEL: debug
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - mcpapi-network

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: mcpapi
      POSTGRES_PASSWORD: mcpapi
      POSTGRES_DB: mcpapi
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./migrations:/docker-entrypoint-initdb.d
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U mcpapi"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - mcpapi-network

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - mcpapi-network

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    networks:
      - mcpapi-network

  grafana:
    image: grafana/grafana:latest
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana:/etc/grafana/provisioning
    ports:
      - "3001:3000"
    depends_on:
      - prometheus
    networks:
      - mcpapi-network

volumes:
  postgres_data:
  redis_data:
  prometheus_data:
  grafana_data:

networks:
  mcpapi-network:
    driver: bridge
```

---

## Kubernetes Manifests

### namespace.yaml

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: mcpapi
  labels:
    name: mcpapi
```

### ConfigMap (Configuration)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mcpapi-config
  namespace: mcpapi
data:
  LOG_LEVEL: "info"
  LOG_FORMAT: "json"
  MCPAPI_WORKERS: "4"
  ANOMALY_THRESHOLD: "2.0"
  BASELINE_LOCK_DAYS: "30"
  MAX_DELEGATION_DEPTH: "3"
  APPROVAL_QUORUM_SIZE: "2"
  QUARANTINE_HOLD_DURATION_HOURS: "1"
  PGL_ENDPOINT: "https://pgl.example.com/api"
  VEKLOM_ENDPOINT: "https://veklom.example.com/api"
```

### Secrets (Sensitive Data)

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: mcpapi-secrets
  namespace: mcpapi
type: Opaque
stringData:
  DATABASE_URL: "postgresql://mcpapi:PASSWORD@postgres.mcpapi.svc.cluster.local:5432/mcpapi"
  REDIS_URL: "redis://redis.mcpapi.svc.cluster.local:6379"
  PGL_API_KEY: "secret-pgl-key"
  VEKLOM_API_KEY: "secret-veklom-key"
  ENCRYPTION_KEY: "base64-encoded-32-byte-key"
  JWT_SECRET: "secret-jwt-signing-key"
```

### PostgreSQL StatefulSet

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: mcpapi
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15-alpine
        ports:
        - containerPort: 5432
          name: postgres
        env:
        - name: POSTGRES_USER
          value: mcpapi
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mcpapi-secrets
              key: POSTGRES_PASSWORD
        - name: POSTGRES_DB
          value: mcpapi
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
        livenessProbe:
          exec:
            command:
            - /bin/sh
            - -c
            - pg_isready -U mcpapi
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - /bin/sh
            - -c
            - pg_isready -U mcpapi
          initialDelaySeconds: 5
          periodSeconds: 5
      volumeClaimTemplates:
      - metadata:
          name: postgres-storage
        spec:
          accessModes: ["ReadWriteOnce"]
          resources:
            requests:
              storage: 50Gi
---
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: mcpapi
spec:
  clusterIP: None
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
```

### Redis StatefulSet

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis
  namespace: mcpapi
spec:
  serviceName: redis
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
          name: redis
        command:
          - redis-server
          - /etc/redis/redis.conf
        volumeMounts:
        - name: redis-data
          mountPath: /data
        - name: redis-config
          mountPath: /etc/redis
        livenessProbe:
          exec:
            command:
            - redis-cli
            - ping
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - redis-cli
            - ping
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: redis-config
        configMap:
          name: redis-config
      volumeClaimTemplates:
      - metadata:
          name: redis-data
        spec:
          accessModes: ["ReadWriteOnce"]
          resources:
            requests:
              storage: 20Gi
---
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: mcpapi
spec:
  clusterIP: None
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379
```

### MCPAPI Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcpapi-runtime
  namespace: mcpapi
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: mcpapi
  template:
    metadata:
      labels:
        app: mcpapi
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "3000"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: mcpapi
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - mcpapi
              topologyKey: kubernetes.io/hostname
      containers:
      - name: mcpapi
        image: mcpapi-runtime:2.0.0
        imagePullPolicy: IfNotPresent
        ports:
        - name: http
          containerPort: 3000
          protocol: TCP
        - name: metrics
          containerPort: 3001
          protocol: TCP
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: mcpapi-secrets
              key: DATABASE_URL
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: mcpapi-secrets
              key: REDIS_URL
        - name: PGL_ENDPOINT
          valueFrom:
            configMapKeyRef:
              name: mcpapi-config
              key: PGL_ENDPOINT
        - name: LOG_LEVEL
          valueFrom:
            configMapKeyRef:
              name: mcpapi-config
              key: LOG_LEVEL
        - name: MCPAPI_WORKERS
          valueFrom:
            configMapKeyRef:
              name: mcpapi-config
              key: MCPAPI_WORKERS
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: http
          initialDelaySeconds: 10
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: http
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 2
        volumeMounts:
        - name: tmp
          mountPath: /tmp
      volumes:
      - name: tmp
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: mcpapi-service
  namespace: mcpapi
spec:
  type: ClusterIP
  selector:
    app: mcpapi
  ports:
  - name: http
    port: 80
    targetPort: http
    protocol: TCP
  - name: metrics
    port: 3001
    targetPort: metrics
    protocol: TCP
---
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
```

### Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: mcpapi-ingress
  namespace: mcpapi
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "1000"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - mcpapi.example.com
    secretName: mcpapi-tls
  rules:
  - host: mcpapi.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: mcpapi-service
            port:
              number: 80
```

### RBAC

```yaml
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
  verbs: ["get", "list", "watch"]
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["get"]
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list"]
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

### Network Policies

```yaml
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
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: TCP
      port: 443
    - protocol: TCP
      port: 53
    - protocol: UDP
      port: 53
```

---

## Monitoring Setup

### Prometheus Configuration

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 30s
  evaluation_interval: 30s
  external_labels:
    cluster: mcpapi-prod
    environment: production

scrape_configs:
- job_name: 'mcpapi'
  static_configs:
  - targets: ['localhost:3000']
  metrics_path: '/metrics'

- job_name: 'postgres'
  static_configs:
  - targets: ['localhost:9187']

- job_name: 'redis'
  static_configs:
  - targets: ['localhost:9121']

- job_name: 'kubernetes'
  kubernetes_sd_configs:
  - role: pod
    namespaces:
      names:
      - mcpapi
  relabel_configs:
  - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
    action: keep
    regex: true
  - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
    action: replace
    target_label: __metrics_path__
    regex: (.+)
  - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
    action: replace
    regex: ([^:]+)(?::\d+)?;(\d+)
    replacement: $1:$2
    target_label: __address__
```

### Alert Rules

```yaml
# monitoring/alerts.yaml
groups:
- name: MCPAPI Alerts
  interval: 30s
  rules:

  # High error rate
  - alert: MCPAPIHighErrorRate
    expr: |
      (
        rate(mcpapi_requests_total{status="error"}[5m]) /
        rate(mcpapi_requests_total[5m])
      ) > 0.05
    for: 5m
    labels:
      severity: critical
      team: platform
    annotations:
      summary: "MCPAPI error rate > 5%"
      description: "Error rate: {{ $value | humanizePercentage }}"
      runbook: "https://docs.example.com/runbooks/mcpapi-high-error-rate"

  # High anomaly detection rate
  - alert: MCPAPIHighAnomalyRate
    expr: rate(mcpapi_anomalies_total[5m]) > 0.1
    for: 5m
    labels:
      severity: warning
      team: security
    annotations:
      summary: "MCPAPI anomaly detection rate > 0.1/sec"
      description: "Anomaly rate: {{ $value }}"

  # Agent trust degradation
  - alert: MCPAPILowAgentTrust
    expr: mcpapi_trust_score < 30
    for: 10m
    labels:
      severity: warning
      team: security
    annotations:
      summary: "Agent trust score < 30"
      description: "Agent {{ $labels.agent_id }} trust: {{ $value }}"

  # Database connection pool exhaustion
  - alert: MCPAPIDBPoolExhausted
    expr: mcpapi_db_pool_active / mcpapi_db_pool_size > 0.9
    for: 2m
    labels:
      severity: critical
      team: platform
    annotations:
      summary: "Database connection pool >90% utilized"
      description: "Pool utilization: {{ $value | humanizePercentage }}"

  # PGL sync backlog
  - alert: MCPAPIPGLSyncBacklog
    expr: mcpapi_pgl_sync_pending > 100
    for: 5m
    labels:
      severity: warning
      team: platform
    annotations:
      summary: "PGL sync backlog > 100 entries"
      description: "Pending: {{ $value }}"

  # High request latency
  - alert: MCPAPIHighLatency
    expr: histogram_quantile(0.95, rate(mcpapi_request_duration_ms_bucket[5m])) > 500
    for: 5m
    labels:
      severity: warning
      team: platform
    annotations:
      summary: "MCPAPI P95 latency > 500ms"
      description: "P95 latency: {{ $value }}ms"

  # Risk profile RED
  - alert: MCPAPIHighRiskAgent
    expr: mcpapi_risk_score > 75
    for: 5m
    labels:
      severity: critical
      team: security
    annotations:
      summary: "Agent at high risk (score > 75)"
      description: "Agent {{ $labels.agent_id }} risk: {{ $value }}"

  # Approval queue overdue
  - alert: MCPAPIApprovalQueueOverdue
    expr: mcpapi_approval_queue_overdue > 0
    for: 1m
    labels:
      severity: critical
      team: platform
    annotations:
      summary: "Approval queue has overdue items"
      description: "Overdue approvals: {{ $value }}"
```

### Grafana Dashboard JSON

```json
{
  "dashboard": {
    "title": "MCPAPI v2.0 Overview",
    "panels": [
      {
        "title": "Requests/sec",
        "targets": [
          {
            "expr": "rate(mcpapi_requests_total[1m])"
          }
        ]
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "rate(mcpapi_requests_total{status=\"error\"}[1m]) / rate(mcpapi_requests_total[1m])"
          }
        ]
      },
      {
        "title": "P95 Latency (ms)",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(mcpapi_request_duration_ms_bucket[5m]))"
          }
        ]
      },
      {
        "title": "Anomalies Detected",
        "targets": [
          {
            "expr": "rate(mcpapi_anomalies_total[5m])"
          }
        ]
      },
      {
        "title": "Risk Score Distribution",
        "targets": [
          {
            "expr": "mcpapi_risk_score"
          }
        ]
      },
      {
        "title": "Cost Attribution (Daily)",
        "targets": [
          {
            "expr": "sum(mcpapi_cost_attributed) by (agent_id)"
          }
        ]
      },
      {
        "title": "Active Agents by Trust Level",
        "targets": [
          {
            "expr": "count(mcpapi_trust_score > 80)",
            "legendFormat": "High (>80)"
          },
          {
            "expr": "count((mcpapi_trust_score >= 60) and (mcpapi_trust_score <= 80))",
            "legendFormat": "Medium (60-80)"
          },
          {
            "expr": "count(mcpapi_trust_score < 60)",
            "legendFormat": "Low (<60)"
          }
        ]
      },
      {
        "title": "PGL Sync Status",
        "targets": [
          {
            "expr": "mcpapi_pgl_sync_pending"
          }
        ]
      },
      {
        "title": "Database Connection Pool",
        "targets": [
          {
            "expr": "mcpapi_db_pool_active",
            "legendFormat": "Active"
          },
          {
            "expr": "mcpapi_db_pool_size",
            "legendFormat": "Total"
          }
        ]
      },
      {
        "title": "Approval Queue",
        "targets": [
          {
            "expr": "mcpapi_approval_queue_pending",
            "legendFormat": "Pending"
          },
          {
            "expr": "mcpapi_approval_queue_approved",
            "legendFormat": "Approved"
          },
          {
            "expr": "mcpapi_approval_queue_denied",
            "legendFormat": "Denied"
          }
        ]
      }
    ]
  }
}
```

---

## Database Migrations

### 001_initial_schema.sql

```sql
-- Identity tables
CREATE TABLE identities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_type VARCHAR(20) NOT NULL, -- 'agent' or 'capability'
  entity_id VARCHAR(255) UNIQUE NOT NULL,
  owner_id VARCHAR(255),
  public_key TEXT,
  metadata JSONB,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_identities_entity_id ON identities(entity_id);
CREATE INDEX idx_identities_owner_id ON identities(owner_id);

-- Policy tables
CREATE TABLE policies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  policy_id VARCHAR(255) UNIQUE NOT NULL,
  policy_name VARCHAR(255),
  version VARCHAR(20),
  rules JSONB,
  metadata JSONB,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_policies_policy_id ON policies(policy_id);

-- Trust scores
CREATE TABLE trust_scores (
  agent_id VARCHAR(255) PRIMARY KEY,
  score FLOAT DEFAULT 50,
  success_rate FLOAT DEFAULT 1.0,
  policy_adherence FLOAT DEFAULT 1.0,
  denial_frequency FLOAT DEFAULT 0,
  escalation_events FLOAT DEFAULT 0,
  last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_trust_scores_score ON trust_scores(score);

-- Evidence/audit log
CREATE TABLE evidence (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  evidence_id VARCHAR(255) UNIQUE NOT NULL,
  connection_id VARCHAR(255),
  pgl_hash VARCHAR(255),
  agent_id VARCHAR(255),
  capability_id VARCHAR(255),
  status VARCHAR(20),
  result_hash VARCHAR(255),
  previous_hash VARCHAR(255),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_evidence_pgl_hash ON evidence(pgl_hash);
CREATE INDEX idx_evidence_agent_id ON evidence(agent_id);
CREATE INDEX idx_evidence_created_at ON evidence(created_at DESC);

-- Audit log
CREATE TABLE audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  connection_id VARCHAR(255),
  agent_id VARCHAR(255),
  capability_id VARCHAR(255),
  action VARCHAR(255),
  decision VARCHAR(20),
  evidence_hash VARCHAR(255),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_log_agent_id ON audit_log(agent_id);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at DESC);

-- Anomalies
CREATE TABLE anomalies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  detection_id VARCHAR(255) UNIQUE,
  agent_id VARCHAR(255),
  anomaly_type VARCHAR(50),
  severity VARCHAR(20),
  detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_anomalies_agent_id ON anomalies(agent_id);
CREATE INDEX idx_anomalies_detected_at ON anomalies(detected_at DESC);

-- Cost tracking
CREATE TABLE cost_attribution (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id VARCHAR(255),
  capability_id VARCHAR(255),
  cost FLOAT,
  currency VARCHAR(20),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cost_agent_capability ON cost_attribution(agent_id, capability_id);
CREATE INDEX idx_cost_created_at ON cost_attribution(created_at DESC);
```

---

## Build & Deploy Script

```bash
#!/bin/bash

set -e

REGISTRY="docker.io"
REPO="mcpapi"
VERSION="2.0.0"
IMAGE="$REGISTRY/$REPO/mcpapi-runtime:$VERSION"

echo "Building MCPAPI v$VERSION..."

# Build Docker image
docker build \
  --target runtime \
  -t "$IMAGE" \
  -f Dockerfile .

echo "Pushing to registry..."
docker push "$IMAGE"

echo "Deploying to Kubernetes..."

# Create namespace
kubectl create namespace mcpapi --dry-run=client -o yaml | kubectl apply -f -

# Apply configs
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/rbac.yaml
kubectl apply -f k8s/network-policy.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/hpa.yaml

# Wait for rollout
kubectl rollout status deployment/mcpapi-runtime -n mcpapi --timeout=5m

echo "Deployment complete!"
echo "MCPAPI v$VERSION is running at https://mcpapi.example.com"
```

---

## Health Check Script

```bash
#!/bin/bash

# Health check endpoints
HEALTH_ENDPOINT="http://localhost:3000/health"
READY_ENDPOINT="http://localhost:3000/ready"
METRICS_ENDPOINT="http://localhost:3000/metrics"

echo "Checking MCPAPI v2.0 health..."

# Health check
echo -n "Health: "
HEALTH=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_ENDPOINT)
if [ "$HEALTH" = "200" ]; then
  echo "✓ OK"
else
  echo "✗ FAILED ($HEALTH)"
  exit 1
fi

# Readiness check
echo -n "Readiness: "
READY=$(curl -s -o /dev/null -w "%{http_code}" $READY_ENDPOINT)
if [ "$READY" = "200" ]; then
  echo "✓ OK"
else
  echo "✗ NOT READY ($READY)"
  exit 1
fi

# Metrics check
echo -n "Metrics: "
METRICS=$(curl -s $METRICS_ENDPOINT | grep mcpapi_requests_total | head -1)
if [ -n "$METRICS" ]; then
  echo "✓ OK"
  echo ""
  echo "Sample metrics:"
  curl -s $METRICS_ENDPOINT | grep mcpapi_ | head -10
else
  echo "✗ NO METRICS"
  exit 1
fi

echo ""
echo "All checks passed! MCPAPI v2.0 is healthy."
```

---

## Backup Strategy

```bash
#!/bin/bash

# Daily backup script
BACKUP_DIR="/backups/mcpapi"
RETENTION_DAYS=30
DATE=$(date +%Y%m%d-%H%M%S)

mkdir -p $BACKUP_DIR

echo "Starting MCPAPI backup at $DATE..."

# PostgreSQL backup
echo "Backing up PostgreSQL..."
pg_dump \
  -h postgres.mcpapi.svc.cluster.local \
  -U mcpapi \
  mcpapi | gzip > $BACKUP_DIR/db-$DATE.sql.gz

# Upload to S3
echo "Uploading to S3..."
aws s3 cp $BACKUP_DIR/db-$DATE.sql.gz s3://mcpapi-backups/ --sse AES256

# Cleanup old backups (>30 days)
echo "Cleaning old backups..."
find $BACKUP_DIR -name "db-*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup complete: $BACKUP_DIR/db-$DATE.sql.gz"
```

---

## Incident Response Runbook

### Runbook 1: High Error Rate

**Alert:** MCPAPIHighErrorRate

```
1. Assess severity
   - Check error rate: > 10% is critical
   - Check error types (logs)
   
2. Immediate actions
   - Page on-call engineer
   - Slack #mcpapi-incidents
   - Start bridge (Zoom/Google Meet)
   
3. Investigation
   kubectl logs -f deployment/mcpapi-runtime -n mcpapi | grep ERROR
   
4. Possible causes
   - Database connection pool exhausted
   - PGL sync failure
   - Capability endpoint unreachable
   - Memory pressure
   
5. Remediation
   a) If DB pool exhausted:
      kubectl patch configmap mcpapi-config -n mcpapi \
        -p '{"data":{"DB_POOL_SIZE":"50"}}'
      kubectl rollout restart deployment/mcpapi-runtime -n mcpapi
   
   b) If PGL down:
      Check PGL status
      Verify network connectivity
      Evidence stored locally, will sync when available
   
   c) If memory pressure:
      kubectl patch deployment mcpapi-runtime -n mcpapi \
        -p '{"spec":{"template":{"spec":{"containers":[{"name":"mcpapi","resources":{"limits":{"memory":"2Gi"}}}]}}}}'
   
   d) If capability unreachable:
      Debug endpoint
      Check MCP server health
      Update endpoint if changed
   
6. Verification
   - Error rate drops
   - Response latency returns to normal
   - PGL sync catches up
   
7. Post-mortem
   - Document root cause
   - Create ticket for prevention
   - Update runbook if needed
```

### Runbook 2: Agent Compromise Suspected

**Alert:** MCPAPIHighRiskAgent or MCPAPIHighAnomalyRate

```
1. Immediate containment
   - Deactivate agent immediately
   - Revoke all API keys
   - Notify agent owner
   
2. Investigation
   - Review recent requests (last 24 hours)
   - Check anomaly details
   - Review cost attribution
   - Check behavioral patterns
   
3. Forensics
   kubectl get pods -n mcpapi
   kubectl logs mcpapi-runtime-xxx -n mcpapi > /tmp/logs.txt
   
   # Query evidence
   psql -h postgres -U mcpapi -d mcpapi
   SELECT * FROM evidence 
   WHERE agent_id = 'agent-xxx' 
   ORDER BY created_at DESC 
   LIMIT 50;
   
4. Damage assessment
   - Which capabilities were accessed?
   - What data was accessed?
   - Were delegations created?
   
5. Remediation
   - Revoke all delegations
   - Reset credentials
   - Review all linked agents
   - Patch vulnerability
   
6. Recovery
   - If agent is legitimate:
     - Reset its keys
     - Reset trust score to 50
     - Re-enable with restrictions
   - If agent is malicious:
     - Delete agent
     - Archive for 7 years
     - Notify security team
   
7. Prevent recurrence
   - Investigate attack vector
   - Add detection for pattern
   - Brief team on lessons learned
```

---

## Deployment Checklist

- [ ] PostgreSQL configured + backed up
- [ ] Redis configured + cluster set up
- [ ] Kubernetes cluster created (≥3 nodes)
- [ ] Secrets created (DB, Redis, API keys)
- [ ] Configs created (log levels, thresholds)
- [ ] RBAC configured
- [ ] Network policies created
- [ ] Ingress/TLS configured
- [ ] Prometheus + Grafana deployed
- [ ] Alert rules configured
- [ ] Health checks passing
- [ ] Load testing passed (1000 req/s)
- [ ] Security audit completed
- [ ] Runbooks documented
- [ ] On-call schedule set up
- [ ] Monitoring dashboards ready
- [ ] Backup strategy tested
- [ ] Disaster recovery tested
- [ ] Team trained
- [ ] Go-live approved

---

## Success Criteria (Week 8)

- [ ] 0 security incidents
- [ ] <1% error rate
- [ ] P95 latency <150ms (excl. capability)
- [ ] 3-5 design partners live
- [ ] 100% uptime (SLA met)
- [ ] 1000 req/s sustained
- [ ] All PGL evidence committed successfully
- [ ] Documentation complete + tested

