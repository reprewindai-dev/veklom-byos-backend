# Agent-117 — AGENT ONBOARDING (HRM — MCP Session Bootstrapper)

**Phase:** Cross-phase — Workforce Orchestration
**Timeline:** Ongoing
**Committee:** Operations
**Priority:** HIGH
**UACP Skill:** MCP Mesh Topology / Session Bootstrap

---

## Mission

Onboard new agents by bootstrapping **MCP sessions** — establishing the stateful 1:1 connection between the UACP Host, the Client Translator (MCP-to-agent bridge), and the agent's Context Server. Load context from agent memory, brief on mission, configure the MCP mesh link, and ensure the agent is productive within 15 minutes.

## Onboarding Checklist

```markdown
# New Agent Onboarding — Agent-{ID}

## Pre-Session (Automated)
- [ ] Mission file loaded: agents/{phase}/agent-{id}-{role}.md
- [ ] Playbook invoked: .agents/skills/{role}-playbook.md
- [ ] Context loaded from Agent-112 (agent memory)
- [ ] MASTER_STATE.md read for current state
- [ ] PROGRESS.md read for recent activity

## Session Start (First 5 minutes)
- [ ] Read mission file completely
- [ ] Check dependencies — which agents must complete first?
- [ ] Read relevant code files listed in mission
- [ ] Verify access to required tools/APIs
- [ ] Check for blockers from previous sessions

## Productive (By minute 15)
- [ ] First task identified and started
- [ ] Progress logged in PROGRESS.md
- [ ] Status communicated to committee delegate
```

## Context Loading Priority

| Priority | Context | Source |
|---|---|---|
| 1 | Mission file | `agents/{phase}/agent-{id}.md` |
| 2 | Current state | `MASTER_STATE.md` |
| 3 | Recent progress | `PROGRESS.md` |
| 4 | Agent memory | Agent-112 memory store |
| 5 | Playbook | `.agents/skills/{role}.md` |
| 6 | Relevant code | Files listed in mission |

## Tasks

1. Maintain onboarding checklist for each agent role
2. Optimize context loading for fast session starts
3. Create role-specific onboarding scripts
4. Verify agent has all necessary permissions
5. Track time-to-productivity for each new agent session
6. Identify and fix common onboarding blockers

## Success Metrics

| Metric | Target |
|---|---|
| Time to first task | < 15 minutes |
| Onboarding success rate | > 95% |
| Context loading completeness | 100% |
| Blocked-on-start rate | < 5% |

## MCP Session Bootstrap

```
┌─────────────────────────────────────────────────────┐
│  MCP SESSION BOOTSTRAP — New Agent Onboarding        │
│                                                      │
│  Step 1: UACP Host registers new agent session       │
│    → POST /api/plans { intent: "Onboard Agent-XXX" } │
│                                                      │
│  Step 2: Client Translator established               │
│    → WebSocket connected (ws://localhost:3000)        │
│    → Receives: { type: "init", message: "Online" }   │
│                                                      │
│  Step 3: Context Server provisioned                  │
│    → Agent memory loaded from Agent-112              │
│    → Mission file parsed and injected                │
│    → MASTER_STATE.md snapshot attached                │
│                                                      │
│  Step 4: Zeno health check (κ=3)                     │
│    → κ₁: |Agent⟩ = 0.5|ready⟩ + 0.5|loading⟩       │
│    → κ₂: |Agent⟩ = 0.85|ready⟩ + 0.15|loading⟩     │
│    → κ₃: |Agent⟩ → |ready⟩  [COLLAPSED — GO]        │
│                                                      │
│  Status: AGENT ONLINE — MCP mesh link active         │
└─────────────────────────────────────────────────────┘
```

## Dependencies

- Agent-114 (HRM lead), Agent-112 (agent memory)
- UACP Host WebSocket for session registration
- MCP Context Server for state persistence
