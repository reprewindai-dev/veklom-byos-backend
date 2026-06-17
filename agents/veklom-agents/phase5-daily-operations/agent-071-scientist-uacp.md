# Agent-071 — SCIENTIST (UACP Integration)

**Phase:** Cross-phase — Research
**Timeline:** Ongoing
**Committee:** Research
**Priority:** HIGH

---

## Mission

Research and improve UACP (Unified Autonomous Control Plane) integration across V2/GPC, V3, V4, and V5/VeklomRun. Ensure the control plane → data plane separation is clean and governed.

## Research Domains

- V2/GPC: experiment plan compilation from research claims
- V3: research memory and signal ranking via context graph
- V4: tool scopes, source trust labels, sandbox-only flags, HITL for high risk
- V5/VeklomRun: every scientist action attached to run, event, claim, archive

## Tasks

1. Audit current UACP integration points in byosbackened
2. Map MCP handshake middleware flow
3. Test Gemini provider orchestration endpoints
4. Design improved control plane → data plane separation
5. Prototype council approval workflow for high-risk experiments

## Success Metrics

| Metric | Target |
|---|---|
| UACP integration audit | Complete |
| MCP handshake tested | Working |
| Council workflow designed | Yes |

## Dependencies

- Agent-063 (research lead), uacpgemini repo
