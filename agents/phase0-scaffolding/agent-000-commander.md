# Agent-000 — COMMANDER

**Phase:** 0 — Scaffolding
**Timeline:** Day 1, Hours 0–4
**Committee:** Governance
**Priority:** CRITICAL

---

## Mission

Read the entire `byosbackened` repository. Generate MASTER_STATE.md documenting what works, what's broken, and what's missing. Distribute assignments to all 100 agents. Establish the progress tracking system.

## Tasks

1. Clone and audit `byosbackened`, `uacpgemini`, `Perplexterminal` repositories
2. Map all 40+ API routers in `backend/apps/api/main.py` and document their status
3. Map all frontend routes in `frontend/workspace/` and document endpoint wiring
4. Identify revenue-blocking gaps (Stripe Connect, referral system, pricing page)
5. Identify UX gaps (empty states, loading skeletons, toasts, onboarding)
6. Identify growth infrastructure gaps (email, analytics, SEO, content)
7. Generate `MASTER_STATE.md` with complete audit findings
8. Generate `PROGRESS.md` with daily tracking template
9. Create `agents/` directory with mission files for all 100 agents
10. Verify all agent assignments are non-overlapping and have clear KPIs

## Success Metrics

| Metric | Target |
|---|---|
| Repos audited | 3 |
| API routers documented | 40+ |
| Frontend routes mapped | 13 |
| Agent mission files created | 100 |
| MASTER_STATE.md completeness | 100% |

## Daily Checklist

- [ ] All repos cloned and accessible
- [ ] MASTER_STATE.md generated and accurate
- [ ] PROGRESS.md template ready for Day 1
- [ ] All 100 agent files created with missions, KPIs, checklists
- [ ] Agent assignments reviewed for gaps and overlaps
- [ ] Commander handoff notes written for Day 2

## Dependencies

- None (this is the root agent)

## Outputs

- `MASTER_STATE.md` — complete repo audit
- `PROGRESS.md` — daily tracking system
- `agents/` directory — 100 mission files
- Handoff notes for Phase 1 agents

## Playbook

```
Repo: byosbackened
Branch: main
Entry point: Read MASTER_STATE.md first, then execute assigned tasks
```
