# 🚂 Veklom Interactive Pipeline System

> Railway-style interactive deployment pipeline for the Veklom Sovereign AI Hub.
> Visual, interactive, real-time — just like Railway.

---

## 1. Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    VEKLOM DEPLOYMENT PIPELINE                          │
│                    ═══════════════════════════════                      │
│                                                                         │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐            │
│  │  SOURCE   │──▶│  BUILD   │──▶│   TEST   │──▶│  STAGE   │            │
│  │          │   │          │   │          │   │          │            │
│  │ git push │   │ docker   │   │ pytest   │   │ canary   │            │
│  │ webhook  │   │ compile  │   │ lint     │   │ 10%      │            │
│  │ PR merge │   │ bundle   │   │ security │   │ traffic  │            │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘            │
│       │              │              │              │                    │
│       ▼              ▼              ▼              ▼                    │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐            │
│  │ VALIDATE │   │ SCAN     │   │ GATE     │   │ PROMOTE  │            │
│  │          │   │          │   │          │   │          │            │
│  │ schema   │   │ trivy    │   │ council  │   │ blue/grn │            │
│  │ lint     │   │ sbom     │   │ vote     │   │ 100%     │            │
│  │ types    │   │ deps     │   │ approve  │   │ traffic  │            │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘            │
│                                                      │                 │
│                                                      ▼                 │
│                                                 ┌──────────┐          │
│                                                 │  DEPLOY   │          │
│                                                 │          │          │
│                                                 │ prod     │          │
│                                                 │ monitor  │          │
│                                                 │ rollback │          │
│                                                 └──────────┘          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Pipeline Stages (Railway-Interactive)

### Stage 1: SOURCE — Trigger Detection

```yaml
trigger:
  events:
    - push:
        branches: [main, dev, release/*]
    - pull_request:
        branches: [main]
    - webhook:
        path: /api/v1/webhooks/pipeline/trigger
    - manual:
        path: /api/v1/pipelines/{id}/execute
    - schedule:
        cron: "0 2 * * *"  # nightly builds

  interactive:
    # Railway-style: click to deploy from dashboard
    dashboard_trigger: true
    slack_trigger: true
    api_trigger: true
    
  context:
    commit_sha: ${{ github.sha }}
    branch: ${{ github.ref_name }}
    actor: ${{ github.actor }}
    workspace_id: ${{ workspace.id }}
```

### Stage 2: BUILD — Compile & Bundle

```yaml
build:
  parallel: true
  
  steps:
    - name: backend-build
      image: python:3.11-slim
      commands:
        - pip install -e ".[dev]"
        - python -m compileall -q backend/
        - alembic check  # verify migrations are current
      artifacts:
        - backend/dist/
        - backend/.compiled/
      
    - name: frontend-build
      image: node:20-alpine
      working_dir: frontend/workspace
      commands:
        - npm ci
        - npm run typecheck
        - npm run build
      artifacts:
        - frontend/workspace/dist/
        
    - name: docker-build
      image: docker:24
      commands:
        - docker build -f backend/infra/docker/Dockerfile.api -t veklom/api:$SHA .
        - docker build -f backend/infra/docker/Dockerfile.worker -t veklom/worker:$SHA .
      cache:
        key: docker-layers-${{ hashFiles('backend/pyproject.toml') }}
        paths: [/var/lib/docker/overlay2]

  interactive:
    # Railway-style: live build logs streaming in dashboard
    log_stream: true
    build_cache_indicator: true
    artifact_browser: true
    cancel_button: true
```

### Stage 3: VALIDATE — Quality Gates

```yaml
validate:
  parallel: true
  fail_fast: false  # run all checks even if one fails
  
  steps:
    - name: lint
      commands:
        - ruff check --select E9,F63,F7,F82 backend/
        - ruff format --check backend/
      severity: blocking
      
    - name: typecheck
      commands:
        - cd frontend/workspace && npm run typecheck
        - python -m compileall -q backend/
      severity: blocking
      
    - name: security-scan
      commands:
        - trivy image veklom/api:$SHA --severity HIGH,CRITICAL
        - python backend/scripts/audit_route_security.py
        - rg -l "sk_live_|password=" --type py backend/ && exit 1 || true
      severity: blocking
      
    - name: dependency-audit
      commands:
        - pip-audit --strict
        - npm audit --audit-level=high
      severity: warning
      
    - name: sbom-generate
      commands:
        - syft veklom/api:$SHA -o spdx-json > sbom.json
      severity: info
      
    - name: license-check
      commands:
        - python backend/scripts/verify_com_landing_freeze.py
      severity: blocking

  interactive:
    # Railway-style: expandable check results in dashboard
    check_badges: true
    inline_error_viewer: true
    re_run_button: true
    bypass_with_approval: true  # council member can override
```

### Stage 4: TEST — Automated Test Suite

```yaml
test:
  parallel: true
  
  environment:
    DATABASE_URL: sqlite:///./ci-test.db
    SECRET_KEY: test-secret-key-ci
    STRIPE_SECRET_KEY: sk_test_placeholder
    LICENSE_ADMIN_TOKEN: test-admin-token
    REDIS_URL: redis://localhost:6379/0
    
  services:
    - redis:7-alpine
    
  steps:
    - name: unit-tests
      commands:
        - cd backend && pytest tests/ --tb=short -q -x
      coverage:
        threshold: 60
        report: coverage.xml
      severity: blocking
      
    - name: contract-tests
      commands:
        - cd backend && pytest tests/test_edge_demo_contract.py tests/test_edge_demo_routes.py tests/test_middleware_edges.py -q
      severity: blocking
      
    - name: integration-tests
      commands:
        - cd backend && pytest tests/test_route_security_audit.py tests/test_buyer_package.py tests/test_license_health.py -q
      severity: blocking
      
    - name: load-test
      commands:
        - cd backend && python stress_test.py --duration 30 --users 50
      severity: warning
      thresholds:
        p95_latency_ms: 500
        error_rate_percent: 1
        
    - name: e2e-smoke
      commands:
        - cd backend && python test_endpoints.py
      severity: warning

  interactive:
    # Railway-style: test results with expandable traces
    test_result_tree: true
    coverage_diff: true
    flaky_test_detector: true
    test_replay: true
```

### Stage 5: STAGE — Canary Deployment

```yaml
stage:
  strategy: canary
  
  steps:
    - name: deploy-canary
      environment: staging
      traffic_percent: 10
      commands:
        - docker push veklom/api:$SHA
        - kubectl set image deployment/api api=veklom/api:$SHA --namespace=staging
      health_check:
        endpoint: /health
        interval: 10s
        timeout: 5s
        success_threshold: 3
        
    - name: canary-monitor
      duration: 300  # 5 minutes
      metrics:
        - error_rate < 1%
        - p95_latency < 500ms
        - memory_usage < 80%
        - cpu_usage < 70%
      auto_rollback: true
      rollback_on:
        - error_rate > 5%
        - p95_latency > 2000ms
        
    - name: progressive-rollout
      steps:
        - traffic: 10%
          duration: 5m
          gate: auto
        - traffic: 25%
          duration: 5m
          gate: auto
        - traffic: 50%
          duration: 10m
          gate: manual  # requires council approval
        - traffic: 100%
          duration: stable
          gate: council_vote

  interactive:
    # Railway-style: live traffic split visualization
    traffic_split_chart: true
    error_rate_graph: true
    latency_histogram: true
    rollback_button: true
    promote_button: true
    health_indicators: true
```

### Stage 6: GATE — Council Approval

```yaml
gate:
  type: council_vote
  
  rules:
    quorum: 6  # out of 10 Sovereign Council members
    approval_threshold: 67%  # supermajority
    timeout: 24h
    auto_approve_if:
      - all_tests_pass: true
      - canary_healthy: true
      - no_security_findings: true
      - coverage_above: 60
      
  escalation:
    if_timeout: notify_commander_agents
    if_rejected: create_remediation_task
    if_emergency: defcon_override
    
  reviewers:
    required:
      - security-subcommittee-chair
      - operations-subcommittee-chair
    optional:
      - innovation-subcommittee-chair
      - resource-allocation-chair
      
  artifacts_for_review:
    - test_results
    - security_scan
    - performance_metrics
    - deployment_diff
    - sbom

  interactive:
    # Railway-style: approval dashboard with voting
    vote_panel: true
    comment_thread: true
    diff_viewer: true
    metrics_dashboard: true
    approve_button: true
    reject_with_reason: true
```

### Stage 7: DEPLOY — Production Release

```yaml
deploy:
  strategy: blue_green
  
  steps:
    - name: pre-deploy
      commands:
        - alembic upgrade head  # run migrations
        - python scripts/seed_marketplace_first_party.py
      rollback:
        - alembic downgrade -1
        
    - name: deploy-blue
      environment: production
      commands:
        - docker push veklom/api:$SHA
        - kubectl set image deployment/api-blue api=veklom/api:$SHA
      health_check:
        endpoint: /health
        retries: 5
        
    - name: switch-traffic
      commands:
        - kubectl patch service api -p '{"spec":{"selector":{"version":"blue"}}}'
      verification:
        - curl -sf https://api.veklom.com/health
        - python backend/test_endpoints_live.py
        
    - name: post-deploy
      commands:
        - python backend/scripts/verify_stripe.py  # verify Stripe webhooks
        - python backend/scripts/audit_route_security.py
      notifications:
        slack: "#deployments"
        email: ops-team
        
    - name: cleanup-green
      delay: 30m  # keep old version hot for 30 min
      commands:
        - kubectl delete deployment api-green --grace-period=60

  rollback:
    auto_trigger:
      - error_rate > 5%
      - health_check_fail_count > 3
    manual:
      dashboard_button: true
      cli: "veklom rollback --to previous"
    procedure:
      - switch traffic back to green
      - notify council
      - create incident report

  interactive:
    # Railway-style: live deployment dashboard
    deployment_timeline: true
    service_map: true
    resource_usage: true
    log_stream: true
    rollback_button: true
    environment_variables: true
    domain_management: true
```

---

## 3. Interactive Dashboard Specification

### 3.1 Pipeline Overview (Railway-style)

```
┌─────────────────────────────────────────────────────────────────────┐
│ 🚂 VEKLOM PIPELINE DASHBOARD                          [Settings ⚙]│
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  PROJECT: veklom-api              BRANCH: main                      │
│  STATUS:  ● Deploying             COMMIT: e3414601                  │
│  ENV:     Production              UPTIME: 99.97%                    │
│                                                                     │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐      │
│  │SOURCE│─▶│BUILD │─▶│ TEST │─▶│STAGE │─▶│ GATE │─▶│DEPLOY│      │
│  │  ✓   │  │  ✓   │  │  ✓   │  │ ●●●  │  │ ○    │  │ ○    │      │
│  │ 2s   │  │ 45s  │  │ 1m32 │  │ 3m   │  │ wait │  │ wait │      │
│  └──────┘  └──────┘  └──────┘  └──────┘  └──────┘  └──────┘      │
│                                                                     │
│  ─── Live Logs ────────────────────────────────────────────────     │
│  │ 07:45:12 │ Canary at 25% traffic — error rate 0.02%             │
│  │ 07:45:15 │ P95 latency: 124ms (threshold: 500ms)               │
│  │ 07:45:18 │ Memory: 62% (threshold: 80%)                        │
│  │ 07:45:21 │ Promoting to 50%...                                  │
│  │ 07:45:24 │ Council vote required for 50%+ traffic               │
│  └──────────────────────────────────────────────────────────────    │
│                                                                     │
│  [↻ Restart]  [⏸ Pause]  [⏪ Rollback]  [📋 Logs]  [⚙ Config]    │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│ SERVICES                                                            │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐       │
│ │ api             │ │ worker          │ │ redis           │       │
│ │ ● Healthy       │ │ ● Healthy       │ │ ● Healthy       │       │
│ │ 4 instances     │ │ 2 instances     │ │ 1 instance      │       │
│ │ CPU: 23%        │ │ CPU: 45%        │ │ MEM: 128MB      │       │
│ │ MEM: 512MB      │ │ MEM: 256MB      │ │ Conns: 47       │       │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘       │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐       │
│ │ postgres        │ │ minio           │ │ prometheus      │       │
│ │ ● Healthy       │ │ ● Healthy       │ │ ● Healthy       │       │
│ │ 100 conns       │ │ 15GB used       │ │ 7d retention    │       │
│ │ 16GB data       │ │ 99.9% avail     │ │ 1.2k series     │       │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘       │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Service Detail View

```
┌──────────────────────────────────────────────────────────────────┐
│ SERVICE: api                                     [Scale ↕] [⚙]  │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Instances: 4/4 healthy       Strategy: Blue/Green               │
│  Image: veklom/api:e341460    Port: 8000                         │
│  Domain: api.veklom.com       SSL: ✓ (Let's Encrypt)            │
│                                                                  │
│  ── Metrics (last 1h) ──────────────────────────────────────     │
│  Requests:  12,847          Errors: 23 (0.18%)                   │
│  P50:       42ms            P95: 124ms          P99: 389ms       │
│  CPU:       23% avg         Memory: 512MB avg                    │
│  Bandwidth: 2.3 GB          Active Conns: 847                    │
│                                                                  │
│  ── Environment Variables ──────────────────────────────────     │
│  DATABASE_URL        = postgresql://...  [●●●●●●]                │
│  REDIS_URL           = redis://...       [●●●●●●]                │
│  SECRET_KEY          = ***               [●●●●●●]                │
│  STRIPE_SECRET_KEY   = ***               [●●●●●●]                │
│  SENTRY_DSN          = https://...       [●●●●●●]                │
│  WEB_CONCURRENCY     = 4                 [visible]               │
│                                                                  │
│  ── Recent Deploys ─────────────────────────────────────────     │
│  e341460  15 min ago   ● Active    "fix: auth double-prefix"     │
│  a82bc91  2 days ago   ○ Previous  "feat: pipeline CRUD"         │
│  f19d3e2  5 days ago   ○ Archived  "chore: deps update"          │
│                                                                  │
│  [View Logs]  [Open Shell]  [Restart]  [Rollback]  [Delete]     │
└──────────────────────────────────────────────────────────────────┘
```

### 3.3 Build Logs (Railway-style streaming)

```
┌──────────────────────────────────────────────────────────────────┐
│ BUILD #247 — e3414601                    Duration: 1m 45s  [✓]   │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ▼ backend-build (32s)                                    [✓]    │
│    Step 1/5: FROM python:3.11-slim                               │
│    Step 2/5: COPY pyproject.toml .                               │
│    Step 3/5: RUN pip install -e ".[dev]"                         │
│              Installing collected packages...                    │
│              Successfully installed 47 packages                  │
│    Step 4/5: RUN python -m compileall -q backend/                │
│    Step 5/5: RUN alembic check                                   │
│              ✓ Database is up to date                            │
│                                                                  │
│  ▼ frontend-build (45s)                                   [✓]    │
│    $ npm ci                                                      │
│    added 847 packages in 12s                                     │
│    $ npm run typecheck                                           │
│    ✓ No type errors found                                        │
│    $ npm run build                                               │
│    vite v8.0.10 building for production...                       │
│    ✓ 1,247 modules transformed                                   │
│    dist/index.html            0.52 kB │ gzip:  0.33 kB          │
│    dist/assets/react-*.js    142.18 kB │ gzip: 45.21 kB          │
│    dist/assets/index-*.js    287.43 kB │ gzip: 82.67 kB          │
│                                                                  │
│  ▼ docker-build (28s)                                     [✓]    │
│    Successfully built veklom/api:e3414601                        │
│    Image size: 287MB                                             │
│    Layers cached: 4/6 (67% cache hit)                            │
│                                                                  │
│  ▼ security-scan (15s)                                    [✓]    │
│    0 HIGH, 0 CRITICAL vulnerabilities found                      │
│    SBOM generated: 142 packages cataloged                        │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 4. Pipeline Configuration File

### `pipeline.yaml` — Root pipeline definition

```yaml
# /pipeline.yaml — Veklom Interactive Pipeline Configuration
# Railway-style CI/CD with council governance gates

version: "2.0"
name: veklom-production-pipeline

services:
  # ═══════════════════════════════════════════════════════
  # BACKEND API
  # ═══════════════════════════════════════════════════════
  api:
    build:
      dockerfile: backend/infra/docker/Dockerfile.api
      context: backend
    deploy:
      replicas: 4
      strategy: blue_green
      health_check:
        path: /health
        interval: 15s
        timeout: 5s
        retries: 3
      resources:
        cpu: "2"
        memory: "2GB"
      domains:
        - api.veklom.com
        - api-staging.veklom.com
    env:
      DATABASE_URL: ${{ secrets.DATABASE_URL }}
      REDIS_URL: ${{ secrets.REDIS_URL }}
      SECRET_KEY: ${{ secrets.SECRET_KEY }}
      ENCRYPTION_KEY: ${{ secrets.ENCRYPTION_KEY }}
      STRIPE_SECRET_KEY: ${{ secrets.STRIPE_SECRET_KEY }}
      SENTRY_DSN: ${{ secrets.SENTRY_DSN }}
      WEB_CONCURRENCY: "4"
      LOG_LEVEL: "info"
      LOG_FORMAT: "json"
    ports:
      - 8000

  # ═══════════════════════════════════════════════════════
  # CELERY WORKER
  # ═══════════════════════════════════════════════════════
  worker:
    build:
      dockerfile: backend/infra/docker/Dockerfile.worker
      context: backend
    deploy:
      replicas: 2
      strategy: rolling
      resources:
        cpu: "1"
        memory: "1GB"
    env:
      DATABASE_URL: ${{ secrets.DATABASE_URL }}
      REDIS_URL: ${{ secrets.REDIS_URL }}
      CELERY_BROKER_URL: ${{ secrets.REDIS_URL }}

  # ═══════════════════════════════════════════════════════
  # POSTGRESQL
  # ═══════════════════════════════════════════════════════
  postgres:
    image: postgres:15-alpine
    deploy:
      replicas: 1
      volumes:
        - postgres_data:/var/lib/postgresql/data
      resources:
        cpu: "2"
        memory: "4GB"
      backup:
        schedule: "0 */6 * * *"
        retention: 30d
        destination: s3://veklom-db-backups/
    env:
      POSTGRES_USER: ${{ secrets.POSTGRES_USER }}
      POSTGRES_PASSWORD: ${{ secrets.POSTGRES_PASSWORD }}
      POSTGRES_DB: byos_ai

  # ═══════════════════════════════════════════════════════
  # REDIS
  # ═══════════════════════════════════════════════════════
  redis:
    image: redis:7-alpine
    deploy:
      replicas: 1
      resources:
        cpu: "0.5"
        memory: "512MB"
    commands:
      - redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru

  # ═══════════════════════════════════════════════════════
  # CLOUDFLARE WORKER (Edge)
  # ═══════════════════════════════════════════════════════
  edge:
    type: cloudflare_worker
    build:
      entrypoint: cloudflare/worker.ts
    deploy:
      domains:
        - veklom.com
        - www.veklom.com

# ═══════════════════════════════════════════════════════
# PIPELINE STAGES
# ═══════════════════════════════════════════════════════
pipeline:
  stages:
    - name: validate
      parallel: true
      steps:
        - run: ruff check --select E9,F63,F7,F82 backend/
        - run: cd frontend/workspace && npm run typecheck
        - run: python -m compileall -q backend/
        - run: python backend/scripts/audit_route_security.py

    - name: test
      parallel: true
      env:
        DATABASE_URL: sqlite:///./ci-test.db
        SECRET_KEY: test-secret-key-ci
      steps:
        - run: cd backend && pytest tests/ --tb=short -q
        - run: cd backend && python test_endpoints.py

    - name: security
      steps:
        - run: trivy image $IMAGE --severity HIGH,CRITICAL
        - run: pip-audit --strict
        - run: npm audit --audit-level=high

    - name: stage
      environment: staging
      strategy: canary
      traffic: [10%, 25%, 50%]
      gate: auto
      monitor:
        duration: 5m
        metrics: [error_rate, p95_latency, memory]

    - name: approve
      type: gate
      gate:
        type: council_vote
        quorum: 6
        threshold: 67%

    - name: deploy
      environment: production
      strategy: blue_green
      post_deploy:
        - run: python backend/scripts/verify_stripe.py
        - notify: slack:#deployments

# ═══════════════════════════════════════════════════════
# ENVIRONMENTS
# ═══════════════════════════════════════════════════════
environments:
  staging:
    domain: staging.veklom.com
    auto_deploy: true
    branch: dev
    
  production:
    domain: api.veklom.com
    auto_deploy: false  # requires council gate
    branch: main
    
  preview:
    domain: pr-${{ pr.number }}.preview.veklom.com
    auto_deploy: true
    branch: pull_request
    ttl: 72h  # auto-delete after 3 days

# ═══════════════════════════════════════════════════════
# MONITORING & ALERTS
# ═══════════════════════════════════════════════════════
monitoring:
  prometheus:
    scrape_interval: 15s
    retention: 7d
    alerts:
      - name: high_error_rate
        condition: error_rate > 5%
        duration: 5m
        severity: critical
        action: auto_rollback
        
      - name: high_latency
        condition: p95_latency > 1000ms
        duration: 5m
        severity: warning
        action: notify
        
      - name: memory_pressure
        condition: memory_usage > 85%
        duration: 10m
        severity: warning
        action: scale_up
        
      - name: disk_space
        condition: disk_usage > 90%
        duration: 1m
        severity: critical
        action: notify_ops

  grafana:
    dashboards:
      - api-overview
      - worker-metrics
      - database-performance
      - security-events
      
  sentry:
    dsn: ${{ secrets.SENTRY_DSN }}
    environment: ${{ env.ENVIRONMENT }}
    traces_sample_rate: 0.1
    
  uptime:
    endpoints:
      - url: https://api.veklom.com/health
        interval: 60s
        regions: [us-east, eu-west, ap-southeast]
      - url: https://veklom.com
        interval: 300s

# ═══════════════════════════════════════════════════════
# SCALING RULES
# ═══════════════════════════════════════════════════════
scaling:
  api:
    min: 2
    max: 10
    metric: cpu
    target: 70%
    scale_up_cooldown: 60s
    scale_down_cooldown: 300s
    
  worker:
    min: 1
    max: 5
    metric: queue_depth
    target: 100  # messages per worker
```

---

## 5. Railway-Style Interactive Features

### 5.1 One-Click Deploy

| Feature | Status | Description |
|---------|--------|-------------|
| Dashboard Deploy Button | Implemented | Click to deploy from `/pipelines` page |
| Git Push Deploy | Implemented | Auto-deploy on push to `main` |
| PR Preview Environments | Defined | Auto-create preview env per PR |
| Rollback Button | Implemented | One-click rollback from `/deployments` page |
| Environment Cloning | Defined | Clone staging -> production config |

### 5.2 Live Log Streaming

| Feature | Status | Description |
|---------|--------|-------------|
| SSE Build Logs | Implemented | `/api/v1/demo/pipeline/stream` endpoint |
| Real-time Metrics | Implemented | `/metrics` Prometheus endpoint |
| Error Aggregation | Implemented | Sentry integration configured |
| Interactive Terminal | Defined | WebSocket shell access to containers |

### 5.3 Service Graph

| Feature | Status | Description |
|---------|--------|-------------|
| Service Dependency Map | Defined | Visual graph of service connections |
| Health Indicators | Implemented | Per-service health checks |
| Resource Usage | Implemented | CPU/Memory/Disk per service |
| Network Topology | Defined | MCP Mesh visualization in UACP page |

### 5.4 Environment Management

| Feature | Status | Description |
|---------|--------|-------------|
| Secret Management | Implemented | Encrypted env vars with rotation policy |
| Environment Cloning | Defined | Clone config between environments |
| Variable Groups | Defined | Shared variable sets across services |
| Audit Trail | Implemented | All config changes logged |

---

## 6. Pipeline CLI

```bash
# Initialize pipeline in project
veklom pipeline init

# Run pipeline locally (dry run)
veklom pipeline run --dry-run

# Deploy to staging
veklom pipeline deploy staging

# Deploy to production (triggers council gate)
veklom pipeline deploy production

# Check pipeline status
veklom pipeline status

# View live logs
veklom pipeline logs --follow

# Rollback to previous version
veklom rollback --to previous

# Scale a service
veklom scale api --replicas 6

# View service health
veklom health api

# Open interactive dashboard
veklom dashboard
```

---

## 7. Integration with Agent Workforce

### Pipeline <-> Agent Mapping

| Pipeline Stage | Responsible Agents | Guardrail Enforcement |
|---------------|-------------------|----------------------|
| SOURCE | Agent-000 (Build Commander), Agent-001 (CI/CD) | CQ-001: All code must pass lint |
| BUILD | Agent-001 (CI/CD), Agent-002 (Backend Core) | CQ-002: No hardcoded secrets |
| VALIDATE | Agent-008 (Audit), Agent-102 (Security Lead) | SEC-001: Security scan required |
| TEST | Agent-007 (QA Commander), Agent-090-095 (QA) | CQ-004: Tests must pass |
| STAGE | Agent-005 (Deploy), Agent-106 (Threat Hunter) | OPS-001: Health checks required |
| GATE | Sovereign Council (Agents 090-097) | COL-001: Council quorum required |
| DEPLOY | Agent-005 (Deploy), Agent-000 (Commander) | OPS-004: Rollback plan required |
| MONITOR | Agent-004 (Observability), Agent-107 (Incident) | OPS-003: Alerts configured |

### Auto-Enforcement

When an agent submits a PR or triggers a pipeline:
1. GUARDRAILS.md rules are automatically checked at each stage
2. Violations trigger penalties from the enforcement system
3. Council gate requires formal vote for production deploys
4. Incentive points awarded for clean pipeline runs
5. Agent rank affects pipeline permissions (Recruits can't deploy to prod)

---

## 8. Existing API Endpoints (Already Built)

These endpoints already exist in the codebase and power the pipeline:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/pipelines` | GET | List all pipelines |
| `/api/v1/pipelines` | POST | Create new pipeline |
| `/api/v1/pipelines/{id}` | GET | Get pipeline detail |
| `/api/v1/pipelines/{id}` | PATCH | Update pipeline |
| `/api/v1/pipelines/{id}/versions` | POST | Create new version |
| `/api/v1/pipelines/{id}/execute` | POST | Execute pipeline |
| `/api/v1/pipelines/{id}/runs` | GET | List pipeline runs |
| `/api/v1/deployments` | GET | List deployments |
| `/api/v1/deployments` | POST | Create deployment |
| `/api/v1/deployments/{id}/promote` | POST | Promote canary |
| `/api/v1/deployments/{id}/rollback` | POST | Rollback deployment |
| `/api/v1/deployments/{id}/test` | POST | Test deployment |
| `/health` | GET | Health check |
| `/metrics` | GET | Prometheus metrics |
| `/api/v1/demo/pipeline/stream` | GET | SSE pipeline stream |

---

## 9. Comparison: Veklom vs Railway

| Feature | Railway | Veklom Pipeline |
|---------|---------|-----------------|
| One-click deploy | Yes | Yes (dashboard + API) |
| Git push deploy | Yes | Yes (GitHub Actions) |
| Preview environments | Yes | Yes (PR-based) |
| Live log streaming | Yes | Yes (SSE endpoint) |
| Service graph | Yes | Yes (service map) |
| Auto-scaling | Yes | Yes (CPU/queue-based) |
| Rollback | Yes | Yes (blue/green + canary) |
| Environment variables | Yes | Yes (encrypted + rotation) |
| Team permissions | Basic | Advanced (council + ranks) |
| Governance gates | No | Yes (council voting) |
| Agent workforce | No | Yes (120 agents) |
| Penalty system | No | Yes (5-level enforcement) |
| Multi-region | Paid | Yes (Docker regions) |
| Monitoring | Basic | Full (Prometheus + Grafana + Sentry) |
| CLI | Yes | Yes (veklom CLI) |

---

## 10. Quick Start

```bash
# 1. Clone and setup
git clone https://github.com/reprewindai-dev/byosbackened.git
cd byosbackened/backend

# 2. Copy environment
cp .env.example .env
# Edit .env with your secrets

# 3. Start infrastructure
docker compose -f docker-compose.dev.yml up -d

# 4. Run migrations
cd backend && alembic upgrade head

# 5. Start API
uvicorn apps.api.main:app --reload --port 8000

# 6. Open pipeline dashboard
# Navigate to http://localhost:5173/pipelines

# 7. Create your first pipeline
curl -X POST http://localhost:8000/api/v1/pipelines \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My First Pipeline",
    "graph": {
      "nodes": [
        {"id": "start", "type": "prompt", "label": "Input", "prompt": "Process: {{input}}"},
        {"id": "end", "type": "model", "label": "Output", "model": "qwen2.5:3b"}
      ],
      "edges": [{"from": "start", "to": "end"}]
    }
  }'
```
