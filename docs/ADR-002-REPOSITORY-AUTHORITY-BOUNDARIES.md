# ADR-002: Repository Authority Boundaries

## Status
Approved

## Context
With the shift to the Canonical Architecture where "Connection is the Product," there needs to be strict separation of concerns across the Veklom repositories to prevent circular authority and fragmented sources of truth. Previous iterations allowed overlapping responsibilities (e.g., CAPPO evaluating CAPPO, cAPI maintaining state, PGL using mocked receipts).

## Decision
The following repository boundaries are absolute and cannot be crossed:

### 1. `reprewindai-dev/veklom-byos-backend`
**Role:** Persistent Aggregate and Data Plane
- **Owns:** Workspace and tenant data, the persistent Trust Connection aggregate (schemas, state transitions, versioning), the Connection saga, RLS-backed data plane, bounded workload operations, and capability lane assignments.
- **Constraints:** Must use normalized schemas. The local CAPPO engine inside BYOS is no longer the final authority. It must be converted into an adapter/context loader for the `cappo-backend` or deprecated entirely.

### 2. `reprewindai-dev/cAPI`
**Role:** Interlink Amphoteric Fabric Gateway
- **Owns:** Capability discovery, OpenAPI-to-MCP translation, negotiation and composition, Amphoteric protocol presentation, and global capability graph coordination.
- **Constraints:** Cannot use process-local memory as the source of truth for capabilities or servers. Persistent records must live in BYOS. cAPI may cache them, but does not own them.

### 3. `reprewindai-dev/cappo-backend`
**Role:** Final Execution Authority
- **Owns:** Sole final authority for consequential execution (LAW 0), ExecutionIdentity, Execution Authorization Tokens (EAT), credential release, side-effect release, budgets, approvals, quarantine, and execution attestation.
- **Constraints:** Must eliminate circular authority. Once a decision is made, it cannot call another CAPPO evaluator. Lane 3 provider calls are prohibited without an APPROVED CAPPO result.

### 4. `reprewindai-dev/veklom-vnp`
**Role:** Physical Measurement and Assurance
- **Owns:** Signed physical telemetry, node registry (with separate UUIDs, locations, and signing keys), signed heartbeats, operational VNP measurements, five-node state compiler, evidence confidence, Performance Assurance, and bonds.
- **Constraints:** VNP proposes evidence outcomes. It never controls unrestricted wallets or directly performs slashing.

### 5. `reprewindai-dev/veklom-FRONTEND`
**Role:** Presentation Layer
- **Owns:** Presentation and operator actions only.
- **Constraints:** Cannot construct hardcoded statuses or topologies. Must consume the canonical backend capability/status manifest. CAPI and CAPPO must be displayed as separate operational entities.

## Consequences
- The TrustConnection implementation in BYOS will be strictly normalized.
- Any direct mutation attempts bypassing CAPPO in Lane 3 will fail.
- All repositories must respect these namespaces and interfaces.
