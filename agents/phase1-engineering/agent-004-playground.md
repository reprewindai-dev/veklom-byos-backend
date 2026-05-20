# Agent-004 — PLAYGROUND ENGINEER

**Phase:** 1 — Complete the Core Product
**Timeline:** Days 1–4
**Committee:** Engineering
**Priority:** HIGH

---

## Mission

Enhance the playground demo experience to convert visitors into users. Add preset prompts, share functionality, and deploy CTAs. The playground currently works (SSE streaming via `/demo/pipeline/stream`) but lacks engagement features.

## Current State

- Playground SSE streaming works — ✅
- Rate-limited public demo (no auth required) — ✅
- **GAP:** No preset demo prompts showcasing platform capabilities
- **GAP:** No "share this run" functionality
- **GAP:** No "deploy this" CTA linking to signup/pipeline creation
- **GAP:** No prompt history or favorites

## Tasks

1. **Preset Prompts** — add 10+ categorized preset prompts:
   - Data Analysis: "Analyze quarterly sales trends and forecast Q3"
   - Code Review: "Review this Python function for security vulnerabilities"
   - Content: "Write a product description for an enterprise AI tool"
   - Compliance: "Check if this data processing meets GDPR requirements"
   - Research: "Summarize recent advances in transformer architecture"
2. **Share Functionality**:
   - Generate shareable URL with encoded prompt + output
   - Copy-to-clipboard button
   - Social share buttons (Twitter/X, LinkedIn)
   - OG meta tags for shared playground runs
3. **Deploy CTA**:
   - "Deploy as Pipeline" button after a successful run
   - Links to signup if not authenticated
   - Links to pipeline creation if authenticated
   - Shows estimated cost per run
4. **Prompt History**:
   - Store last 20 prompts in localStorage
   - Quick-access dropdown
   - Star/favorite prompts
5. **Visual Enhancements**:
   - Typing animation on output
   - Token count display
   - Latency indicator
   - Model info badge

## Success Metrics

| Metric | Target |
|---|---|
| Preset prompts available | 10+ |
| Share URL generation | Working |
| Deploy CTA conversion | Track baseline |
| Prompt history | 20 items |
| Average session duration | Increase 30%+ |

## Daily Checklist

- [ ] Day 1: Preset prompts + prompt history (localStorage)
- [ ] Day 2: Share functionality + OG meta tags
- [ ] Day 3: Deploy CTA + cost estimation
- [ ] Day 4: Visual enhancements + PR

## Dependencies

- Agent-000 (MASTER_STATE.md)
- Agent-003 (UX components — loading, toasts)
- Agent-005 (onboarding flow after deploy CTA)

## Key Files

- `frontend/workspace/src/pages/Playground.tsx`
- `backend/apps/api/routers/demo_pipeline.py`

## Playbook

```
Repo: byosbackened
Branch: main
Read MASTER_STATE.md first
Focus: frontend/workspace/src/pages/Playground.tsx
Test: npm run dev → localhost playground page
```
