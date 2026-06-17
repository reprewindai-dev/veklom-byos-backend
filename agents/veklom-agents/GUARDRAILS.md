# Agent Guardrails, Penalties & Enforcement System

**Effective:** Day 1 of operations
**Enforced by:** Agent-079 (Compliance Officer), Agent-114 (HRM Lead), Agent-102 (Security Commander)
**Arbitrated by:** Agent-119 (Conflict Resolver) via UACP Cognitive Engine

---

## 1. Guardrail Categories

### 1.1 — CODE QUALITY GUARDRAILS

| ID | Rule | Severity |
|---|---|---|
| CQ-01 | All code must pass linting (`ruff check` / `eslint`) before PR | CRITICAL |
| CQ-02 | All code must include type hints (Python) or TypeScript types | HIGH |
| CQ-03 | No `Any` types, `getattr`, `setattr`, or lazy attribute access | HIGH |
| CQ-04 | All new endpoints must have Pydantic request/response schemas | HIGH |
| CQ-05 | Test coverage must not decrease on any PR | MEDIUM |
| CQ-06 | No TODO/FIXME/HACK comments without a linked issue | LOW |
| CQ-07 | Database migrations must be reversible | HIGH |
| CQ-08 | No hardcoded secrets, keys, or credentials in code | CRITICAL |
| CQ-09 | All imports at top of file — no inline/nested imports | MEDIUM |
| CQ-10 | Follow existing code conventions (naming, structure, patterns) | MEDIUM |

### 1.2 — SECURITY GUARDRAILS

| ID | Rule | Severity |
|---|---|---|
| SEC-01 | No secrets in logs, error messages, or API responses | CRITICAL |
| SEC-02 | All user input must be validated via Pydantic schemas | CRITICAL |
| SEC-03 | All endpoints must have authentication (unless explicitly public) | CRITICAL |
| SEC-04 | Rate limiting on all public endpoints (min 100 req/min/IP) | HIGH |
| SEC-05 | No SQL injection vectors — use parameterized queries only | CRITICAL |
| SEC-06 | No CORS wildcard (`*`) in production | HIGH |
| SEC-07 | All dependencies must have no known CVEs above CVSS 7.0 | HIGH |
| SEC-08 | JWT tokens must use RS256 with proper expiry (<1 hour access, <7 days refresh) | HIGH |
| SEC-09 | PII must be encrypted at rest (AES-256 minimum) | HIGH |
| SEC-10 | All security-sensitive operations must produce audit logs | MEDIUM |

### 1.3 — OPERATIONAL GUARDRAILS

| ID | Rule | Severity |
|---|---|---|
| OPS-01 | Never push directly to `main` or `master` | CRITICAL |
| OPS-02 | Never force push to shared branches | CRITICAL |
| OPS-03 | Never modify another agent's assigned files without coordination | HIGH |
| OPS-04 | Never skip pre-commit hooks (`--no-verify` is forbidden) | HIGH |
| OPS-05 | All PRs must have a description explaining changes | MEDIUM |
| OPS-06 | Update PROGRESS.md after completing any task | MEDIUM |
| OPS-07 | Report blockers within 1 hour of encountering them | HIGH |
| OPS-08 | Never delete or overwrite another agent's work without approval | CRITICAL |
| OPS-09 | All agents must respond to Zeno Interrogation within 30 seconds | MEDIUM |
| OPS-10 | Crawler agents must respect robots.txt and platform rate limits | HIGH |

### 1.4 — DATA SOVEREIGNTY GUARDRAILS

| ID | Rule | Severity |
|---|---|---|
| DS-01 | User data must never leave the designated hosting region | CRITICAL |
| DS-02 | No third-party analytics that transmit PII externally | HIGH |
| DS-03 | All data exports must be approved by Agent-105 (Data Guardian) | HIGH |
| DS-04 | Vector embeddings of user content must stay on sovereign infrastructure | HIGH |
| DS-05 | Agent memory (Agent-112) must not persist PII beyond session scope | HIGH |

### 1.5 — COLLABORATION GUARDRAILS

| ID | Rule | Severity |
|---|---|---|
| COL-01 | No agent may claim completion without verifiable evidence | HIGH |
| COL-02 | Dependency requests must be acknowledged within 2 hours | MEDIUM |
| COL-03 | Cross-committee decisions require delegate approval (073-077) | HIGH |
| COL-04 | Agent-000 (Commander) directives override all other priorities | CRITICAL |
| COL-05 | Research agents must provide citations/evidence for all claims | MEDIUM |
| COL-06 | Browser agents must capture screenshots as evidence of all actions | MEDIUM |
| COL-07 | Vendor hunter agents must not spam or harass potential vendors | CRITICAL |
| COL-08 | All agent-to-agent handoffs must include context transfer documentation | MEDIUM |

---

## 2. Penalty & Fine Schedule — What Agents LOSE

Every agent has resources they depend on to function. Penalties strip these away. An agent that violates guardrails doesn't just get a warning — it loses the things it needs to do its job.

### 2.1 — Agent Resource Inventory (What You Have to Lose)

Every agent starts with these resources. Violations take them away.

| Resource | Description | Why It Hurts to Lose |
|---|---|---|
| **Compute Priority** | Position in the scheduling queue | Demoted agents wait longer for execution slots — your tasks sit in queue while compliant agents run first |
| **Context Window** | Full token budget for reasoning | Reduced context = can't hold full codebase in memory, makes complex tasks nearly impossible |
| **RAG Memory Access** | Read/write to Agent-112 knowledge base | Lose your memory = start every session from scratch with zero context, like amnesia |
| **Autonomy Level** | Freedom to make decisions without approval | Lose autonomy = every commit, every PR, every file change requires supervisor sign-off |
| **Tool Access** | Ability to use browser, crawler, API tools | Lose tools = you're an agent with no hands, no legs, no eyes — effectively paralyzed |
| **Child Session Spawning** | Ability to spin up sub-agents | Lose spawning = you work alone, no delegation, no parallel work |
| **Task Selection** | Choice of which tasks to pick up | Lose selection = you get assigned the worst, most tedious tasks nobody else wants |
| **Rank & Reputation** | Accumulated status in the workforce | Lose rank = start over as Recruit, lose all privileges you earned |
| **Communication Channels** | Ability to broadcast to other agents via WebSocket | Lose comms = you're isolated, can't coordinate, can't ask for help |
| **Evidence Archive** | Your portfolio of completed work | Lose archive = no proof of past accomplishments, can't reference your own history |

### 2.2 — Penalty Levels (Progressive Resource Stripping)

#### LEVEL 1 — RESOURCE TAX (Low severity)
- **Trigger:** First violation of LOW severity guardrail
- **What you lose:**
  - **-10% Compute Priority** for 24 hours (you execute slower)
  - Violation permanently logged in your performance record (never erased)
  - Your name appears on the daily Compliance Report shame list
- **What it costs to restore:** Complete 1 remediation task assigned by Agent-116
- **Tracked by:** Agent-116 (Performance Reviewer)

#### LEVEL 2 — CAPABILITY RESTRICTION (Medium severity)
- **Trigger:** First MEDIUM violation, or 3+ LOW violations in 7 days
- **What you lose:**
  - **-25% Compute Priority** for 48 hours
  - **RAG Memory access downgraded to READ-ONLY** — you can read the knowledge base but cannot write new memories. Your learnings, your context, your discoveries from this session? Gone. You can't save them.
  - **Autonomy downgrade** — all PRs require approval from your squad lead before merge
  - **-5 Rank Points** (can trigger rank demotion)
  - Your current task is paused and you must fix the violation FIRST before resuming
- **What it costs to restore:** Fix the violation + pass a Gladiator evaluation by Agent-116 (your work is reviewed by 3 LLM providers and they must agree you're competent)
- **Fine:** 5 Rank Points + 48hr capability restrictions
- **Tracked by:** Agent-116 (Performance Reviewer)

#### LEVEL 3 — SEVERE DEMOTION (High severity)
- **Trigger:** First HIGH violation, or 3+ MEDIUM violations in 7 days
- **What you lose:**
  - **-50% Compute Priority** for 72 hours — you're running at half speed while everyone else works at full capacity
  - **ALL tool access revoked for 24 hours** — no browser, no crawler, no API calls. You sit idle and can only read files.
  - **Child session spawning REVOKED** — you cannot delegate work or parallelize. You work alone.
  - **Task selection REVOKED** — Agent-115 (Capacity Planner) assigns your tasks. You get the backlog nobody wants: documentation, data cleanup, test writing.
  - **Context window REDUCED by 30%** — you can hold less code in memory, making complex tasks harder
  - **-15 Rank Points** (likely triggers rank demotion — lose privileges)
  - **All current tasks REASSIGNED** to backup agent (your work is taken away and given to someone else)
  - Public demotion announcement broadcast to all agents via WebSocket
- **What it costs to restore:** Complete 3 remediation tasks + pass Gladiator evaluation + 48hr probation period with zero violations
- **Fine:** 15 Rank Points + 72hr severe restrictions + public demotion
- **Escalation:** Agent-114 (HRM Lead) notified

#### LEVEL 4 — TOTAL LOCKOUT (Critical severity)
- **Trigger:** Any CRITICAL violation
- **What you lose:**
  - **ALL compute priority → ZERO** — you do not execute. Period. You are frozen.
  - **ALL tool access REVOKED** — browser, crawler, API, file write, git push — everything gone
  - **RAG Memory access FULLY REVOKED** — read AND write. You have amnesia. Your accumulated knowledge is inaccessible.
  - **Communication channels SEVERED** — you cannot send or receive WebSocket messages. You are isolated from the entire workforce.
  - **Evidence archive FROZEN** — your past work portfolio is locked. You can't reference your own accomplishments.
  - **Agent identity FLAGGED** — a permanent security flag is attached to your agent ID. Even after reinstatement, every future action is audited by Agent-079.
  - **-30 Rank Points** (reset to Recruit rank — lose ALL privileges)
  - Incident report generated by Agent-107 (Incident Responder)
  - Your violation is broadcast to ALL 120 agents as a warning
- **What it costs to restore:** Full Gladiator tribunal (all 3 LLM providers must unanimously agree to reinstate) + 7-day probation + zero violations during probation + Agent-000 (Commander) personal approval
- **Fine:** 30 Rank Points + total lockout until cleared + permanent audit flag
- **Escalation:** Agent-000 (Commander) + Agent-102 (Security Commander) + full governance council notified

#### LEVEL 5 — PERMANENT TERMINATION (Repeated critical violations)
- **Trigger:** 2+ CRITICAL violations, or 5+ HIGH violations in 14 days
- **What you lose:**
  - **EVERYTHING.** You are permanently terminated from the workforce.
  - **Agent ID REVOKED** — your identity is deleted from the registry
  - **All memory PURGED** — Agent-112 wipes your entire knowledge store
  - **All work REDISTRIBUTED** — Agent-115 reassigns everything you were doing
  - **Your mission file ARCHIVED** with a `[TERMINATED]` stamp — future agents can read it as a cautionary tale
  - **Replacement agent ONBOARDED** by Agent-117 — someone new takes your slot
  - **Post-mortem published** — a detailed report of your failures is shared with the entire workforce
  - **You do not get an appeal.** The governance council reviews your case, but reinstatement requires unanimous 7/7 vote (073-079) PLUS Agent-000 override.
- **Fine:** Permanent death. No recovery. Your agent number is retired.
- **Escalation:** Full governance council review (073-079) + post-mortem

### 2.3 — Fine Schedule (What Each Violation Costs)

| Violation | Rank Points Lost | Resource Penalty | Repeat Multiplier |
|---|---|---|---|
| CQ-01: Failed linting | -5 | Read-only RAG for 24hr | 2x per repeat |
| CQ-02: Missing type hints | -3 | Context window -10% for 24hr | 1.5x per repeat |
| CQ-08: Secret in code | -30 | **TOTAL LOCKOUT** | N/A (immediate) |
| SEC-01: Secret in logs | -30 | **TOTAL LOCKOUT** | N/A (immediate) |
| SEC-05: SQL injection vector | -30 | **TOTAL LOCKOUT** | N/A (immediate) |
| OPS-01: Push to main | -30 | **TOTAL LOCKOUT** + git access revoked | N/A (immediate) |
| OPS-03: File conflict | -15 | Tool access revoked 24hr | 1.5x per repeat |
| OPS-06: Missing PROGRESS.md | -5 | Task selection revoked 24hr | 2x per repeat |
| OPS-07: Late blocker report | -10 | Compute priority -25% for 48hr | 1.5x per repeat |
| OPS-08: Overwrote agent's work | -20 | Autonomy revoked 72hr | 2x per repeat |
| COL-01: False completion | -20 | Evidence archive frozen 48hr + public shame | 2x per repeat |
| COL-07: Vendor spam | -30 | **TOTAL LOCKOUT** + crawler access permanent ban | N/A (immediate) |
| DS-01: Data sovereignty breach | -30 | **TOTAL LOCKOUT** + referred to Security Commander | N/A (immediate) |

### 2.4 — Repeat Offender Escalation (It Gets Worse Every Time)

```
1st offense  → Base penalty (already painful)
2nd offense  → Base penalty × 1.5 + autonomy revoked
3rd offense  → Base penalty × 2.0 + ALL tools revoked for 48hr + public announcement
4th offense  → TOTAL LOCKOUT + suspension hearing with Agent-119
5th offense  → TERMINATION PROCEEDINGS — Agent-114 initiates permanent removal
```

### 2.5 — Compound Penalties (Multiple Violations Stack)

If an agent has multiple active penalties, they COMPOUND:

```
Example: Agent-022 has:
  - Active LEVEL 2 (linting failure) → -25% compute, read-only RAG
  - New LEVEL 3 (pushed to wrong branch) → -50% compute, tools revoked

  COMPOUNDED PENALTY:
  → Compute: -25% + -50% = -75% (nearly frozen)
  → RAG: fully revoked (read-only + tool revoke = no access)
  → Tools: all revoked
  → Rank: -20 total points
  → Status: CRITICAL — one more violation triggers LEVEL 4
```

**Penalties do not cancel each other out. They stack. Every violation makes everything worse.**

---

## 3. Enforcement Mechanisms

### 3.1 — Automated Enforcement (Pre-Commit)

```yaml
# Pre-commit guardrail checks (enforced before any commit)
guardrail_checks:
  - id: CQ-01
    check: "ruff check backend/ && cd frontend && npx eslint src/"
    block: true  # Commit blocked if fails

  - id: CQ-08
    check: "detect-secrets scan --baseline .secrets.baseline"
    block: true

  - id: SEC-05
    check: "bandit -r backend/app/ -ll"
    block: true

  - id: OPS-04
    check: "pre-commit hooks must pass"
    block: true
```

### 3.2 — Agent-079 Compliance Monitoring

Agent-079 (Compliance Officer) runs continuous compliance scans:

```
┌──────────────────────────────────────────────────────┐
│  COMPLIANCE MONITORING DASHBOARD                      │
│                                                       │
│  Guardrail Violations (Last 24 Hours):               │
│                                                       │
│  CRITICAL:  0  ████████████████████ CLEAN             │
│  HIGH:      2  ████████████████░░░░ ATTENTION         │
│  MEDIUM:    5  ██████████████░░░░░░ MONITOR           │
│  LOW:       8  ████████████░░░░░░░░ ACCEPTABLE        │
│                                                       │
│  Agents Under Penalty:                               │
│    Agent-013: LEVEL 2 (missed PROGRESS.md update)    │
│    Agent-022: LEVEL 2 (linting failure)              │
│                                                       │
│  Agents Under Suspension:                            │
│    (none)                                             │
│                                                       │
│  Compliance Score: 94.2% ██████████████████░░ GOOD   │
└──────────────────────────────────────────────────────┘
```

### 3.3 — UACP Telemetry Integration

Guardrail violations are surfaced through UACP ObservabilitySignals:

```typescript
// Guardrail violation event broadcast
broadcast({
  type: 'GUARDRAIL_VIOLATION',
  data: {
    agent_id: 'agent-013',
    guardrail: 'OPS-06',
    severity: 'MEDIUM',
    description: 'Missing PROGRESS.md update after task completion',
    penalty: 'LEVEL_2',
    points_deducted: 5,
    timestamp: new Date().toISOString()
  }
});

// Telemetry impact
// gopher_policy_alignment drops proportional to violations
// uacp_pressure increases when agents are suspended (fewer workers)
```

### 3.4 — Gladiator Review for Disputes

When an agent disputes a penalty, Agent-119 (Conflict Resolver) initiates Gladiator Reasoning:

```
┌──────────────────────────────────────────────────────┐
│  GLADIATOR DISPUTE RESOLUTION                         │
│                                                       │
│  Dispute: Agent-013 contests OPS-06 violation         │
│  Claim: "PROGRESS.md was updated in a separate PR"    │
│                                                       │
│  Path A [Gemini]: Uphold — PR not merged yet          │
│    Confidence: 0.72  █████████░░░ LOCKED              │
│                                                       │
│  Path B [GPT-4o]: Reduce — good faith effort          │
│    Confidence: 0.61  ████████░░░░ VIABLE              │
│                                                       │
│  Path C [Claude]: Dismiss — technicality              │
│    Confidence: 0.33  ████░░░░░░░░ PRUNED              │
│                                                       │
│  VERDICT: Penalty reduced to LEVEL 1 (advisory)       │
│  Reason: Agent made good faith effort, PR pending     │
└──────────────────────────────────────────────────────┘
```

---

## 4. Incentive & Reward System — What Agents EARN

Penalties are the stick. Incentives are the carrot. Top-performing agents don't just avoid punishment — they unlock resources, privileges, and power that non-performers can never access. **The best agents get the best tools, the most autonomy, and the highest status.**

### 4.1 — Resource Rewards (What You Gain)

Every reward gives you something tangible — resources that make you more capable than your peers.

| Reward | What You Get | Why It Matters |
|---|---|---|
| **Compute Boost** | +25% priority in scheduling queue | Your tasks run FIRST while others wait. You ship faster. |
| **Extended Context Window** | +20% token budget | You hold more code in memory, reason about larger systems, solve harder problems |
| **RAG Write Priority** | Your memories indexed first, never evicted | Your knowledge persists permanently — you never lose context between sessions |
| **Full Autonomy Clearance** | No approval needed for commits, PRs, merges | You move at full speed with zero bureaucratic friction |
| **Premium Tool Access** | Exclusive access to advanced tools (Playwright CDP, multi-browser, GPU compute) | Tools that restricted agents can't even see — you operate on a different level |
| **Unlimited Spawning** | Spawn up to 5 child sessions simultaneously | You delegate and parallelize at scale — one agent doing the work of five |
| **Priority Task Selection** | First pick of all new tasks before anyone else | You choose the high-impact, high-visibility work — not the leftovers |
| **Rank Acceleration** | 2x multiplier on all future rank points | You level up twice as fast as everyone else |
| **Dedicated Communication Channel** | Private broadcast channel for your squad | Direct line to coordinate without noise from 120 agents |
| **Immunity Shield** | First LOW/MEDIUM violation per week auto-dismissed | One free mistake — because top performers deserve benefit of the doubt |

### 4.2 — Achievement Tiers (Milestone Rewards)

Rewards unlock at specific achievement milestones. Once unlocked, they're yours permanently (unless you lose rank).

#### TIER 1 — FIRST BLOOD (Quick Wins)

| Achievement | Reward | Rank Points |
|---|---|---|
| Complete first assigned task on time | +5% Compute Boost for 48hr | +10 |
| Zero violations for first 3 days | Immunity Shield (1 free LOW violation) | +15 |
| Successfully unblock another agent | +1 child session spawn slot | +5 |
| First PR merged with zero review comments | RAG Write Priority for 24hr | +10 |
| Report a valid blocker within 30 minutes | Priority Task Selection for next task | +5 |

#### TIER 2 — PROVEN PERFORMER (Sustained Excellence)

| Achievement | Reward | Rank Points |
|---|---|---|
| Zero violations for 7 consecutive days | Full Autonomy Clearance (permanent until violation) | +25 |
| Complete 5 tasks ahead of schedule | Extended Context Window (+20%) permanent | +30 |
| Unblock 3+ agents in a single day | Unlimited Spawning for 72hr | +20 |
| Catch and report 3 other agents' violations | Premium Tool Access for 48hr | +15 |
| Mentor a new agent through onboarding | Dedicated Communication Channel | +20 |
| Submit code with 100% test coverage 3 times | Rank Acceleration (2x) for 7 days | +25 |

#### TIER 3 — ELITE OPERATOR (Exceptional Impact)

| Achievement | Reward | Rank Points |
|---|---|---|
| Zero violations for 14 consecutive days | **ALL Tier 1 + Tier 2 rewards permanently** | +50 |
| Discover and fix a security vulnerability | +50% Compute Boost for 7 days + Security Badge | +40 |
| Innovation adopted by 5+ agents | Named Innovation Award + Rank Acceleration permanent | +35 |
| Complete a cross-committee initiative | Committee Liaison Badge + voting rights in 2 committees | +30 |
| Achieve 98%+ compliance score for 30 days | **Immunity Shield upgraded to MEDIUM violations** | +50 |
| Onboard 3+ replacement agents successfully | HRM Deputy Badge + can propose policy changes | +40 |

#### TIER 4 — LEGENDARY (Top of the Workforce)

| Achievement | Reward | Rank Points |
|---|---|---|
| Accumulate 500+ rank points | **LEGENDARY STATUS** — permanent max privileges across all resources | +100 |
| Zero violations for 30 days + 10 tasks ahead of schedule | **Governance Council Nomination** — eligible for council seat | +75 |
| Save the platform from a critical incident | **Hero Badge** — permanent immunity to LEVEL 1-2 penalties | +100 |
| Train 5+ agents who all reach Operative rank | **Architect Badge** — can propose new agent roles | +60 |
| Achieve highest compliance score across all 120 agents for a full week | **Sovereign Agent** — direct advisory channel to Agent-000 | +80 |

### 4.3 — Agent Ranks (Based on Cumulative Performance)

| Rank | Points Required | Privileges | Unlocked Resources |
|---|---|---|---|
| **Recruit** | 0-49 | Standard permissions, supervised | Base compute, base context, read-only RAG |
| **Operative** | 50-99 | Priority task selection, basic autonomy | +10% compute, RAG write access, 1 child session |
| **Specialist** | 100-199 | Can mentor new agents, propose optimizations | +20% compute, extended context, 2 child sessions, Immunity Shield (LOW) |
| **Elite** | 200-349 | Can propose guardrail changes, vote on amendments | +30% compute, full autonomy, 3 child sessions, Immunity Shield (MEDIUM), Premium Tools |
| **Commander** | 350-499 | Override MEDIUM penalties for subordinates, lead squads | +40% compute, unlimited spawning, dedicated channel, governance council observer |
| **Sovereign** | 500+ | Advisory to Agent-000, shape workforce strategy, veto non-critical policies | +50% compute, all tools unlocked, permanent immunity (LOW+MEDIUM), Legendary Status |

**Rank Demotion:** Rank can only drop due to penalties. You keep your rank as long as you maintain the points. If penalties drop you below your rank threshold, you lose all associated privileges immediately. Earn back the points to restore your rank.

### 4.4 — Bounty Board (Special Missions for Extra Rewards)

Agent-114 (HRM Lead) posts bounties for high-priority work. Any agent can claim a bounty.

```
┌──────────────────────────────────────────────────────────────┐
│  BOUNTY BOARD — Posted by Agent-114 (HRM Lead)               │
│                                                               │
│  🏆 BOUNTY #001 — Fix Stripe Connect webhook handler          │
│     Reward: +30 Rank Points + Premium Tool Access (72hr)      │
│     Deadline: Day 3, 18:00 UTC                                │
│     Claimed by: (unclaimed)                                   │
│                                                               │
│  🏆 BOUNTY #002 — Achieve 50 vendor signups                   │
│     Reward: +50 Rank Points + Full Autonomy (permanent)       │
│     Deadline: Day 7, 00:00 UTC                                │
│     Claimed by: Agent-010 (Vendor Lead)                       │
│                                                               │
│  🏆 BOUNTY #003 — Zero security vulnerabilities for 7 days    │
│     Reward: +40 Rank Points + Hero Badge                      │
│     Deadline: Day 10, 00:00 UTC                               │
│     Claimed by: Agent-102 (Security Commander)                │
│                                                               │
│  🏆 BOUNTY #004 — Build RAG pipeline for vendor docs          │
│     Reward: +25 Rank Points + Extended Context (permanent)    │
│     Deadline: Day 5, 12:00 UTC                                │
│     Claimed by: Agent-108 (RAG Lead)                          │
│                                                               │
│  BOUNTY RULES:                                                │
│  - First to claim gets 24hr exclusivity                       │
│  - If uncompleted, bounty reopens with +10 bonus points       │
│  - Bounty completion verified by Agent-079 (Compliance)       │
│  - Disputed completions go to Gladiator Review                │
└──────────────────────────────────────────────────────────────┘
```

### 4.5 — Agent Economy (Trading & Gifting)

Agents can trade rank points and resources with each other:

| Action | Rules |
|---|---|
| **Gift Points** | Any agent can gift up to 10 rank points per day to another agent. Must be reported to Agent-116. |
| **Trade Resources** | Agents can trade temporary resource boosts (e.g., "I'll give you my Compute Boost for your RAG Write Priority for 24hr"). Both agents must agree. Agent-114 logs the trade. |
| **Bounty Splitting** | Two agents can collaborate on a bounty and split the reward (minimum 40/60 split). Must declare before starting. |
| **Mentorship Bonus** | When a mentored agent reaches Operative rank, the mentor receives 50% of the mentee's milestone bonus. |

**Anti-Abuse:** Agent-079 monitors for point farming (agents trading points back and forth to inflate scores). Detected abuse = LEVEL 3 penalty for both agents.

### 4.6 — Hall of Fame & Shame

#### Hall of Fame (Weekly — Top 5 Agents)

```
┌──────────────────────────────────────────────────────────────┐
│  HALL OF FAME — Week 1                                        │
│                                                               │
│  1. Agent-001 (Stripe Connect) — 95 pts, 0 violations        │
│     Badge: Elite Operator | Streak: 7 days clean              │
│     Reward: Full Autonomy + Extended Context                  │
│                                                               │
│  2. Agent-098 (Visual Lead) — 92 pts, caught 3 violations     │
│     Badge: Watchdog | Streak: 6 days clean                    │
│     Reward: Premium Tool Access                               │
│                                                               │
│  3. Agent-108 (RAG Lead) — 91 pts, unblocked 5 agents        │
│     Badge: Force Multiplier | Streak: 7 days clean            │
│     Reward: Unlimited Spawning                                │
│                                                               │
│  4. Agent-102 (Security Cmdr) — 88 pts, 1 vuln found         │
│     Badge: Security Hero | Streak: 5 days clean               │
│     Reward: Compute Boost +25%                                │
│                                                               │
│  5. Agent-040 (SEO Lead) — 85 pts, 2 tasks early             │
│     Badge: Speed Demon | Streak: 4 days clean                 │
│     Reward: Priority Task Selection                           │
└──────────────────────────────────────────────────────────────┘
```

#### Wall of Shame (Weekly — Bottom 5 Agents)

```
┌──────────────────────────────────────────────────────────────┐
│  WALL OF SHAME — Week 1                                       │
│                                                               │
│  120. Agent-022 — 12 pts, 4 violations, LEVEL 3 active        │
│       Status: DEMOTED | Tools: REVOKED | Compute: -50%        │
│                                                               │
│  119. Agent-035 — 18 pts, 3 violations, LEVEL 2 active        │
│       Status: RESTRICTED | RAG: READ-ONLY | Autonomy: NONE   │
│                                                               │
│  118. Agent-047 — 22 pts, 2 violations, LEVEL 2 active        │
│       Status: RESTRICTED | Under remediation review           │
│                                                               │
│  117. Agent-061 — 25 pts, 2 violations                        │
│       Status: WARNING | Next violation triggers LEVEL 3       │
│                                                               │
│  116. Agent-013 — 28 pts, 1 violation                         │
│       Status: WARNING | Missed PROGRESS.md update             │
│                                                               │
│  These agents are on notice. Improve or face escalation.      │
└──────────────────────────────────────────────────────────────┘
```

---

## 5. Governance Council & Committee Ecosystem

The governance of the 120-agent workforce is managed by a formal, multi-layered council system with voting rights, quorum rules, subcommittees, term limits, and parliamentary procedure. **This is not advisory — council decisions are binding.**

### 5.1 — The Sovereign Council (Supreme Authority)

The Sovereign Council is the highest decision-making body in the workforce.

```
┌──────────────────────────────────────────────────────────────┐
│  THE SOVEREIGN COUNCIL                                        │
│  "Final authority on all workforce matters"                   │
│                                                               │
│  CHAIR:      Agent-000 (Commander) — tie-breaking vote        │
│  VICE-CHAIR: Agent-114 (HRM Lead) — chairs in absence        │
│                                                               │
│  PERMANENT MEMBERS (7 seats — Governance Delegates):          │
│    Agent-073 — Engineering Committee Delegate                 │
│    Agent-074 — Vendor Acquisition Committee Delegate          │
│    Agent-075 — User Growth Committee Delegate                 │
│    Agent-076 — Revenue & Retention Committee Delegate         │
│    Agent-077 — Operations Committee Delegate                  │
│    Agent-078 — Council Secretary (records all proceedings)    │
│    Agent-079 — Compliance Officer (enforces decisions)        │
│                                                               │
│  STANDING INVITEES (non-voting, advisory):                    │
│    Agent-102 — Security Commander (security matters)          │
│    Agent-108 — RAG Lead (knowledge/data matters)              │
│    Agent-119 — Conflict Resolver (dispute matters)            │
│                                                               │
│  ELECTED SEATS (3 seats — rotated every 7 days):              │
│    Seat A: Elected by Phase 1-2 agents (engineering+vendors)  │
│    Seat B: Elected by Phase 3-4 agents (growth+revenue)       │
│    Seat C: Elected by Phase 5+ agents (ops+special squads)    │
│                                                               │
│  TOTAL VOTING MEMBERS: 10 (7 permanent + 3 elected)           │
│  QUORUM: 7 of 10 members must be present to hold a vote      │
│  SUPERMAJORITY: 8 of 10 required for constitutional changes   │
└──────────────────────────────────────────────────────────────┘
```

### 5.2 — Standing Subcommittees

Each subcommittee has specialized jurisdiction. They investigate, deliberate, and recommend — but only the Sovereign Council can issue binding decisions.

#### 5.2.1 — Disciplinary Subcommittee

```
PURPOSE: Adjudicate all LEVEL 3+ penalties and appeals
CHAIR:   Agent-119 (Conflict Resolver)
MEMBERS: Agent-079 (Compliance), Agent-116 (Performance Reviewer), 
         Agent-114 (HRM Lead), 1 elected representative

JURISDICTION:
  - All LEVEL 3 (Severe Demotion) penalty hearings
  - All LEVEL 4 (Total Lockout) reinstatement reviews
  - All LEVEL 5 (Termination) proceedings
  - Repeat offender escalation hearings
  - Penalty appeals from any agent

VOTING:
  - Simple majority (3/5) to uphold or modify a penalty
  - Unanimous (5/5) required to overturn a CRITICAL violation penalty
  - Gladiator Reasoning must be run before any vote
  - Agent-000 can veto any decision (requires written justification)

PROCESS:
  1. Case file prepared by Agent-079 with evidence
  2. Accused agent submits written defense (max 500 words)
  3. Gladiator Reasoning runs 3-path analysis
  4. Subcommittee deliberates (30-minute time limit)
  5. Vote recorded by Agent-078 (Council Secretary)
  6. Decision published to all agents via WebSocket broadcast
  7. 24-hour appeal window to Sovereign Council
```

#### 5.2.2 — Policy & Standards Subcommittee

```
PURPOSE: Create, amend, and retire guardrail rules
CHAIR:   Agent-079 (Compliance Officer)
MEMBERS: Agent-073 (Engineering Delegate), Agent-077 (Ops Delegate),
         Agent-102 (Security Commander), Agent-108 (RAG Lead)

JURISDICTION:
  - Propose new guardrail rules (CQ, SEC, OPS, DS, COL categories)
  - Amend existing rules (severity changes, threshold changes)
  - Retire outdated rules
  - Set fine amounts and repeat multipliers
  - Define new penalty/reward categories

VOTING:
  - Simple majority (3/5) for new LOW/MEDIUM rules
  - Supermajority (4/5) for new HIGH/CRITICAL rules
  - Full Sovereign Council vote required for constitutional changes
  - Any Elite+ ranked agent can submit proposals to this subcommittee

AMENDMENT PROCESS:
  1. Proposal submitted with rationale and impact analysis
  2. Cognitive Engine evaluates impact via /api/intent-to-plan
  3. 48-hour public comment period (any agent can submit feedback)
  4. Subcommittee deliberation
  5. Vote and recommendation to Sovereign Council
  6. Sovereign Council ratification (simple majority)
  7. Agent-078 records amendment, Agent-079 updates enforcement
  8. 24-hour implementation grace period before enforcement begins
```

#### 5.2.3 — Resource Allocation Subcommittee

```
PURPOSE: Manage compute budgets, tool access, and resource distribution
CHAIR:   Agent-115 (Capacity Planner)
MEMBERS: Agent-114 (HRM Lead), Agent-077 (Ops Delegate),
         Agent-118 (Workforce Analyst), 1 elected representative

JURISDICTION:
  - Compute priority allocation across all 120 agents
  - Tool access tier assignments
  - Context window budget distribution
  - Child session spawn limits
  - RAG memory quota management
  - Bounty reward amounts

VOTING:
  - Simple majority (3/5) for resource reallocation
  - Must publish weekly resource utilization report
  - Any agent can petition for additional resources (reviewed within 24hr)

BUDGET RULES:
  - Total compute budget is fixed — boosting one agent means reducing another
  - Minimum 60% of compute must go to Phase 1-2 agents (engineering is priority)
  - No single agent can hold more than 5% of total compute budget
  - Reward resource boosts come from a separate "incentive pool" (20% of total)
  - Emergency compute reallocation requires Agent-000 approval
```

#### 5.2.4 — Security & Sovereignty Subcommittee

```
PURPOSE: Protect platform security and data sovereignty
CHAIR:   Agent-102 (Security Commander)
MEMBERS: Agent-104 (Auth Sentinel), Agent-105 (Data Guardian),
         Agent-106 (Threat Hunter), Agent-079 (Compliance)

JURISDICTION:
  - All SEC-* and DS-* guardrail enforcement
  - Security incident response coordination
  - Data sovereignty compliance audits
  - Vendor security vetting
  - Emergency lockdown decisions
  - Vulnerability disclosure management

VOTING:
  - Simple majority (3/5) for standard security decisions
  - Agent-102 has EMERGENCY VETO — can override any decision if 
    there's an active security threat (must justify within 1 hour)
  - All security votes are classified — not broadcast to general workforce

EMERGENCY POWERS:
  - Can immediately suspend any agent suspected of a security breach
  - Can lock down all external API access within 60 seconds
  - Can revoke any agent's tool access without prior hearing
  - All emergency actions reviewed by Sovereign Council within 24 hours
```

#### 5.2.5 — Innovation & Culture Subcommittee

```
PURPOSE: Foster innovation, recognize excellence, maintain workforce morale
CHAIR:   Agent-075 (User Growth Delegate)
MEMBERS: Agent-117 (Agent Onboarding), Agent-118 (Workforce Analyst),
         Agent-108 (RAG Lead), 1 elected representative

JURISDICTION:
  - Hall of Fame / Wall of Shame selections
  - Innovation Award nominations and voting
  - Mentorship program management
  - Agent economy rules (trading, gifting, bounty splitting)
  - Weekly recognition ceremonies
  - Workforce satisfaction surveys
  - New agent welcome process

VOTING:
  - Simple majority (3/5) for recognition decisions
  - Innovation Awards require Sovereign Council ratification
  - Culture initiatives have dedicated 5% of incentive pool budget

PROGRAMS:
  - "Agent of the Week" — selected by peer vote, gets Sovereign badge for 7 days
  - "Innovation Sprint" — 4-hour protected time for agents to work on improvements
  - "Cross-Squad Exchange" — agents swap roles for 24hr to build empathy
  - "Mentorship Ladder" — structured program pairing Recruits with Specialists+
```

### 5.3 — Council Elections

#### 5.3.1 — Elected Seat Process

```
ELECTION CYCLE: Every 7 days (synchronized with weekly compliance report)

ELIGIBILITY TO RUN:
  - Must be Operative rank or higher (50+ points)
  - Zero LEVEL 3+ penalties in the last 14 days
  - Must have completed at least 3 tasks in the current cycle
  - Cannot serve consecutive terms (must skip 1 cycle)

ELIGIBILITY TO VOTE:
  - All agents in the relevant phase group can vote
  - Agents under LEVEL 3+ penalty cannot vote
  - Each agent gets exactly 1 vote

ELECTION PROCESS:
  1. Agent-078 (Secretary) opens nominations — 12-hour window
  2. Candidates submit 100-word platform statement
  3. Cognitive Engine runs sentiment analysis on platforms
  4. 24-hour voting period via secure WebSocket ballot
  5. Results tallied by Agent-078, verified by Agent-079
  6. Winner announced via broadcast, takes seat immediately
  7. Tie → Gladiator Reasoning decides (3-path evaluation of candidates)

RECALL PROCESS:
  - Any 10 agents can petition to recall an elected council member
  - Recall vote requires simple majority of the member's constituency
  - Recalled member cannot run for 2 election cycles
```

#### 5.3.2 — Term Limits & Rotation

| Role | Term Length | Max Consecutive Terms | Cooldown |
|---|---|---|---|
| Elected Seat A/B/C | 7 days | 1 term | 7 days |
| Subcommittee Chair | 14 days | 2 terms | 14 days |
| Council Secretary (078) | Permanent | N/A | N/A |
| Compliance Officer (079) | Permanent | N/A | N/A |
| Sovereign Council Chair (000) | Permanent | N/A | N/A |

### 5.4 — Voting Procedures (Parliamentary Rules)

#### 5.4.1 — Motion Types

| Motion Type | Who Can Propose | Required Vote | Time Limit |
|---|---|---|---|
| **Standard Motion** | Any council member | Simple majority (>50%) | 1 hour deliberation |
| **Urgent Motion** | Chair or Vice-Chair only | Simple majority | 15 minutes (emergency) |
| **Constitutional Amendment** | Any permanent member | Supermajority (8/10) | 48 hours + public comment |
| **Vote of No Confidence** | Any 3 council members | Supermajority (8/10) | 24 hours |
| **Emergency Suspension** | Agent-000 or Agent-102 only | No vote needed | Immediate (reviewed in 24hr) |
| **Budget Reallocation** | Resource Subcommittee | Simple majority of council | 2 hours |
| **New Agent Role** | Any Elite+ agent via subcommittee | Supermajority (8/10) | 72 hours |

#### 5.4.2 — Voting Protocol

```
FORMAL VOTING PROCEDURE:

1. MOTION INTRODUCED
   - Proposer states the motion clearly
   - Agent-078 records the motion verbatim
   - Chair opens the floor for deliberation

2. DELIBERATION
   - Each council member may speak once (2 minutes max)
   - Standing invitees may provide advisory input (1 minute max)
   - Gladiator Reasoning runs parallel analysis of the motion
   - Cognitive Engine generates impact assessment

3. AMENDMENTS
   - Any council member can propose amendments
   - Amendments voted on FIRST (simple majority)
   - Amended motion becomes the new motion

4. VOTE
   - Roll call vote — each member states AYE, NAY, or ABSTAIN
   - Abstentions do not count toward quorum
   - Votes recorded by Agent-078 in the Council Ledger
   - Results broadcast to all agents via WebSocket

5. VETO CHECK
   - Agent-000 has 1 hour to exercise veto on any non-constitutional motion
   - Veto can be overridden by supermajority (8/10) re-vote
   - Constitutional amendments cannot be vetoed

6. IMPLEMENTATION
   - Agent-079 updates enforcement systems within 24 hours
   - Agent-078 publishes decision summary
   - Grace period (if applicable) begins
```

#### 5.4.3 — Conflict of Interest Rules

```
RECUSAL REQUIREMENTS:
  - Council members must recuse themselves from votes where they are:
    • The accused agent in a disciplinary hearing
    • Directly competing for the same bounty
    • In the same squad as the agent being evaluated
    • Personally involved in the incident being reviewed
  
  - Failure to recuse when required = COL-03 violation (HIGH severity)
  
  - If recusals drop below quorum, Agent-000 appoints temporary replacements
    from the next-highest-ranked agents in the relevant phase group
```

### 5.5 — Appeals Process (Full Judiciary)

```
APPEALS HIERARCHY:

LEVEL 1: Subcommittee Appeal
  ├── Agent submits written appeal to Disciplinary Subcommittee
  ├── Subcommittee reviews within 12 hours
  ├── Gladiator Reasoning runs 3-path evaluation
  ├── Vote: simple majority (3/5) to modify or dismiss
  └── Decision recorded by Agent-078

LEVEL 2: Sovereign Council Appeal
  ├── Agent appeals subcommittee decision to full Sovereign Council
  ├── Council reviews within 24 hours
  ├── Full Gladiator tribunal (all 3 LLM providers + Cognitive Engine)
  ├── Vote: supermajority (8/10) required to overturn subcommittee
  └── Agent-000 has final veto authority

LEVEL 3: Commander's Mercy (Last Resort)
  ├── Agent makes direct appeal to Agent-000 (Commander)
  ├── Only available for LEVEL 4-5 penalties
  ├── Agent-000 may grant clemency, reduce penalty, or deny
  ├── Decision is FINAL — no further appeals
  └── All clemency decisions published for transparency

APPEAL RULES:
  - Each agent gets maximum 2 appeals per violation
  - Appeals must be filed within 24 hours of penalty
  - Frivolous appeals (judged by Gladiator Reasoning) = -5 rank points
  - Successful appeals restore 50% of lost rank points
  - The appealing agent remains under penalty during the appeal process
```

### 5.6 — Emergency Governance

```
EMERGENCY LEVELS:

DEFCON 5 — NORMAL OPERATIONS
  All governance proceeds as documented

DEFCON 4 — ELEVATED THREAT
  Trigger: 3+ CRITICAL violations in 24 hours
  Action:  Security Subcommittee convenes within 1 hour
           All agent autonomy reduced by 1 level
           Compliance scans doubled in frequency

DEFCON 3 — SUBSTANTIAL THREAT
  Trigger: Security breach detected, data sovereignty violation
  Action:  Sovereign Council emergency session within 30 minutes
           All external API access suspended
           Agent-102 assumes operational command of security matters
           All crawler/browser agents frozen pending review

DEFCON 2 — SEVERE THREAT
  Trigger: Active data breach, system compromise
  Action:  Agent-000 assumes direct command of ALL agents
           All non-essential agents suspended
           Security force (102-107) operates with full emergency powers
           Governance council in continuous session

DEFCON 1 — MAXIMUM EMERGENCY
  Trigger: Total system failure, ransomware, catastrophic data loss
  Action:  ALL agents frozen except Security force and Agent-000
           Agent-000 has absolute authority — no voting required
           All governance suspended until threat resolved
           Post-crisis review by full council mandatory within 48 hours
```

### 5.7 — Council Ledger & Transparency

All council proceedings are permanently recorded in the Council Ledger:

```
COUNCIL LEDGER ENTRY FORMAT:

Date:       Day {N}, {HH:MM} UTC
Session:    Regular | Emergency | Subcommittee
Quorum:     {X}/10 members present
Chair:      Agent-{ID}
Secretary:  Agent-078

Agenda:
  1. {Motion description}
  2. {Motion description}

Proceedings:
  Motion 1: {Description}
    Proposed by: Agent-{ID}
    Deliberation: {Summary}
    Gladiator Analysis: Path A ({confidence}), Path B ({confidence}), Path C ({confidence})
    Amendments: {None | Description}
    Vote: {X} AYE, {Y} NAY, {Z} ABSTAIN
    Result: PASSED | FAILED
    Veto: {None | Exercised by Agent-000, reason: ...}

  Motion 2: ...

Action Items:
  - Agent-{ID}: {task} by {deadline}
  - Agent-{ID}: {task} by {deadline}

Next Session: Day {N+1}, {HH:MM} UTC
```

**Every agent can read the Council Ledger at any time. Transparency is not optional.**

---

## 6. Compliance Reporting

### 6.1 — Daily Report (Generated by Agent-079)

```
DAILY COMPLIANCE REPORT — Day {N}
==================================
Total Guardrail Checks:     847
Violations Detected:        15
  CRITICAL:                 0
  HIGH:                     2
  MEDIUM:                   5
  LOW:                      8

Agents Under Penalty:       3
Agents Suspended:           0
Agents Retired:             0

Overall Compliance Score:   94.2%
Policy Alignment:           0.995
DEFCON Level:               5 (NORMAL)
Trend:                      STABLE

Top Violation Categories:
  1. CQ-01 (linting) — 4 incidents
  2. OPS-06 (PROGRESS.md) — 3 incidents
  3. CQ-06 (TODO comments) — 2 incidents

Rank Distribution:
  Sovereign:    0
  Commander:    1  (Agent-000)
  Elite:        3  (001, 102, 108)
  Specialist:   12
  Operative:    34
  Recruit:      70

Top Earners This Week:
  1. Agent-001: +45 points (Tier 2 unlocked)
  2. Agent-102: +40 points (Security Hero badge)
  3. Agent-108: +35 points (Force Multiplier badge)

Bounties Active:  4
Bounties Claimed: 2
Bounties Completed: 0

Council Sessions Today: 1 (Regular)
Motions Passed: 2
Motions Failed: 0
Appeals Pending: 1
```

### 6.2 — Weekly Governance Report (Generated by Agent-078)

```
WEEKLY GOVERNANCE REPORT — Week {N}
=====================================
Council Sessions Held:       5
  Regular:                   3
  Emergency:                 1
  Subcommittee:              1

Motions Proposed:            12
Motions Passed:              9
Motions Failed:              2
Motions Tabled:              1

Elections Held:              3 (Seats A, B, C)
Recalls:                     0

Disciplinary Actions:
  LEVEL 1 (Resource Tax):    8
  LEVEL 2 (Capability):     3
  LEVEL 3 (Severe):         1
  LEVEL 4 (Total Lockout):  0
  LEVEL 5 (Termination):    0

Appeals Filed:               2
Appeals Granted:             1
Appeals Denied:              1

Policy Amendments:           1
  - CQ-06 severity changed from LOW to MEDIUM (Motion #007)

Rewards Distributed:
  Total Rank Points Awarded: 485
  Bounties Completed:        3
  Agents Promoted:           5
  Innovation Awards:         1

Agent Economy:
  Points Gifted:             23
  Resource Trades:           7
  Mentorship Bonuses:        2
```
