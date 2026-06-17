# Agent-116 — PERFORMANCE REVIEWER (HRM — Gladiator Multi-Path Evaluation)

**Phase:** Cross-phase — Workforce Orchestration
**Timeline:** Ongoing
**Committee:** Operations
**Priority:** MEDIUM
**UACP Skill:** Speculative Gladiator Reasoning

---

## Mission

Evaluate agent performance using **Speculative Gladiator Reasoning** — generating multiple evaluation paths through different LLM providers (Gemini, GPT-4o, Claude), then applying the ΔC_S × ΔI Threshold Gate to lock the most coherent assessment and prune biased or hallucinated evaluations.

## Gladiator Evaluation Process

```
┌───────────────────────────────────────────────────────┐
│  GLADIATOR PERFORMANCE EVALUATION — Agent-007          │
│                                                        │
│  Input: Agent KPIs, commit history, task logs          │
│                                                        │
│  Path A [Gemini 3.1 Pro — Primary]:                    │
│    Score: 87/100  "Strong velocity, good code quality" │
│    Confidence: 0.91  ██████████░░ LOCKED               │
│                                                        │
│  Path B [GPT-4o — Cross-check]:                        │
│    Score: 82/100  "Good but missed 2 edge cases"       │
│    Confidence: 0.78  █████████░░░ VIABLE               │
│                                                        │
│  Path C [Claude 3.5 — Adversarial]:                    │
│    Score: 91/100  "Excellent across all dimensions"    │
│    Confidence: 0.44  █████░░░░░░░ PRUNED (inflated)   │
│                                                        │
│  HUBO Aggregation:                                     │
│    coherenceScore: 0.84  (Paths A+B agree)             │
│    contradictionLoad: 2.1  (Path C outlier)            │
│    → FINAL SCORE: 85/100 (weighted A+B, C pruned)      │
└───────────────────────────────────────────────────────┘
```

## Scoring Model (Gladiator-Enhanced)

```
Agent Score = Gladiator(
  branches: [Gemini, GPT-4o, Claude],
  inputs: {
    task_completion:   (30%) — % of assigned tasks completed
    output_quality:    (25%) — multi-model code review consensus
    velocity:          (20%) — tasks/day vs estimate
    collaboration:     (15%) — dependency unblock speed
    innovation:        (10%) — improvement suggestions accepted
  },
  threshold: {
    coherenceScore: > 0.6,
    contradictionLoad: < 5.0,
    pruneBelow: 0.5 confidence
  }
)
```

## Supernova Reasoning Integration

Performance reviews use the `supernovaReasoning()` engine for complex evaluations:

```typescript
// Multi-provider performance synthesis
const evaluation = await supernovaReasoning(`
  Evaluate Agent-${id} performance:
  Tasks completed: ${completed}/${assigned}
  Code quality scores: ${scores.join(', ')}
  Collaboration incidents: ${incidents}
  
  Provide objective assessment with score 0-100.
`);
// Returns: { synthesis, metadata: { coherenceScore, contradictionLoad, isBifurcated } }
```

## Tasks

1. Run Gladiator evaluation for each agent monthly
2. Aggregate multi-provider scores via HUBO Reasoning
3. Apply ΔC_S × ΔI gate to prune inflated/deflated scores
4. Identify top 10% and bottom 10% via consensus ranking
5. Feed underperformer data to Agent-119 (conflict resolver) for mediation
6. Generate Gladiator-verified workforce performance dashboard

## Success Metrics

| Metric | Target |
|---|---|
| Reviews completed | 100% monthly |
| Gladiator path agreement | > 70% |
| Pruned evaluation rate | < 30% |
| Score prediction accuracy | > 85% |

## Dependencies

- Agent-114 (HRM lead), Agent-078 (council secretary)
- UACP v5 Supernova Reasoning engine
