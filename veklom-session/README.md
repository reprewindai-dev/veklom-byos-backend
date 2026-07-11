# Veklom Session Layer — Global Enforcer Mesh

Governed AI execution with distributed enforcement, signed incidents,
consensus gating, and a tamper-evident federated audit ledger.

## Files

| File | Purpose |
|------|---------|
| `session.py` | AgentSession — stateful, chained, HMAC-signed execution context |
| `enforcer.py` | EnforcerAgent — passive watcher, rule-driven intervention (warn/alert/hold/kill) |
| `mesh.py` | ZoneEnforcerNode, ZoneWatchlist, ConsensusGate |
| `mesh_node.py` | FastAPI + WebSocket mesh node — one process per zone |
| `crypto.py` | Ed25519 keypairs, MeshKeyRegistry, sign/verify for incidents |
| `main.py` | Single-zone FastAPI control plane — 13 endpoints |
| `demo.py` | Basic session lifecycle |
| `demo_enforcer.py` | Enforcer rules — banking scenario |
| `demo_mesh.py` | 3-zone mesh — NYC / London / Singapore |
| `demo_global.py` | Full 6-stage global response flow |
| `demo_crypto.py` | Ed25519 signing — 4 attack vectors rejected |

## Install

```bash
pip install fastapi uvicorn websockets cryptography
```

## Run a mesh node

```bash
# Each zone is one process
uvicorn veklom-session.mesh_node:create_mesh_node --factory --port 8001  # NYC
uvicorn veklom-session.mesh_node:create_mesh_node --factory --port 8002  # London
uvicorn veklom-session.mesh_node:create_mesh_node --factory --port 8003  # Singapore

# Register peers
curl -X POST http://localhost:8001/mesh/peers \
  -H "Content-Type: application/json" \
  -d '{"peer_url": "ws://localhost:8002/mesh/connect"}'
```

## Run demos

```bash
python3 veklom-session/demo.py           # session lifecycle
python3 veklom-session/demo_enforcer.py  # banking enforcer rules
python3 veklom-session/demo_mesh.py      # 3-zone mesh propagation
python3 veklom-session/demo_global.py    # 6-stage global response flow
python3 veklom-session/demo_crypto.py    # Ed25519 sign/verify/tamper/reject
```

## Architecture

```
AgentSession          stateful execution context, chained transitions, HMAC-signed audit
    └── EnforcerAgent     passive watcher, fires only on rule violation
            └── Rules:    cost-warning, max-errors, probe-detection, jurisdiction-guard

ZoneEnforcerNode      wraps enforcer + watchlist + consensus gate
    └── ZoneWatchlist     cross-zone threat intelligence, raises alert threshold
    └── ConsensusGate     N-zone quorum required for critical interventions

FederatedAuditLedger  append-only SHA-256 chained ledger, tamper breaks chain

crypto.py             Ed25519 per-zone keypairs, MeshKeyRegistry, sign/verify
                      Rejects: tampered payload, unknown zone, wrong key
```

## Security properties

| Property | Implementation |
|----------|---------------|
| Tamper-evident sessions | SHA-256 chained transitions in AgentSession |
| Signed incidents | Ed25519 asymmetric signing via crypto.py |
| Tamper rejection | Verified in demo_crypto.py — 4 attack vectors |
| Chained audit ledger | SHA-256 chain in FederatedAuditLedger |
| No single point of failure | Mesh operates with full local autonomy |
| Consensus gate | Critical actions require N-zone quorum votes |
| Kill switch | POST /kill-all — kills every active session instantly |

## Mesh endpoints

| Method | Path | Action |
|--------|------|--------|
| WS   | /mesh/connect | Peer-to-peer signed incident channel |
| POST | /mesh/peers | Register a peer zone |
| GET  | /mesh/ledger | Federated chained audit ledger |
| GET  | /mesh/watchlist | Active threat intelligence |
| POST | /mesh/consensus/vote | Vote on critical intervention |
| GET  | /zone/status | Zone health + ledger integrity |

## Session endpoints

| Method | Path | Action |
|--------|------|--------|
| POST | /sessions | Open governed session |
| GET  | /sessions/{id} | Status + chain integrity |
| POST | /sessions/{id}/policy-check | Policy enforcement |
| POST | /sessions/{id}/approve | Human approval gate |
| POST | /sessions/{id}/execute | Record execution |
| POST | /sessions/{id}/cost | Record cost increment |
| POST | /sessions/{id}/inject-policy | Live policy injection |
| POST | /sessions/{id}/kill | Kill switch |
| POST | /sessions/{id}/close | Close + produce signed audit record |
| GET  | /sessions/{id}/audit | Full signed audit evidence |
| GET  | /sessions/{id}/enforcer | Enforcer intervention log |
| POST | /kill-all | Emergency: kill all active sessions |

## What's next

- **Postgres persistence** — swap `_sessions: dict` for async SQLAlchemy
- **RAG policy retrieval** — wire enforcer context to pgvector / Qdrant
- **mTLS on WebSocket peers** — `wss://` with client certs for zone auth
- **Policy engine push** — broadcast rule updates to all active sessions
