# 00 — VEKLOM BIBLE — READ FIRST

> **This file is mandatory context for every human or AI working in this repository.**
> Canonical operational source: `reprewindai-dev/veklom-ops-command/00_VEKLOM_BIBLE.md`.
> This local copy intentionally excludes management addresses, credentials, private keys, and ephemeral runtime identifiers.

## What Veklom is now

Veklom is the **sovereign AI capability control plane / runtime authority layer**. It governs capability, not a permanent fleet of privileged agents.

Canonical lifecycle:

`Resolve capability → Bind policy + authority → Issue scoped grant → Instantiate ephemeral worker/runtime → Execute → Record evidence → Revoke → Destroy → Observe / Settle when applicable`

The stable object is the capability contract: inputs, outputs, preconditions, effects, authority requirements, resource/budget bounds, recovery/revocation behavior, evidence requirements, and version compatibility.

## Truth hierarchy

1. Live endpoint/public behavior.
2. Coolify runtime state.
3. GitHub default branch source.
4. Persisted + verified PGL/Gnomledger evidence.
5. Documentation.

A merged PR is not deployment proof. A screenshot or pasted log is not proof of every downstream claim. Synthetic/demo data must never be presented as production evidence.

## Component boundaries

- **VCCP / UCH / UCR:** capability control, packaging, resolution, orchestration, lifecycle.
- **cAPI / Covenant:** governed connection/discovery layer.
- **CAPPO:** fail-closed runtime authorization / LAW 0 boundary.
- **ABIDE:** blueprint and bounded execution-contract compilation.
- **Lockerphycer:** secret/key security domain; do not claim HSM/TEE guarantees unless proven by the deployed implementation.
- **BYOS:** sovereign execution substrate/provider.
- **Gnomledger / PGL:** evidence, provenance, lineage, hash-linked verification. Default claim is **tamper-evident**, not magically undeletable.
- **VNP:** measurement/telemetry/observation evidence.
- **RepoGate:** repository/capability intake and security/policy gating.
- **Veklom ID:** identity/trust evidence.
- **x402:** settlement/payment integration where verified; payment is not execution proof.

## Standalone products vs Capability OS

A Veklom-built product may also be sold standalone. Its standalone UI is **not** embedded wholesale into Capability OS.

Project Genome Ledger, ABIDE, RepoGate, Apex, and similar products can have independent product surfaces. Inside Veklom, their reusable domain logic appears as native Veklom capabilities and custom OS surfaces.

## Operations doctrine

- GitHub default branch is source truth; Coolify is deployment/runtime truth.
- Secrets belong in deployment secret management, never committed files.
- Use Coolify UI/API for Coolify resource management; reserve SSH for direct host/container verification or operations that cannot be safely done through Coolify.
- `localhost` means the current container/process. Use stable service DNS/config for inter-container calls.
- Internal application ports such as `3000` and `8000` are allowed behind Traefik. The old blanket prohibition on those ports is retired; avoid conflicting host-published ports instead.
- Do not hard-code ephemeral Coolify container identifiers into product code.

## Evidence language

Use: `VERIFIED_LIVE`, `VERIFIED_REPO`, `CONFIGURED`, `LAST_KNOWN`, `TARGET`, `UNVERIFIED`, `DEMO`, `ARCHIVED`.

Do not use unsupported claims such as “100% real”, “production ready”, “SOC 2 Type II compliant”, “HIPAA compliant”, “hardware enclave protected”, “prompt injection eliminated”, or “immutable” without independent evidence for the exact claim.

## Documentation rule

This Bible supersedes older Golden Bible, agent-alignment, topology, deployment-authority, and port-doctrine documents wherever they conflict. Repo-specific docs may describe local APIs/build/test behavior, but cross-repo architecture and deployment ownership defer to the canonical Bible.
