# MCPAPI v2 — Current-Truth Classification

**Status:** CURRENT-TRUTH COMPANION / NOT A NEW CONFORMANCE SEAL  
**Date:** 2026-08-30  
**Scope:** Historical MCPAPI v2 package in this repository

## Why this document exists

The June 2026 MCPAPI package contains useful architecture, packaging, deployment, and productization ideas. It also contains claims and topology assumptions that must not be inherited as current Veklom truth merely because the package labels itself "Complete & Production Ready."

This companion preserves the useful material while preventing historical documentation from widening current architectural or conformance claims.

## Current Veklom interpretation

Veklom's current category is **Machine Authority Infrastructure**.

The constitutional boundary is:

> **Capability without authority produces no consequence.**

The governing chain is:

`intent → policy → identity → bounded authority → execution → consequence → evidence → reconciliation`

Downstream authority may preserve or attenuate upstream authority; it may not silently widen it:

`A(n+1) ⊆ A(n)`

MCPAPI material should therefore be interpreted as an integration/reference layer beneath this doctrine, not as a parallel authority engine.

## What remains valuable from MCPAPI v2

### 1. Packaging and adoption model

The package's `START_HERE` entry point, role-specific reading paths, quick reference, implementation guide, operations guide, and deployment guide are a strong productization pattern. Current Veklom should keep the principle: one obvious entry point, progressively deeper material, and separate paths for decision makers, engineers, and operators.

### 2. Consequence pipeline decomposition

The historical nine-phase flow usefully separates identity/security, capability/policy, safety checks, budget, approvals, execution, evidence, audit, and response. In current Veklom these are not independent authority domains. They are subordinate stages around the canonical machine-authority boundary.

### 3. Layer concepts

The historical Safety / Intelligence / Governance split can remain useful internally:

- **Safety** may detect or suppress risk but must never mint authority.
- **Intelligence** may estimate cost, anomaly, or risk but must never mint authority.
- **Governance** may compile or narrow policy but consequence still requires canonical authority enforcement.

No score, anomaly model, approval UI, metadata field, or learned state may independently widen a CapabilityLease or other upstream cryptographic authority.

### 4. Deployment profiles

The historical package describes Docker Compose, Kubernetes, standalone/edge, and managed-service paths. These are deployment profiles, not constitutional architecture. Current production topology must be established from live deployment evidence rather than inherited from these documents.

A managed offering, if used, must remain optional and must not erase customer-controlled authority, evidence, or sovereign execution properties.

### 5. Offline and degraded operation

The historical idea of retaining local evidence and reconciling later is directionally compatible with current Veklom, but only when bounded offline authority, replay resistance, epoch monotonicity, budget monotonicity, and reconciliation semantics are actually enforced and evidenced. Availability must never be achieved by silently bypassing authority or evidence requirements.

## Claims that are historical, unverified, or stale until re-proven

The following statements in the June package are **not current production facts merely because they appear in documentation**:

- "Complete & Production Ready"
- stated throughput and latency ranges
- 99.9% / 100% uptime targets or outcomes
- design-partner and MRR targets
- Kubernetes readiness or Kubernetes as canonical production
- PostgreSQL/Redis as mandatory current architecture
- managed-service availability
- every-request anomaly learning / risk scoring as deployed behavior
- PGL described as universally "immutable" without the applicable evidence tier and verifier context
- any statement that every named reference implementation is currently present, wired, tested, or deployed

These require source-observed, test-observed, or live-runtime evidence at the relevant current SHA and deployment profile.

## Repository consistency finding

`START_HERE.md` and `MCPAPI_PROJECT_MANIFEST.md` describe `mcpapi-veklom-integration.ts` as a delivered reference implementation. At the time of this classification, that root path is not present on `main` and GitHub returns 404 for it.

Therefore the package should not currently be represented as "no missing pieces" without either restoring the referenced artifact from authoritative source history or correcting the historical manifest to identify it as absent/reference-only.

This is a documentation/package-integrity issue; it is not evidence that the integration concept itself is invalid.

## Canonical integration rule

MCPAPI/cAPI/connector layers may provide transport, identity context, request integrity, routing, trust data, observation, receipts, and evidence support. They must not become a second authority engine.

For any real-world consequence:

`effective consequence authority ⊆ mounted/bound authority ⊆ upstream cryptographic authority`

The consequence path must pass the canonical CAPPO authority boundary, and the evidence returned to the product must be bound to the actual execution rather than synthesized by the UI or integration layer.

## Product lesson extracted from the June package

The strongest idea in the old package is not the phrase "Safety + Intelligence + Governance." It is the reduction of integration friction into a clear adoption package.

Current Veklom should apply that lesson to Activation v1:

`connect → bind authority → execute allowed consequence → prove intentional denial → inspect evidence`

The goal is to make sophisticated machine authority feel operationally simple without simplifying away the cryptographic boundary.

## Evidence discipline

Use the following classifications when referencing MCPAPI material:

- **HISTORICAL_REFERENCE** — useful design/product material from the June package.
- **SOURCE_OBSERVED** — present in a current repository SHA.
- **TEST_OBSERVED** — executed by a reproducible test/harness at a recorded SHA.
- **LIVE_OBSERVED** — reproduced against the actual deployed substrate.
- **SEALED** — only where a separately defined immutable conformance/evidence seal exists.

A stronger classification must never be inferred from a weaker one.

## Non-goal

This document does not create a new foundational proof gate, reopen an existing seal, or introduce a parallel Veklom architecture. It exists to harvest MCPAPI's useful ideas while constraining stale claims to their actual evidence level.
