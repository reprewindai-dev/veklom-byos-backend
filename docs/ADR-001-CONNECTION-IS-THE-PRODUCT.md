# ADR-001: Connection is the Product

## Status
Approved

## Context
Historically, the Veklom architecture accumulated multiple competing conceptual top-level products (e.g., "Covenant," various SDKs, disparate data planes). This drift led to scattered execution authority, circular dependencies, and a lack of canonical evidence. To stabilize the platform and ensure deterministic, governed execution across physical nodes and settlement layers, a singular product philosophy is required.

## Decision
We establish the following unalterable doctrine for the canonical Veklom architecture:

1. **Connection is the Product**: The Trust Connection is the sole aggregate root representing the product. The SDK is merely its machine-native embodiment.
2. **Interlink is the Fabric**: The distributed operating fabric that classifies intent, negotiates, and coordinates capability graphs.
3. **Amphoteric is the Runtime**: The local participation runtime representation of the fabric.
4. **CAPPO Authorizes**: The sole final authority for consequential execution, credentials, and side-effects (LAW 0).
5. **PGL Proves**: Identity, lineage, and canonical evidence are sealed in PGL/Gnome Ledger.
6. **VNP Measures**: Operational measurement and telemetry across canonical physical nodes.
7. **VABP Certifies**: Authorized benchmark certification across 4 pillars (1,000 points).
8. **x402 Settles**: Machine-to-machine settlement strictly bound to executions.

### Legacy Terminology
- **Covenant**: The term "Covenant" is hereby demoted. It may remain strictly as a historical codename, a compatibility alias, or an internal lifecycle profile state. It must **never** be presented as a competing top-level product or execution authority.

## Consequences
- All repositories must align their schemas, language, and behavior to this doctrine.
- The Trust Connection lifecycle acts as the foundational state machine for all integrations.
- Code generation (SDKs, GraphQL schemas) will pivot around the capabilities granted within a specific Trust Connection context.
