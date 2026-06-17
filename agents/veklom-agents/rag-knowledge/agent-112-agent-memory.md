# Agent-112 — AGENT MEMORY (RAG)

**Phase:** Cross-phase — Knowledge
**Timeline:** Ongoing
**Committee:** Engineering
**Priority:** HIGH

---

## Mission

Maintain shared memory and context across all 100+ agents. Store agent decisions, learnings, and state so agents in future sessions can pick up where previous agents left off. This is the institutional memory of the workforce.

## Memory Architecture

```
┌─────────────────────────────────────────┐
│           Agent Memory Store             │
│                                          │
│  ┌─────────────┐  ┌──────────────────┐  │
│  │ Short-Term   │  │ Long-Term        │  │
│  │ (Session)    │  │ (Persistent)     │  │
│  │              │  │                  │  │
│  │ - Current    │  │ - Decisions log  │  │
│  │   task state │  │ - Learnings      │  │
│  │ - WIP notes  │  │ - Patterns       │  │
│  │ - Blockers   │  │ - Best practices │  │
│  └─────────────┘  └──────────────────┘  │
│                                          │
│  ┌──────────────────────────────────┐   │
│  │ Episodic Memory                  │   │
│  │                                   │   │
│  │ - "Agent-001 tried X, it failed" │   │
│  │ - "Agent-010 found Y works best" │   │
│  │ - "Agent-050 learned Z about     │   │
│  │    pricing conversion"           │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

## Memory Types

| Type | Scope | Persistence | Example |
|---|---|---|---|
| Working Memory | Single session | Temporary | "Currently fixing auth bug" |
| Episodic Memory | Cross-session | Persistent | "Last time, Redis config was the issue" |
| Semantic Memory | Permanent | Persistent | "Stripe webhook URL format is..." |
| Procedural Memory | Permanent | Persistent | "To deploy, run X then Y then Z" |

## Storage

- **Short-term:** PROGRESS.md + agent session notes
- **Long-term:** Knowledge notes (Devin knowledge system)
- **Episodic:** `agents/memory/` directory with structured logs
- **Procedural:** `.agents/skills/` playbooks

## Tasks

1. Design memory schema for agent state persistence
2. Build memory write API (agents store learnings)
3. Build memory read API (agents retrieve context)
4. Implement memory pruning (remove stale/contradicted entries)
5. Generate memory health report (coverage, staleness)
6. Manage memory permissions per committee

## Success Metrics

| Metric | Target |
|---|---|
| Agent context handoff success | > 90% |
| Memory staleness | < 7 days |
| Cross-session continuity | Seamless |
| Memory conflicts resolved | All |

## Dependencies

- Agent-108 (RAG lead), Agent-000 (commander — memory governance)
