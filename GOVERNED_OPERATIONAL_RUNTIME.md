# Governed Operational Runtime Specification

## Objective

Define Veklom as a sovereign operational runtime for enterprise multi-agent systems. The product is not a chat wrapper or generic agent dashboard. It is the runtime substrate that governs execution, normalizes enterprise systems, preserves state, and records replayable telemetry inside buyer-controlled infrastructure.

## System Components

| Layer | Function | Failure Mode Resolved |
|-------|----------|-----------------------|
| Runtime reliability and telemetry | Execution graph lineage, immutable telemetry ledger, drift observation, replay controller | Basic logs cannot reconstruct multi-agent causal state |
| Unified execution and interoperability | UACP message envelopes, step composition, correlation IDs, MCP-compatible tool/resource bridge | Custom wrappers create fragmented permissions and brittle handoffs |
| Legacy ingestion and translation | SNMP, Modbus, webhooks, legacy API wrappers, on-prem/cloud schema normalization | Enterprise systems rarely expose clean modern APIs |
| Operational governance and sovereignty | Workspace isolation, policy gates, approvals, evidence immutability, budget/payment boundaries | Unconstrained agents exceed production boundaries |
| BYOS deployment | Docker/Coolify deploy, self-hosted initialization, private runtime packaging | Months-long integration blocks enterprise adoption |
| Autonomous maintenance and survivability | Dependency drift monitoring, self-healing retries, circuit breakers, dynamic API adaptation | Upstream changes cascade through agent systems |

## Execution Flow

1. A tenant submits an authenticated workload to Veklom.
2. Veklom validates workspace boundary, entitlement, wallet state, and policy context.
3. GPC compiles plan-required intent into an ordered execution graph.
4. UACP wraps agent coordination in signed, correlated, schema-validated messages.
5. Legacy adapters normalize external systems into safe tool schemas when the target environment is not API-clean.
6. `py03-irongrid` classifies the route using latency, cost, sovereignty, pressure, and replay needs.
7. Veklom executes through the selected private runtime, provider, tool, or connector.
8. The telemetry ledger records model calls, tool inputs, state transitions, cost, evidence, and lineage.
9. Failures are replayed from the immutable execution graph or rolled back to the last validated state.

## Interfaces / APIs

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/routing/operational-runtime` | Governed operational runtime substrate contract |
| GET | `/api/v1/routing/stack` | Veklom/UACP/GPC/py03-irongrid boundaries |
| GET | `/api/v1/routing/topology` | Route classes and IronGrid substrate contract |
| POST | `/api/v1/routing/decision` | Deterministic workload route classification |
| POST | `/api/v1/gpc/intent-to-plan` | Governed plan compilation |
| GET | `/api/v1/internal/uacp/summary` | UACP command-center state |
| GET | `/api/v1/marketplace/listings` | Governed marketplace listings and add-ons |

## State & Data Handling

- Veklom owns tenant runtime state, billing state, API keys, audit records, provider credentials, and execution telemetry.
- UACP owns cross-agent coordination semantics, escalation doctrine, approvals, and worker gates.
- GPC owns plan graph state, step ordering, and replay surfaces for compiled workflows.
- `py03-irongrid` owns route scoring, mesh pressure, latency topology, and data movement economics.
- Legacy adapters must emit schema-validated facts before any agent or tool can act on them.
- Regulated workflows require evidence capture before external execution.

## Failure & Degradation Rules

| Failure | Degradation Rule |
|---------|------------------|
| Telemetry ledger unavailable | Regulated and autonomous execution is blocked |
| UACP unavailable | Autonomous regulated actions are blocked; direct user-initiated safe actions may continue |
| GPC unavailable | Plan-required workloads are rejected; direct non-planned execution may continue only if policy allows |
| IronGrid unavailable | Veklom uses local deterministic route classification from `backend.core.runtime_contract` |
| Legacy adapter unavailable | Dependent tool execution is blocked instead of falling back to raw unsafe calls |
| Billing/wallet unavailable | Paid execution is blocked unless prepaid state is locally verifiable |
| Provider degraded | Runtime applies deterministic fallback only inside policy and sovereignty boundaries |

## Constraints

- No unauthenticated paid execution.
- No unmetered model/tool execution.
- No all-to-all agent chatter as a default topology.
- No regulated autonomous workflow without evidence gates.
- No legacy system mutation without a normalized schema and policy gate.
- No route decision without replayable policy version.
- No secrets in committed files.

## Deployment Notes

The production runtime runs on port `80` behind Coolify/Docker. Public HTTPS should terminate at the platform proxy and forward to the container's internal `80` port. BYOS buyers can expose the same runtime through Cloudflare Tunnel without opening server firewall ports.

The strategic product path is one undeniable sovereign flow: ingest an enterprise workload, normalize it, compile it, govern it, route it, execute it, bill it, and replay it with custody remaining inside buyer-controlled infrastructure.
