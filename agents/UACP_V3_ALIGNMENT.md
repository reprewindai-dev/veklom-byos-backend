# UACP V3 — Operator Worker ↔ Repo Agent Alignment

> **Generated:** 2026-05-21 | **Source:** Deep research against `agents/` + `API_SURFACE.md`
> **Purpose:** Dial-in document — maps every named UACP V3 operator worker to the specific repo agents
> that power them, with their actual API calls, autonomous prompt clusters, and escalation root causes.
> Nothing assumed or guessed — every entry grounded in the repo's documented agent mission files.

---

## Governance Council Hierarchy

```
Founder Council  (constitutional)
  └── Signal Council  (advisory / Research Director)
  └── Execution Board (operational / Operations Marshal)
        └── Operator Committees (workers)
```

### Founder Council
- **Role:** Final approval, veto, and escalation authority
- **Allowed actions:** `approve_plans` | `veto_runs` | `reassign_committees`
- **Veto conditions:** regulatory breach · margin-negative execution · missing research evidence

### Signal Council
- **Role:** Advisory — convert live research + market signals into opportunities and operating pressure
- **Allowed actions:** `publish_briefs` | `recommend_targets` | `open_investigations`
- **Veto conditions:** no live sources · low-evidence thesis

### Execution Board
- **Role:** Operational — route approved work into governed runs and service delivery
- **Allowed actions:** `queue_runs` | `assign_skills` | `open_approvals`
- **Veto conditions:** unapproved skill usage · missing archive evidence

---

## Committee → Worker → Repo Agent → API Mapping

### Marketplace Operations

| Worker | Schedule | Repo Agent(s) | Key API Calls | Primary Pillar |
|--------|----------|---------------|---------------|----------------|
| Herald | 15 min | Agent-060 (Support), Agent-078 (Council Secretary) | `GET /internal/operators`, `POST /audit/logs` | operations |
| Harvest | 30 min | Agent-097 (Crawler Market Intel), Agent-070 (Scientist Marketplace) | `POST /marketplace/automation`, `POST /pipelines/{id}/run` | operations |
| Bouncer | 10 min | Agent-079 (Compliance Officer), Agent-103 (Perimeter Guard) | `POST /compliance/check`, `POST /content-safety/check`, `POST /privacy/scan` | compliance-risk |
| Gauge | 15 min | Agent-061 (Monitoring), Agent-067 (Scientist Telemetry) | `GET /platform/pulse`, `GET /metrics`, `GET /monitoring/events` | operations |
| Arbiter | 30 min | Agent-119 (Conflict Resolver) | `GET /autonomous/decisions`, `POST /autonomous/override` | governance |

---

### Governance & Evidence

| Worker | Schedule | Repo Agent(s) | Key API Calls | Primary Pillar |
|--------|----------|---------------|---------------|----------------|
| Ledger | 15 min | Agent-112 (Agent Memory), Agent-072 (Scientist Evidence) | `GET /audit/logs`, `GET /audit/verify/{id}` | governance |
| Oracle | Hourly | Agent-125 (RAG Sovereign), Agent-066 (Scientist Governance) | `GET /source-of-truth/snapshot`, `POST /source-of-truth/sync` | knowledge-research |
| Builder Arbiter | 90 min | Agent-124 (Quantum-Hybrid Builder), Agent-079 (Compliance Officer) | `GET /compliance/regulations`, `POST /compliance/check` | governance |
| Sheriff | 15 min | Agent-128 (Sentinel Prime), Agent-104 (Auth Sentinel) | `GET /security/events`, `GET /kill-switch/status` | compliance-risk |

---

### Growth & Intelligence

| Worker | Schedule | Repo Agent(s) | Key API Calls | Primary Pillar |
|--------|----------|---------------|---------------|----------------|
| Signal | 30 min | Agent-126 (Listener Nexus) | `GET /autonomous/decisions`, `POST /telemetry` | growth |
| Scout | 45 min | Agent-097 (Crawler Market Intel), Agent-095 (Crawler GitHub) | `POST /pipelines/{id}/run` (crawl pipelines) | knowledge-research |
| Spyglass | 30 min | Agent-096 (Crawler HuggingFace), Agent-097 (Crawler Market Intel) | Headless Selenium crawl → `POST /autonomous/decisions` | knowledge-research |
| Raider | Hourly | Agent-074 (Delegate Growth), Agent-121 (Gladiator Optimizer) | `POST /marketplace/automation` | growth |
| Mint | Hourly | Agent-067 (Telemetry Scientist) | `POST /ai/predict-cost`, `GET /cost/predict`, `GET /budget/rules` | finance |
| Welcome | 30 min | Agent-091 (Browser Signup), Agent-005 (Onboarding) | `POST /auth/register` (Playwright test), onboarding flow validation | sales |

---

### Builder Systems

| Worker | Schedule | Repo Agent(s) | Key API Calls | Primary Pillar |
|--------|----------|---------------|---------------|----------------|
| Builder Scout | 90 min | Agent-095 (Crawler GitHub) | GitHub crawler pipeline → opportunity queue | knowledge-research |
| Builder Forge | 120 min | Agent-121 (Gladiator Optimizer), Agent-124 (Quantum-Hybrid Builder) | `POST /pipelines`, `POST /deployments` | engineering |

---

### Experience Assurance

| Worker | Schedule | Repo Agent(s) | Key API Calls | Primary Pillar |
|--------|----------|---------------|---------------|----------------|
| Sentinel | 15 min | Agent-128 (Sentinel Prime), Agent-061 (Monitoring) | `GET /monitoring/health`, `GET /health` | product |
| Mirror | 15 min | Agent-099 (Visual Regression), Agent-085 (QA Frontend) | `GET /platform/pulse` + visual regression suite | product |
| Polish | Hourly | Agent-003 (UX Completion), Agent-085 (QA Frontend) | `POST /ai/complete` for copy review | product |
| Glide | 45 min | Agent-091 (Browser Signup), Agent-005 (Onboarding) | Playwright-driven onboarding traversal | product |
| Pulse | 15 min | Agent-067 (Telemetry), Agent-100 (Dashboard Watcher) | `GET /platform/pulse/stream` (SSE), `POST /telemetry` | operations |

---

### Vendor Network

| Worker | Schedule | Repo Agent(s) | Key API Calls | Primary Pillar |
|--------|----------|---------------|---------------|----------------|
| Vendor Scout | Hourly | Agent-094 (Crawler Lead), Agents 010–029 (20× Vendor Hunters) | Headless crawler pipeline → vendor candidate queue | growth |
| Vendor Recruiter | 90 min | Agent-030 (Vendor Outreach Lead), Agent-031 (Vendor Success) | Governed outreach + follow-up sequences | sales |
| Vendor Auditor | 120 min | Agent-079 (Compliance Officer), Agent-105 (Data Guardian) | `POST /compliance/check`, `POST /privacy/scan` | compliance-risk |

---

## Escalation Root Cause — 5 Workers Firing `regulated-objective-review`

**Affected workers:** Bouncer · Sheriff · Sentinel · Mint · Welcome

**Root cause:** Oracle has never run (`Last run: none`). Bouncer, Mint, and Sheriff depend on Oracle's evidence
packets to satisfy the `missing research evidence` veto condition. Without those packets, they cannot
validate their objectives and must escalate to the Founder Council.

**Fix sequence:**
```
1. POST /internal/uacp/command   →  { "command": "force_run", "worker": "Oracle" }
2. POST /source-of-truth/sync    →  force archive sync
3. GET  /source-of-truth/snapshot →  confirm evidence packets populated
4. Allow Bouncer, Sheriff, Mint to run next cycle — they will pass evidence check
```

---

## Autonomous Schedule — 3 Prompt Clusters

These three clusters run without founder intervention. Each is evidence-gated to prevent unapproved execution.

---

### Cluster 1 — Governance Heartbeat
**Cadence:** Every 15 minutes  
**Workers:** Herald · Ledger · Pulse

```
Prompt:
"Herald: Check /internal/operators and log any new triggers to /audit/logs.
Ledger: Run /audit/verify/{id} on the last 10 archive entries — if any hash fails,
raise escalation to Founder Council and halt the cycle.
Pulse: Pull /platform/pulse/stream and confirm all telemetry cards are fresh.
Do not advance to next cycle without a clean Ledger hash confirmation."
```

**Why this earns passive income:** Catches compliance drift and archive corruption before they compound
into regulatory vetoes that block revenue-generating runs.

---

### Cluster 2 — Intelligence Sweep
**Cadence:** Every 30–45 minutes  
**Workers:** Signal · Scout · Spyglass · Raider

```
Prompt:
"Signal: Pull live market data via Listener Nexus. Require minimum 2 live sources before proceeding.
Scout + Spyglass: Run crawler agents 095–097 against GitHub and competitor surfaces.
Output top 3 competitor weaknesses to /autonomous/decisions log.
Raider: Take the top 3 weaknesses from Spyglass output and generate counter-positioning packets.
Gate: Signal must confirm live source count ≥ 2 before Raider fires. If gate fails, pause cycle
and notify Signal Council."
```

**Why this earns passive income:** Continuously surfaces competitor attack surfaces and converts them into
actionable campaign packets without manual research.

---

### Cluster 3 — Quality + Vendor Pipeline
**Cadence:** Hourly  
**Workers:** Mirror · Sentinel · Vendor Scout · Vendor Recruiter · Vendor Auditor · Builder Scout

```
Prompt:
"Mirror + Sentinel: Run visual regression and uptime checks. If both pass:
Vendor Scout: Submit top 3 vendor candidates from crawler queue to Vendor Recruiter.
Vendor Auditor: Run /compliance/check and /privacy/scan on each candidate before
Vendor Recruiter sends outreach. Do not send outreach without clean Auditor sign-off.
Builder Scout: File any new GitHub-sourced builder opportunities to Builder Forge queue.
If Mirror or Sentinel fail, halt vendor and builder actions and escalate to Execution Board."
```

**Why this earns passive income:** Runs the vendor acquisition pipeline and builder opportunity discovery
autonomously — the two highest-leverage passive revenue levers in the Veklom marketplace model.

---

## Notes

- All API calls require `Authorization: Bearer <token>` unless marked Public in `API_SURFACE.md`
- UACP command endpoint: `POST /internal/uacp/command` (Admin auth required)
- Operator registry: `GET /internal/operators` (Admin auth required)
- Oracle must run before Bouncer, Sheriff, and Mint can clear their evidence gate
- Vendor Scout maps to 20 dedicated vendor hunter agents (phase2-vendor-acquisition, agents 010–029)
