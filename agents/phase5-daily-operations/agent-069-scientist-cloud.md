# Agent-069 — SCIENTIST (Cloud & Runtime)

**Phase:** Cross-phase — Research
**Timeline:** Ongoing
**Committee:** Research
**Priority:** MEDIUM

---

## Mission

Research cloud and runtime architecture: BYOS runtime placement, Coolify/Cloudflare split optimization, private cloud templates, local model routing, GPU utilization, autoscaling queues.

## Research Domains

- Optimal runtime placement (Hetzner/Coolify vs Cloudflare Workers)
- Private cloud deployment templates
- On-prem execution models
- Local model routing optimization
- GPU utilization and sharing strategies
- Autoscaling queue design
- Zero external-call mode for air-gapped environments

## Tasks

1. Benchmark Coolify vs Cloudflare Workers for different workload types
2. Design private cloud deployment templates (Docker Compose, K8s)
3. Test local model routing with Ollama cluster
4. Evaluate GPU sharing strategies for multi-tenant inference
5. Prototype autoscaling queue for pipeline execution

## Success Metrics

| Metric | Target |
|---|---|
| Runtime experiments completed | 2+ |
| Deployment template created | 1+ |
| GPU utilization improvement | > 20% |

## Dependencies

- Agent-063 (research lead), Agent-007 (performance handoff)
