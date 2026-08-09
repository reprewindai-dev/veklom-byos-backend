# AGENT.md — DEPRECATED ALIGNMENT ENTRYPOINT

> [!IMPORTANT]
> **Use [`00_VEKLOM_BIBLE.md`](./00_VEKLOM_BIBLE.md) as the canonical Veklom architecture/runtime reference.**

The previous June 2026 infrastructure/x402 alignment guide is archived historical material. It contained service status, runner state, deployment ownership, and topology that changed over time and must not be reused as current production truth.

Current rules:

- GitHub default branch = source truth.
- Coolify = deployment/runtime configuration truth.
- Live endpoint behavior = final product verification.
- Host port `8000` is currently owned by Coolify; internal container port `8000` may still be used behind Docker/Traefik.
- Do not allocate host `3000` until its current reservation is explicitly reverified.
- Use Coolify UI/API/MCP for Coolify management; SSH only for direct host/container verification or operations.
- No production claim without current evidence.

Historical index: [`docs/archive/2026-08-09/README.md`](./docs/archive/2026-08-09/README.md).
