# Embedded Control Plane — Reference Only

This directory is a historical/reference copy of an earlier Veklom control-plane implementation. It is **not a canonical build or deployment surface**.

The canonical Governance Portal / Capability OS frontend is maintained in:

`reprewindai-dev/veklom-FRONTEND`

Do not deploy, publish, or use `apps/control-plane` as a fallback control plane. Its `dev`, `build`, and `start` scripts intentionally fail closed so an operator, scanner, or automation cannot accidentally promote this duplicate source into a second runtime.

The files remain here only while any useful historical UI/reference material is migrated or audited. New frontend/runtime integration work belongs in the canonical frontend repository and must consume the canonical BYOS/cAPI/CAPPO contracts rather than creating a parallel authority or presentation source.

## Source-truth boundary

- Canonical frontend source: `reprewindai-dev/veklom-FRONTEND`
- Canonical BYOS API/runtime source: this repository's backend
- This directory: reference-only / non-deployable
- Runtime deployment/listener state: must be verified independently from source code

## Static inspection

`lint` and `typecheck` remain available only for inspecting or migrating the historical source. Any command that would run or build the embedded application exits non-zero by design.
