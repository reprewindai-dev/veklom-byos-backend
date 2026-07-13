# Veklom Canonical Architecture

## 1. Overview
This document represents the unified architectural truth lock for the Veklom platform. It establishes the mandatory boundaries for components across all repositories, enforcing that "Connection is the Product" and ensuring that no single component attempts to bypass the strict separation of concerns.

## 2. Component Authority

### 2.1 The Product: Trust Connection
- The Trust Connection is the top-level aggregate and product.
- It is managed persistently in `veklom-byos-backend`.
- It dictates capability lane assignments and execution boundaries.
- The SDK is strictly a generated machine-native embodiment of a connection, not an independent layer.

### 2.2 The Fabric: Interlink
- **Component:** Ambient Interlink cAPI (`reprewindai-dev/cAPI`)
- **Role:** The distributed operating fabric. It handles intent classification, negotiation, capability composition, and public-facing gateway duties.
- **Rules:** Interlink cannot invent capabilities; it only discovers and routes them based on persistent truths stored in BYOS.

### 2.3 The Runtime: Amphoteric
- **Component:** Amphoteric Runtime
- **Role:** The local participation runtime that represents agents connecting to the fabric.

### 2.4 The Authority: CAPPO
- **Component:** CAPPO Backend (`reprewindai-dev/cappo-backend`)
- **Role:** The sole final authority for consequential execution (LAW 0).
- **Rules:** It controls all Execution Authorization Tokens (EAT) and side-effect releases. Lane 3 executions CANNOT proceed without explicit CAPPO approval. It is purely deterministic and acts without circular authority logic.

### 2.5 The Evidence: PGL & Genome Ledger
- **Component:** IdentityRAG / Genome Ledger
- **Role:** Manages identity, lineage, and canonical evidence.
- **Rules:** Requires persistent signing keys (no simulated fallback). Seals the cryptographic proof of all transactions and connection states.

### 2.6 The Measurement: VNP
- **Component:** Veklom Network Protocol (`reprewindai-dev/veklom-vnp`)
- **Role:** Publishes signed physical telemetry and measures operational behavior across exactly five canonical Hetzner nodes.
- **Rules:** Cannot slash wallets directly. Proposes evidence and evaluates bounded states through the deterministic compiler.

### 2.7 The Certification: VABP
- **Component:** Veklom Authorized Benchmark Protocol
- **Role:** Certifies authorized benchmark outcomes across 4 pillars. Distinct and strictly decoupled from VNP.

### 2.8 The Settlement: x402
- **Component:** x402
- **Role:** Handles machine-to-machine settlement strictly bound to connection and execution identifiers.

## 3. Maturity Framework: API-m-FAMM
API-m-FAMM is the research-backed maturity baseline used to assess connection-management practices (lifecycle, security, performance, observability). It signals `connection_maturity` exclusively and must never alter VNP physical performance measurements or VABP benchmark scores.

## 4. Status Namespaces
All repositories must adopt and strictly adhere to the following namespaces. Frontend interfaces are forbidden from hardcoding arbitrary statuses.

- `readiness_status`
- `connection_state`
- `execution_state`
- `policy_decision`
- `measurement_state`
- `settlement_stage`
- `verification_result`

## 5. Deployment Mandate
All infrastructure must target Dockerized services on Hetzner via Coolify. Previous mixed-cloud deployment models are deprecated and superseded by this document.
