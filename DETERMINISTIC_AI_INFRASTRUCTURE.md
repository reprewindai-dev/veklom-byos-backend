# Deterministic AI Infrastructure Doctrine

## Objective

Codify the source-of-truth split between Veklom, UACP, GPC, and `py03-irongrid`.

Veklom is not positioned as an AI assistant. Veklom is sovereign runtime infrastructure for governed,
paid, tenant-isolated AI execution.

This doctrine sits under the broader governed operational runtime specification:
[GOVERNED_OPERATIONAL_RUNTIME.md](./GOVERNED_OPERATIONAL_RUNTIME.md).

## System Components

| Component | Role | System Boundary |
|-----------|------|-----------------|
| Veklom BYOS Backend | Sovereign Runtime Infrastructure | Auth, tenants, billing, runtime execution, audit, provider routing contracts |
| UACP | Constitutional Coordination Layer | Operator hierarchy, governance gates, escalation doctrine, worker coordination |
| GPC | Deterministic Planning / Execution Compiler | Intent-to-plan compilation, graph execution, replay state, policy gate ordering |
| `py03-irongrid` | Deterministic Routing Mesh | Route scoring, pressure topology, latency routing, data movement economics |

## Execution Flow

1. A tenant submits an authenticated workload to Veklom.
2. Veklom validates entitlement, wallet state, workspace boundary, and request policy.
3. GPC compiles governed intent into an ordered execution graph when the workload requires planning.
4. UACP applies constitutional gates for autonomous, regulated, or cross-agent execution.
5. `py03-irongrid` supplies deterministic routing class, pressure, and substrate path.
6. Veklom executes through the selected provider or private runtime.
7. Veklom records billing, usage, evidence, and audit hash state.

## Interfaces / APIs

Runtime doctrine and routing contracts are exposed through:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/routing` | Runtime routing contract |
| GET | `/api/v1/routing/topology` | Route classes and `py03-irongrid` substrate contract |
| GET | `/api/v1/routing/economics` | Token, latency, verification, and routing economics model |
| GET | `/api/v1/routing/operational-runtime` | Governed operational runtime substrate contract |
| GET | `/api/v1/routing/stack` | Repo responsibility boundaries |
| POST | `/api/v1/routing/decision` | Deterministic workload route classification |
| POST | `/api/v1/gpc/intent-to-plan` | Governed plan compilation |
| GET | `/api/v1/internal/uacp/summary` | UACP control-plane backend summary |
| GET | `/api/v1/internal/operators` | UACP operator registry |

## State & Data Handling

- Veklom owns tenant data, execution records, billing state, provider credentials, and audit records.
- UACP owns governance state and escalation semantics.
- GPC owns plan graph state and execution replay surfaces.
- `py03-irongrid` owns routing pressure, topology inputs, and substrate scoring.
- Cross-boundary calls must pass explicit contracts. No layer may infer another layer's authority.

## Failure & Degradation Rules

| Failure | Degradation |
|---------|-------------|
| UACP unavailable | Veklom blocks autonomous regulated actions and allows only direct user-initiated execution within entitlement limits |
| GPC unavailable | Veklom rejects plan-required workloads and allows direct non-planned execution only |
| `py03-irongrid` unavailable | Veklom uses deterministic local fallback route classification from `backend.core.runtime_contract` |
| Private runtime unavailable | Veklom falls back only if policy permits non-sovereign providers |
| Evidence capture unavailable | Regulated execution is blocked |
| Billing unavailable | Paid execution is blocked unless prepaid wallet state is locally verifiable |

## Constraints

- No unauthenticated paid execution.
- No unmetered model execution.
- No regulated autonomous run without evidence gates.
- No all-to-all agent chatter as a default topology.
- No route decision without replayable policy version.
- No live secrets in committed files.

## Deployment Notes

The backend exposes deterministic routing contracts without requiring `py03-irongrid` to be deployed locally.
When `py03-irongrid` is available, it should become the upstream route scorer behind the same `/api/v1/routing`
contract instead of changing client-facing APIs.
