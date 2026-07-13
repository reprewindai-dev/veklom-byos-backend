# Veklom Infrastructure Truth-Lock

**Status**: Verified via live SSH audits against physical edge nodes and the central Hillsboro server on 2026-07-13.

## Local Development Topology

### CAPPO (`veklom-byos-backend-2` / `cappo-backend`)
- **Containers**: `veklom-api`, `veklom-celery-worker`, `veklom-celery-beat`, `veklom-postgres`, `veklom-redis`, `cappo-backend-web`, `veklom-ollama`.
- **Findings**: The `162/UDP` port mapping resides entirely in the local Windows `docker-compose.yml` for testing SNMP traps/telemetry. It is **not** exposed in production. `localhost` is heavily utilized in `.env` configurations. These are development resources only.

## Physical Hetzner Topology

| Node Name | Region | Public IP | Overlay IP (`wg0`) | Container | VNP Status |
|---|---|---|---|---|---|
| `veklom-prod-1` (Central) | Hillsboro | `5.78.135.11` | Unknown (Manager) | Coolify + All Services | **Live** |
| `veklom-edge-us-east` | Ashburn | `87.99.154.166` | `10.0.0.5` | `vnp_probe` | **Connected** |
| `veklom-edge-eu-north2` | Nuremberg | `91.98.78.218` | Unknown | `vnp_probe` | **Connected** |
| `veklom-edge-ap-southeast` | Singapore | `5.223.90.12` | Unknown | `vnp_probe` | **Connected** |
| `veklom-edge-eu-central` | Falkenstein | `167.233.202.195` | Unknown | `vnp_probe` | **Connected** |

**Truth Status**: The 4 edge nodes are **Connected**, but they are **not** marked as `Live` because they lack verifiable signed heartbeats and accepted observations in the central ledger.

## Production Coolify Topology (`veklom-prod-1`)

### Application Inventory

1. **veklom-byos-backend**
   - FQDN: `api.veklom.com`
   - Internal Alias: `n13gp1nhrcdp0hvazvbnlxru`
   - Port: `8088/tcp`
   - DB / Redis: `veklom-postgres`, `veklom-redis`
   - Status: **Live** (Duplicate RepoGate logic excised)

2. **cappo-backend**
   - FQDN: `cappo.veklom.com`
   - Internal Alias: `yen2fecq8burtsgqrm2b988e`
   - Port: `8000/tcp`
   - DB / Redis: `cappodb`
   - Status: **Live** (Alembic PythonPath fix deployed)

3. **veklom-control-plane**
   - FQDN: `control.veklom.com`
   - Internal Alias: `tvxcsezs2ypd8tjuj6ic9gih`
   - Port: `3002/tcp`
   - Status: **Live**

4. **real-repo-gate-for-veklom**
   - FQDN: `repogate.veklom.com`
   - Internal Alias: `repogate-container`
   - Port: `3000/tcp` (Internal)
   - Status: **Live** (Manually deployed to `coolify` network, proxy dynamically bound)

5. **veklom-vnp-standalone**
   - FQDN: `vnp.veklom.com`
   - Internal Alias: `vnp-container`
   - Port: `8000/tcp` (Internal)
   - Status: **Live** (Manually deployed to `coolify` network, proxy dynamically bound)

6. **gnomledger (PGL)**
   - FQDN: `pgl.veklom.com`
   - Port: `8000/tcp`
   - Status: **Insufficient Evidence** (Lacks dedicated database cluster in `docker ps`; persistence guarantees unverified).

7. **cAPI / MetaMCP / NewAPI / GPC**
   - Status: **Live**

8. **Poltergeist / Replay**
   - Status: **Not Yet Wired** (Contracts and storage requirements frozen per directive).

### Database Security Inventory

| Resource | Image | Port | Public Exposure | Status |
|---|---|---|---|---|
| `veklom-postgres` | `postgres:15-alpine` | `5432/tcp` | None (No Host Bind) | **Live** |
| `cappodb` | `postgres:16-alpine` | `5432/tcp` | None (No Host Bind) | **Live** |
| `veklom-redis` | `redis:7-alpine` | `6379/tcp` | None (No Host Bind) | **Live** |

## Required Corrections (Audit Findings)

1. **Localhost Violations**: `localhost` is heavily utilized in Coolify application settings (e.g., `Server: localhost`). Application `.env` configs must be audited to ensure they route to `coolify` Docker DNS aliases instead of `localhost`. **(Status: Config Incomplete)**
2. **Edge Network Isolation**: Wireguard (`wg0`) exists on the edge nodes (`10.0.0.5`), but `vnp_probe` is binding to `0.0.0.0:8002`, bypassing the secure overlay network. Edge nodes must be restricted. **(Status: Auth Required)**
3. **Synthetic Telemetry**: Must be aggressively purged from `vnp_probe` logic before nodes can be transitioned to `Live`. **(Status: Methodology Target)**
4. **GitHub Runner**: Isolated to `n7c69w73sfjoygmimv2j3wlj` Docker network. **(Status: Live)**
