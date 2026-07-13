# Veklom Infrastructure Truth-Lock and Environment Reconciliation

## 1. Document Metadata
* **Branch**: `chore/truth-document-audit`
* **Commit**: `f9003b97de9630a4ba39fe05dc4c2cb37f82dac8`
* **Reviewed document revision**: `f9003b97de9630a4ba39fe05dc4c2cb37f82dac8`
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
| **PGL / GnomLedger — Identity and Evidence Ledger** | Config Incomplete | Coolify (`pgl.veklom.com`) | Service exists but settlement wiring to CAPPO/VNP lacks final keys. |

## 4. Containment Result

**CAPPO Backend**
* CAPPO contains temporary production startup-validation bypasses for `CAPI_GATEKEEPER_PUBLIC_KEY` and `APPROVAL_TOKEN_SIGNING_KEY` inside `cappo_backend/config.py`.
* Some execution paths may independently reject missing keys when `security_enforcement` is enabled, but startup remains fail-open for these two required controls.
* Production Deployed Commit: `a456724e9528402d3dbf2c1ab331fcf5b17d5ce9`

**BYOS Backend**
* Strict JWT audience validation is currently disabled in production. The auth middleware defaults to `strict` but the previous commit explicitly set the `enforcement_mode` for Audience to `warn` to bypass the failure.
* Production Deployed Commit: `bfffaa184476556b32838f7cca8922397d9938e4` (excise duplicate repo risk gate logic)

**VNP Slashing Engine**
* Local modifications exist in `C:\Users\antho\.windsurf\veklom-vnp` to disable the SlashingEngine in `vnp_ingest.py` (commit `65355ce380`), but these are **NOT** committed to the remote repository or deployed to production yet. Production is currently unmodified and uncontained.

## 5. Deployed-Commit & Rollback Map

| Repository | Current Deployed Commit | Previous Commit (Rollback Target) | Deployed Timestamp | Operator / Confidence |
|------------|-------------------------|-----------------------------------|--------------------|-----------------------|
| `veklom-byos-backend` | `a0a98b0` | `4845900` | 2026-07-13 | Antigravity (High) |
| `cappo-backend` | `a456724e9528402d3dbf2c1ab331fcf5b17d5ce9` | `0f018fc` | 2026-07-13 | Antigravity (High) |

### Rollback Procedure
If the site fails or the containment patch needs reversing:
Do not use `git reset --hard` manually. Rollbacks must be performed using the official deployment-version rollback function in the Coolify UI/API for the respective application.

## 6. Raw Evidence Appendix

### Central Node (`5.78.135.11`) Ports and Reachability
* **Port 8000**: Mapped to `8080/tcp` inside container `7115e7e36546` (`coolify`). Containers `8b49c3f614d7` (`yen2fecq8burtsgqrm2b988e-085938457758`), `63e18109407f` (`gnomledger-api-1`), and `161860d45402` (`xlkby54o7jdlib3rz2p510cs-012322741566`) also map `0.0.0.0:8000->8080/tcp`. 
  * **Reachability**: Reachable externally via public IP (Tested 2026-07-13).
* **Port 8080**: Owned by container `fe8b16d7ac29` (`coolify-proxy`) mapped `0.0.0.0:8080->8080/tcp`. Container `f1e303700088` (`pageindex-mcp`) also maps to `8080`.
  * **Reachability**: Unreachable externally (blocked or failing TCP connection).
* **Port 8089**: Container `32f4c44b023e` (`vnp-container`) and container `ab40785c6bd1` (`veklom-vnp-standalone-node`) both map to `8089/tcp`. The overlap implies one container is likely stopped or not actively binding the host interface if the other succeeds.
  * **Reachability**: Unreachable externally (blocked or failing TCP connection).
* **Firewall Status**: UFW is `inactive`. `iptables -L -n -t nat` shows `DOCKER` chain redirects actively routing traffic on the host (e.g., `ADDRTYPE match dst-type LOCAL`). Hetzner Cloud firewall rules may still be restricting external ingress for ports `8080` and `8089`.

### WireGuard Edge Node Evidence (`5.78.135.11` Peers)
```
interface: wg0
  listening port: 51820

peer: o8R344Czf5XFgTnvazVGHVwybn5umtzmOeQvjfGb6m8=
  endpoint: 167.233.202.195:42443  (Falkenstein)
  allowed ips: 10.0.0.2/32
  latest handshake: 1783961082
  transfer: 1.61 MB received, 434.88 KB sent
  persistent keepalive: off

peer: koZknvEnmKb+UP4n0Q3mK36RgvBbPpArU7SdLOsEPlE=
  endpoint: 5.223.90.12:35373  (Singapore)
  allowed ips: 10.0.0.3/32
  latest handshake: 1783961067
  transfer: 1.60 MB received, 434.61 KB sent
  persistent keepalive: off

peer: 2Syj4aBv/Fjyt4eObwwbPIVQz/2yI6XQ8CxJV1bWFlQ=
  endpoint: 91.98.78.218:41336  (Nuremberg)
  allowed ips: 10.0.0.4/32
  latest handshake: 1783961103
  transfer: 1.61 MB received, 435.16 KB sent
  persistent keepalive: off

peer: VWKy431xIN9gJBZoCB0dn63dgq+agSNaF7ohmyhZcFU=
  endpoint: 87.99.154.166:38304  (Ashburn)
  allowed ips: 10.0.0.5/32
  latest handshake: 1783961178
  transfer: 1.61 MB received, 436.33 KB sent
  persistent keepalive: off
```
