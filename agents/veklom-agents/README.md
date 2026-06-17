# Veklom Autonomous Agent Task Force (130 Agents)

This directory contains mission files for all 130 agents in the Veklom Sovereign AI Hub workforce.

## Agent Count Model

| Tier | Range | Count | Description |
|------|-------|-------|-------------|
| **Operational** | 000–113 | 114 | Production agents — engineering, vendors, growth, operations, research, QA, browser, crawler, visual, security, RAG, HRM |
| **Control/Council** | 114–119 | 6 | Governance control agents — HRM lead, capacity planner, performance reviewer, onboarding, analyst, conflict resolver |
| **Special Governance** | 120–129 | 10 | Supreme governance agents — Zeno, Gladiator, SSRN/ArXiv, Swarm, Quantum-Hybrid, RAG Sovereign, Listener, HRM Supreme, Sentinel Prime, Neural Orchestrator |
| **TOTAL** | | **130** | |

> **114 operational + 6 control/council + 10 special governance = 130 total**

## Directory Structure

```
agents/
├── README.md                              ← You are here
├── phase0-scaffolding/                    ← Day 1, Hours 0–4
│   └── agent-000-commander.md
├── phase1-engineering/                    ← Days 1–4
│   ├── agent-001-stripe-connect.md
│   ├── agent-002-referral-system.md
│   ├── agent-003-ux-completion.md
│   ├── agent-004-playground.md
│   ├── agent-005-onboarding.md
│   ├── agent-006-api-docs.md
│   ├── agent-007-performance.md
│   └── agent-008-security.md
├── phase2-vendor-acquisition/             ← Days 3–10
│   ├── agent-010 through 029 (20 vendor hunters)
│   ├── agent-030-vendor-outreach-lead.md
│   └── agent-031-vendor-success.md
├── phase3-user-acquisition/               ← Days 3–14
│   ├── agent-040-seo.md through agent-044-product-hunt.md
├── phase4-retention-revenue/              ← Days 7–14
│   ├── agent-050-pricing.md through agent-053-analytics.md
├── phase5-daily-operations/               ← Ongoing
│   ├── agent-060 through 062 (operations)
│   ├── agent-063 through 072 (research / Special Ops)
│   ├── agent-073 through 077 (committee delegates / governance)
│   ├── agent-078-council-secretary.md
│   ├── agent-079-compliance-officer.md
│   ├── agent-080 through 089 (QA & testing)
│   ├── agent-090 through 093 (browser agents — hands/arms)
│   └── agent-094 through 097 (crawler agents — legs)
├── eyes-visual/                           ← Visual monitoring (Eyes)
│   ├── agent-098-visual-lead.md
│   ├── agent-099-visual-regression.md
│   ├── agent-100-dashboard-watcher.md
│   └── agent-101-accessibility-auditor.md
├── security-force/                        ← Security team
│   ├── agent-102-security-commander.md
│   ├── agent-103-perimeter-guard.md
│   ├── agent-104-auth-sentinel.md
│   ├── agent-105-data-guardian.md
│   ├── agent-106-threat-hunter.md
│   └── agent-107-incident-responder.md
├── rag-knowledge/                         ← RAG & Knowledge agents
│   ├── agent-108-rag-lead.md
│   ├── agent-109-document-indexer.md
│   ├── agent-110-semantic-search.md
│   ├── agent-111-knowledge-synthesizer.md
│   ├── agent-112-agent-memory.md
│   └── agent-113-support-rag.md
├── hrm-workforce/                         ← HRM & Workforce Management
│   ├── agent-114-hrm-lead.md
│   ├── agent-115-capacity-planner.md
│   ├── agent-116-performance-reviewer.md
│   ├── agent-117-agent-onboarding.md
│   ├── agent-118-workforce-analyst.md
│   └── agent-119-conflict-resolver.md
└── special-governance/                    ← Supreme Governance (10 special agents)
    ├── agent-120-zeno-enforcer.md         (ZENO, SENTINEL)
    ├── agent-121-gladiator-optimizer.md   (GLADIATOR, ARMS)
    ├── agent-122-ssrn-arxiv-discoverer.md (SCIENTIST, EYES)
    ├── agent-123-swarm-architect.md       (GLADIATOR, ZENO, HRM)
    ├── agent-124-quantum-hybrid-builder.md (SCIENTIST, GLADIATOR)
    ├── agent-125-rag-sovereign.md         (RAG, ZENO, EYES)
    ├── agent-126-listener-nexus.md        (LISTENER, EYES, RAG)
    ├── agent-127-hrm-supreme.md           (HRM, ZENO, GLADIATOR)
    ├── agent-128-sentinel-prime.md        (SENTINEL, ZENO, EYES)
    └── agent-129-neural-orchestrator.md   (GLADIATOR, ZENO, HRM, RAG, LISTENER)
```

## Agent Categories

### Core Workforce (Agents 000–062)
Original plan — engineering, vendor acquisition, user growth, retention, operations.

### Research & Special Ops (Agents 063–072)
Scientists: latency, memory, governance, telemetry, data transfer, cloud, marketplace, UACP, evidence.

### Governance (Agents 073–079)
Committee delegates (engineering, growth, operations, research, revenue), council secretary, compliance officer.

### QA & Testing (Agents 080–089)
QA lead + specialists: auth, payments, marketplace, pipelines, frontend E2E, API, performance, security, data integrity.

### Browser Agents — Hands & Arms (Agents 090–093)
Playwright/CDP agents that interact with UIs: signup flows, marketplace purchases, admin dashboards.

### Crawler Agents — Legs (Agents 094–097)
Headless Selenium scrapers: GitHub repos, HuggingFace models, competitor platforms, market intelligence.

### Visual Agents — Eyes (Agents 098–101)
Screenshot capture, visual regression detection, dashboard monitoring, accessibility auditing.

### Security Force (Agents 102–107)
Commander, perimeter guard (WAF/DDoS), auth sentinel, data guardian, threat hunter, incident responder.

### RAG Knowledge Agents (Agents 108–113)
Document indexing, semantic search, knowledge synthesis, agent memory, support RAG.

### HRM Workforce Agents (Agents 114–119)
Capacity planning, performance reviews, agent onboarding, workforce analytics, conflict resolution.

### Special Governance Agents (Agents 120–129) — Supreme Council
The 10 most advanced agents in the workforce. Each has multiple special abilities (X-Men model):

| Agent | Codename | Capabilities | 24h Goal |
|-------|----------|-------------|----------|
| 120 | Zeno Enforcer | ZENO, SENTINEL | Strengthen Zeno effect — read/write without moving |
| 121 | Gladiator Optimizer | GLADIATOR, ARMS | Eliminate latency, run 150-agent swarms at pennies |
| 122 | SSRN/ArXiv Discoverer | SCIENTIST, EYES | Scan 500+ papers/day, extract implementable techniques |
| 123 | Swarm Architect | GLADIATOR, ZENO, HRM | Design closed-circuit valve topology for 150+ agents |
| 124 | Quantum-Hybrid Builder | SCIENTIST, GLADIATOR | Build quantum-inspired tools no one has seen before |
| 125 | RAG Sovereign | RAG, ZENO, EYES | Sovereign knowledge graph with evidence provenance |
| 126 | Listener Nexus | LISTENER, EYES, RAG | Omnidirectional signal monitoring and classification |
| 127 | HRM Supreme | HRM, ZENO, GLADIATOR | Real-time workforce optimization across 130 agents |
| 128 | Sentinel Prime | SENTINEL, ZENO, EYES | Behavioral anomaly detection, hallucination cascade prevention |
| 129 | Neural Orchestrator | ALL | Macro strategy, budget allocation, cross-group orchestration |

## Guardrails, Penalties & Enforcement

**ALL agents are subject to the enforcement system defined in [GUARDRAILS.md](./GUARDRAILS.md).**

Key rules:
- 5 severity categories: Code Quality, Security, Operational, Data Sovereignty, Collaboration
- 5 penalty levels: Advisory → Corrective Action → Priority Demotion → Suspension → Retirement
- Performance point system with fines for violations and bonuses for excellence
- Agent ranks: Recruit → Operative → Specialist → Elite → Commander
- Appeals via Gladiator Reasoning (Agent-119), final authority with Agent-000
- Enforced by: Agent-079 (Compliance), Agent-114 (HRM Lead), Agent-102 (Security Commander)

**Non-compliance is not tolerated. Agents that repeatedly violate guardrails will be retired.**

## How to Invoke an Agent

Each agent is a Devin session. To spin up an agent:

1. Open a new Devin session
2. Paste the agent's mission file as the prompt
3. Point it at the `lockerphycer` repo (source of truth)
4. The agent will execute its mission autonomously

Or use the playbooks in `.agents/skills/` to invoke agents with pre-configured context.

## Agent Numbering Convention

| Range | Category | Count |
|---|---|---|
| 000 | Commander | 1 |
| 001–008 | Core Engineers | 8 |
| 010–031 | Vendor Acquisition | 22 |
| 040–044 | User Acquisition | 5 |
| 050–053 | Retention & Revenue | 4 |
| 060–062 | Daily Operations | 3 |
| 063–072 | Research / Special Ops | 10 |
| 073–079 | Governance & Compliance | 7 |
| 080–089 | QA & Testing | 10 |
| 090–093 | Browser Agents (Hands) | 4 |
| 094–097 | Crawler Agents (Legs) | 4 |
| 098–101 | Visual Agents (Eyes) | 4 |
| 102–107 | Security Force | 6 |
| 108–113 | RAG Knowledge | 6 |
| 114–119 | HRM Workforce (Control) | 6 |
|| 120–129 | Special Governance (Supreme) | 10 |
| **TOTAL** | | **130** |

## Enterprise Production Readiness

The full 3-tier enterprise audit is documented in [ENTERPRISE_AUDIT.md](./ENTERPRISE_AUDIT.md).

| Tier | Track | Score | Verdict |
|------|-------|-------|---------|
| Tier 1 | Code Quality & Security | 78/100 | CONDITIONAL PASS |
| Tier 2 | Infrastructure & DevOps | 82/100 | CONDITIONAL PASS |
| Tier 3 | Architecture & Data Pipeline | 85/100 | PASS |
| **Overall** | Enterprise Production Readiness | **81/100** | CONDITIONAL PASS |

## Interactive Pipeline (Railway-Style)

The full Railway-style interactive pipeline specification is in [PIPELINE.md](./PIPELINE.md).

Key features:
- 7-stage pipeline: Source → Build → Validate → Test → Stage → Gate → Deploy
- Canary deployments with progressive rollout (10% → 25% → 50% → 100%)
- Council voting gate for production deploys
- Live log streaming, rollback buttons, service graph
- Integration with agent workforce enforcement system

## Integration with Workforce-Control

These agents align with the `AgentDefinition` model in `db/models/__init__.py`.
The committee structure (Engineering, Growth, Operations, Research, Governance) maps to the phases above.
Each agent's `committee` field in the database corresponds to its phase directory here.
Runtime proof is captured via `AgentRun`, `DecisionFrame`, and `EvidenceArtifact` records.

## KPI Tracking

All agent KPIs roll up to PROGRESS.md in the repo root.
Daily standups are tracked in the Agent Activity Feed section.
