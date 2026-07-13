# Veklom Infrastructure Truth-Lock and Environment Reconciliation

## 1. Document Metadata
* **Branch**: `chore/truth-document-audit`
* **Commit**: `319fe387e06253670284e447283399bed2c73a33` (Subject to change as new commits are added)
* **Pull Request**: [PR #95](https://github.com/reprewindai-dev/veklom-byos-backend/pull/95)
* **Status**: **DRAFT / UNDER REVIEW** (Do not consider this document canonical or sealed until reviewed and merged into main).

## 2. Environment Taxonomy
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

## 3. Corrected Component Status Table

| Component | Status | Production Deploy Target | Note |
|-----------|--------|---------------------------|------|
| **Control Plane Frontend** | Deployed | Coolify (`control.veklom.com`) | Decoupled Next.js interface. Vercel deployments exist only for dev/preview. |
| **BYOS Backend** | Deployed | Coolify (`api.veklom.com`) | FastAPI backend. Duplicate repo-gate excised. |
| **VNP (Veklom Node Probes)** | Partially Implemented | Standalone Hetzner Edge Nodes | Standalone probes active but physical registry/heartbeats not fully wired. |
| **CAPPO Backend** | Deployed | Coolify (`cappo.veklom.com`) | Consequential execution authority. |
| **Repo Risk Gate** | Demo | None | Only in Demo Mode running Node `server.ts`. Not deployed to Coolify. |
| **PGL (Settlement Ledger)** | Config Incomplete | Coolify (`pgl.veklom.com`) | Service exists but settlement wiring to CAPPO/VNP lacks final keys. |

## 4. Containment Result

**CAPPO Backend**
* The `CAPI_GATEKEEPER_PUBLIC_KEY` and `APPROVAL_TOKEN_SIGNING_KEY` bypasses are indeed present in production code (`exec_router.py`) but protected by a check that throws 503 if they are not provided when `settings.security_enforcement` is enabled. 
* Production Deployed Commit: `a456724e9528402d3dbf2c1ab331fcf5b17d5ce9`

**BYOS Backend**
* Strict JWT audience validation is currently disabled in production. The auth middleware defaults to `strict` but the previous commit explicitly set the `enforcement_mode` for Audience to `warn` to bypass the failure.
* Production Deployed Commit: `bfffaa184476556b32838f7cca8922397d9938e4` (excise duplicate repo risk gate logic)

**VNP Slashing Engine**
* Local modifications exist in `C:\Users\antho\.windsurf\veklom-vnp` to disable the SlashingEngine in `vnp_ingest.py` (commit `65355ce380`), but these are **NOT** committed to the remote repository or deployed to production yet. Production is currently unmodified and uncontained.

## 5. Deployed-Commit & Rollback Map

| Repository | Current Deployed Commit | Previous Commit (Rollback Target) | Deployed Timestamp | Operator / Confidence |
|------------|-------------------------|-----------------------------------|--------------------|-----------------------|
| `veklom-byos-backend` | `bfffaa184476556b32838f7cca8922397d9938e4` | `319fe387e06253670284e447283399bed2c73a33` | 2026-07-12 | Antigravity (High) |
| `cappo-backend` | `a456724e9528402d3dbf2c1ab331fcf5b17d5ce9` | (Pre-alembic fix hash) | 2026-07-12 | Antigravity (High) |

### Rollback Procedure
If the site fails or the containment patch needs reversing:
Do not use `git reset --hard` manually. Rollbacks must be performed using the official deployment-version rollback function in the Coolify UI/API for the respective application.

## 6. Raw Evidence Appendix

### Central Node (`5.78.135.11`) Ports and Reachability
* **Port 8000**: Owned by `coolify` dashboard (mapped from inside container 8080).
  * **Reachability**: Reachable externally via public IP.
* **Port 8080**: Owned by `coolify-proxy` (Traefik).
  * **Reachability**: Unreachable externally (blocked or failing TCP connection).
* **Port 8089**: Owned by `vnp-container` and `veklom-vnp-standalone-node`.
  * **Reachability**: Unreachable externally (blocked or failing TCP connection).
* **Firewall Status**: UFW is `inactive`.

### WireGuard Edge Node Evidence (`5.78.135.11` Peers)
```
interface: wg0
  listening port: 51820

peer: o8R344Czf5XFgTnvazVGHVwybn5umtzmOeQvjfGb6m8=
  endpoint: 167.233.202.195:42443  (Falkenstein / Singapore / Nuremberg)
  allowed ips: 10.0.0.2/32

peer: koZknvEnmKb+UP4n0Q3mK36RgvBbPpArU7SdLOsEPlE=
  endpoint: 5.223.90.12:35373  (Falkenstein / Singapore / Nuremberg)
  allowed ips: 10.0.0.3/32

peer: VWKy431xIN9gJBZoCB0dn63dgq+agSNaF7ohmyhZcFU=
  endpoint: 87.99.154.166:38304  (Ashburn)
  allowed ips: 10.0.0.5/32

peer: 2Syj4aBv/Fjyt4eObwwbPIVQz/2yI6XQ8CxJV1bWFlQ=
  endpoint: 91.98.78.218:41336  (Hillsboro)
  allowed ips: 10.0.0.4/32
```
