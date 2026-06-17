---
name: runtime-guard
description: Performs pre-flight predictive emulation to ensure a task is safe and cost-effective before execution. Use when verifying tasks for model routing, cost estimation, privacy checks, latency, and fallback.
---


# Runtime-Guard Skill


This skill enforces "verify-before-incurring." It runs a local simulation to verify policy, cost, and risk before any live execution.


## When to use this skill


- When a task involves calling an external LLM or tool that could incur compute cost or leak data.
- When routing between internal/private models and public APIs based on data sensitivity.
- When you need to compute token estimates and choose the lowest-latency route.


## How to use it


1. **Gather Input Parameters**
   - Task prompt
   - Tenant's policy and budget settings
   - Requested model/provider
   - Evidence requirements
   - Risk tier and fallback options


2. **Run Pre-Flight Emulation**
   - Perform privacy classification: detect PII/PHI and other sensitive data.
   - Estimate token and cost usage using your cost heuristics.
   - Determine if the prompt and retrieved context fit within policy.
   - Compute latency estimates based on model/provider.
   - Enforce fallback rules: route to local or private models if sensitive.


3. **Decision**
   - If policy passes, budget permits, and latency is within limits, mark as **Clear to run**.
   - Otherwise, block the action and emit a detailed `DecisionFrame` explaining why (e.g., privacy violation or budget overrun).


4. **Log Evidence**
   - Record the input, simulation results, and decision in a deterministic `RuntimeRecord` for replay.
   - Provide relevant metadata (model, latency, cost) to the user or Command Center.


5. **Trigger Live Dispatch (When Safe)**
   - Only after the simulation confirms the run is safe and approved, proceed to the live execution stage.
   - Continuously monitor for latency spikes or policy violations during live dispatch, and stop the run if needed.


## Best Practices


- Always run the simulation before any model call that might incur cost or risk.
- If unsure, default to local/private models and require human approval.
- Use the recorded evidence to support compliance and audit requirements.


## DecisionFrame Schema


```json
{
  "task_id": "uuid",
  "status": "CLEAR" | "BLOCKED" | "PENDING_APPROVAL",
  "reason": "string",
  "privacy_flags": ["PII", "PHI"],
  "estimated_tokens": 0,
  "estimated_cost_usd": 0.0,
  "estimated_latency_ms": 0,
  "recommended_provider": "string",
  "fallback_provider": "string",
  "evaluated_at": "ISO8601 timestamp"
}
```


## RuntimeRecord Schema


```json
{
  "record_id": "uuid",
  "task_id": "uuid",
  "tenant_id": "string",
  "decision_frame": {},
  "simulation_log": ["string"],
  "recorded_at": "ISO8601 timestamp"
}
```
