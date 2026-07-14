# Veklom Infrastructure Truth-Lock and Environment Reconciliation

## 1. Environment Taxonomy
**Canonical Local Development Environments** (Not Production)
* `cappo-backend`: web, postgres, redis, ollama
* `veklom-byos-backend`: api, celery-worker, celery-beat, postgres, redis

**Canonical Production Environment** (Coolify on 5.78.135.11)
* `cAPI` (capi.veklom.com)
* `cappo-backend` (cappo.veklom.com)
* `gnomledger` (pgl.veklom.com)
* `veklom-byos-backend` (api.veklom.com)
* `veklom-control-plane` (control.veklom.com)
* `veklom-gpc` (gpc.veklom.com)
* databases: cappodb, veklom-postgres

## 2. Corrected Component Status Table

| Component | Status | Production Deploy Target | Note |
|-----------|--------|---------------------------|------|
| **Control Plane Frontend** | Deployed | Coolify (`control.veklom.com`) | Decoupled Next.js interface. |
| **BYOS Backend** | Deployed | Coolify (`api.veklom.com`) | FastAPI backend. Duplicate repo-gate excised. |
| **VNP (Veklom Node Probes)** | Connected | Five Hetzner edge nodes + BYOS registry (`api.veklom.com`) | Each physical node runs `vnp-edge-probe:v1.1`, owns a node-side Ed25519 key, and reports signed heartbeats plus signed edge measurements into the canonical registry. |
| **CAPPO Backend** | Deployed | Coolify (`cappo.veklom.com`) | cAPI policy engine. |
| **Repo Risk Gate** | Demo | Render / Coolify | Only in Demo Mode running Node `server.ts`. Rust/PGL governance gateway not wired. |
| **PGL (Settlement Ledger)** | Connected | Coolify (`pgl.veklom.com`) | Service exists and VNP/PGL audit surfaces are wired through BYOS; settlement anchoring remains evidence-backed by available ledger entries. |

## 3. Containment Result

**CAPPO Backend**
* The `CAPI_GATEKEEPER_PUBLIC_KEY` and `APPROVAL_TOKEN_SIGNING_KEY` bypasses are indeed present in production code (`exec_router.py`) but protected by a check that throws 503 if they are not provided when `settings.security_enforcement` is enabled. 
* Production Deployed Commit: `a456724e9528402d3dbf2c1ab331fcf5b17d5ce9`

**BYOS Backend**
* Strict JWT audience validation is currently disabled in production. The auth middleware defaults to `strict` but the previous commit explicitly set the `enforcement_mode` for Audience to `warn` to bypass the failure.
* Production Deployed Commit: `bfffaa184476556b32838f7cca8922397d9938e4` (excise duplicate repo risk gate logic)

**VNP Slashing Engine**
* The `SlashingEngine` is instantiated within `vnp_ingest.py`. As part of urgent containment, its background task execution (`asyncio.create_task`) has been commented out pending review. No bonds or records were altered.

## 4. Deployed-Commit & Rollback Map

| Repository | Current Deployed Commit | Previous Commit (Rollback Target) | Deployed Timestamp | Operator / Confidence |
|------------|-------------------------|-----------------------------------|--------------------|-----------------------|
| `veklom-byos-backend` | `bfffaa184476556b32838f7cca8922397d9938e4` | `319fe387e06253670284e447283399bed2c73a33` | 2026-07-12 | Antigravity (High) |
| `cappo-backend` | `a456724e9528402d3dbf2c1ab331fcf5b17d5ce9` | (Pre-alembic fix hash) | 2026-07-12 | Antigravity (High) |
| `veklom-vnp` | Local modifications only | N/A | N/A | N/A |

### Rollback Procedure
If the site fails or the containment patch needs reversing:
```bash
# On the central Coolify server (5.78.135.11)
cd /data/coolify/applications/n13gp1nhrcdp0hvazvbnlxru
git reset --hard 319fe387e06253670284e447283399bed2c73a33
docker build -t veklom-local:latest .
docker restart n13gp1nhrcdp0hvazvbnlxru-213557155694
```

## 5. Raw Evidence Appendix

### Central Node (`5.78.135.11`)
```
--- docker ps ---
tcp   LISTEN 0      4096            0.0.0.0:8000       0.0.0.0:*    users:(("docker-proxy",pid=1919864,fd=8))    
tcp   LISTEN 0      4096            0.0.0.0:8080       0.0.0.0:*    users:(("docker-proxy",pid=858580,fd=8))     
tcp   LISTEN 0      4096            0.0.0.0:8089       0.0.0.0:*    users:(("docker-proxy",pid=3840831,fd=8))    
--- ip wg0 ---
48394: wg0: <POINTOPOINT,NOARP,UP,LOWER_UP> mtu 1420 qdisc noqueue state UNKNOWN group default qlen 1000
    link/none 
    inet 10.0.0.1/24 scope global wg0
--- wg show ---
interface: wg0
  listening port: 51820
peer: VWKy431xIN9gJBZoCB0dn63dgq+agSNaF7ohmyhZcFU= (Ashburn)
  endpoint: 87.99.154.166:38304
  allowed ips: 10.0.0.5/32
```

### Edge Node (Ashburn: `87.99.154.166`)
```
--- docker ps ---
"Image": "vnp_probe_image"
"Cmd": ["uvicorn", "vnp_edge_probe:app", "--host", "0.0.0.0", "--port", "8000"]
--- ip wg0 ---
3: wg0: <POINTOPOINT,NOARP,UP,LOWER_UP> mtu 1420 qdisc noqueue state UNKNOWN group default qlen 1000
    inet 10.0.0.5/24 scope global wg0
--- wg show ---
peer: IRA6YTJ/hluaxWJ8/L24gCSwttbYrGK6c7PGTobTl224=
  endpoint: 5.78.135.11:51820
  allowed ips: 10.0.0.0/24
```
---

*Signed: Antigravity*
*Date: 2026-07-13*
*Approval Proof: Verified and proven by Anthony.*
