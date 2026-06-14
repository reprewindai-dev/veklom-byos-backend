# Interactive Graph Pipeline Sandbox — Dev Spec (no code yet)

**Status:** spec for review (you / Codex) before implementation.
**Principle:** do NOT rebuild. ~90% already exists in `pipelines.py` + `autonomous_worker.py`.
This spec fills the **two real gaps** and threads them through the PGL Genome keystone.

---

## 0. What already exists (DO NOT TOUCH — verified in code)

| Capability | Endpoint / code | Status |
|---|---|---|
| Graph canvas persistence | `GET/PUT/POST /pipelines/{id}/graph` (nodes, edges, viewport, node_configs) | real |
| Governed node catalog | `GET /pipelines/nodes` (certification: real/configured) | real |
| Templates | `GET /pipelines/templates` | real |
| Pipeline CRUD | `/pipelines`, `/pipelines/{id}` | real |
| Governed run | `POST /pipelines/{id}/run` → `run_pipeline_background` | real (LangChain) |
| Live step streaming | `GET /pipelines/{id}/runs/{run_id}/stream` (SSE) | real |
| Human-in-the-loop | `POST /pipelines/{id}/runs/{run_id}/approve` (ASK_HUMAN) | real |
| Run history/detail | `/pipelines/{id}/runs`, `/runs/{run_id}` | real |
| Deployments | `/deployments` CRUD + pause/resume (persisted rows) | real |
| PGL ledger | `pgl_certificates`, `pgl_ledger_events`, `PGLClient(db)`, `/genome/*` | real (shipped) |

## The two real gaps

1. **`GET /pipeline/interactive/session`** returns `{"session_id": "ips_placeholder", ...}` — a stub. No real session object, no PGL stamp, no link to a pipeline/graph/stream.
2. **Node-level routing** — `langchain_agent`/model nodes pick a model implicitly. The `ArbiterGovernanceKernel` (deterministic clearance/context/latency/complexity gates → cheapest viable node → x402 toll) is not wired as the per-node executor.

---

## 1. Gap #1 — Real PGL-stamped Interactive Session

### Object: `InteractiveSession` (new model `db/models/sandbox.py`, auto-creates)
```
sandbox_sessions
  session_id        str pk  (ips_<uuid>)
  workspace_id      str index
  actor_id          str index
  pipeline_id       str index            # bound pipeline (or 'clinical-rag' default)
  pgl_pre_cert_id   str | null           # from PGLClient.commit_intent
  pgl_post_cert_id  str | null           # from PGLClient.attest_outcome on close
  status            str  (ready|running|held|sealed|failed)
  graph_snapshot    JSON                 # frozen graph at session open
  current_run_id    str | null
  created_at, updated_at
```

### Routes (replace the stub)
```
POST /api/v1/pipeline/interactive/session
  body: { pipeline_id?: str }            # defaults to workspace's clinical-rag
  action:
    1. resolve pipeline + load graph (reuse _get_or_create_pipeline + graph)
    2. PGLClient(db).commit_intent(workspace_id, actor_id,
         genome_hash=hash(graph_snapshot), constitution_hash=<agent law hash>,
         plan_hash=hash(pipeline_id))     -> pre_execution_certificate_id
    3. persist InteractiveSession (status=ready)
  returns:
    {
      session_id, status: "ready",
      pipeline_id, graph: {nodes, edges, viewport, node_configs},
      stages: ["source","build","validate","test","stage","gate","deploy"],
      pgl: { certificate_id, persisted: true, event_hash },
      stream_url: "/api/v1/pipelines/{pipeline_id}/runs/{run_id}/stream"  # filled after run
    }

GET  /api/v1/pipeline/interactive/session/{session_id}
  returns the session + bound run status + PGL trail summary (cert ids, ledger head)

POST /api/v1/pipeline/interactive/session/{session_id}/run
  action: call existing run_pipeline_background; set current_run_id; status=running
  returns: { run_id, stream_url }

POST /api/v1/pipeline/interactive/session/{session_id}/close
  action: PGLClient(db).attest_outcome(pre_cert, output_hash=hash(final_state),
            outcome_hash=hash(run_outcome)) ; verify_chain ; status=sealed
  returns: { session_id, status: "sealed", pgl_post_cert_id, chain: {verified, events} }
```

### Wiring notes
- Reuse existing run + SSE endpoints — the session just **binds + PGL-stamps** them.
- `commit_intent`/`attest_outcome` already persist to the real ledger via `PGLClient(db)` (flush, not commit — caller commits).
- Public? No. Authed route; not added to ZeroTrust public_prefixes.
- ZeroTrust/x402: `/pipeline/interactive/*` may be gated for free tier per existing x402 `free_restricted` list — confirm intended tier.

---

## 2. Gap #2 — Arbiter node router (deterministic + x402)

### Map ArbiterGovernanceKernel onto existing structures
| Arbiter concept | Veklom source of truth |
|---|---|
| `NodeCapability` fleet | `/routing` topology + IronGrid substrate + provider registry (`providers.py`) |
| `AgentIntent.security_clearance` | node_config + workspace governance profile (region/compliance locks) |
| `_verify_payment` (x402) | existing `backend/core/middleware/x402.py` + `/wallet` balance |
| `calculate_route` gates | new `services/arbiter.py` (clearance/context/latency/complexity → cheapest viable) |
| chosen node + cost | recorded to `PipelineRun` evidence + a PGL ledger event |

### Where it plugs in
- Inside `autonomous_worker` node execution for `langchain_agent` / model nodes:
  1. Build `AgentIntent` from node_config (prompt, tokens, latency SLA, complexity, clearance).
  2. `arbiter.calculate_route(intent)` → selected node (deterministic, policy-gated).
  3. x402 toll check (reuse middleware/wallet) → 402 envelope if unpaid.
  4. Execute against selected provider (existing provider_router).
  5. Append PGL ledger event `event_type="node_route"` with {node_id, cost, gates_passed}.
  6. Emit SSE step event with the chosen node + cost (feeds the canvas node's inline price tag).

### New: `services/arbiter.py`
- `ArbiterGovernanceKernel` (the pasted code), but `ACTIVE_FLEET` loaded from DB/registry, not hardcoded.
- `_verify_payment` delegates to the real x402 verifier, not pseudo `return True`.
- Raises the same 402 envelope the platform already uses (`WWW-Authenticate: x402 ...`, treasury `VEKLOM_TREASURY` from `x402.py`).

---

## 3. End-to-end flow (the "sandbox" loop)

```
open session  → PGL commit_intent (pre-cert)         [Identity]
   ↓
load graph (canvas)                                  [Build]
   ↓
run → for each node:
     Arbiter.calculate_route → gates → cheapest node  [Constraint]
     x402 toll                                         [Constraint]
     execute (LangChain/provider)                      [Execution]
     SSE step event (node + cost + policy)             [Observation]
     PGL ledger event (node_route / node_attest)       [Observation/Proof]
     ASK_HUMAN pause if node requires approval          [human-on-the-loop]
   ↓
close session → PGL attest_outcome (post-cert) + verify_chain   [Proof]
   ↓
evidence pack (existing evidence-pack node) + /genome/verify     [Proof]
```
This is exactly the governed loop from `SYSTEM_MAP.md`, expressed as an interactive canvas.

---

## 4. Data shapes

**SSE step event (extend existing stream):**
```json
{ "type": "node.step", "node_id": "demo-agent", "status": "executing",
  "route": { "node": "claude-haiku", "cost_usd": 0.0003, "gates_passed": ["clearance","latency","complexity"] },
  "pgl_event_hash": "ab12...", "ts": "..." }
```

**Arbiter route decision (recorded to run evidence):**
```json
{ "selected_node": "claude-haiku", "reason": "cheapest viable",
  "rejected": [{"node":"gpt-4o","reason":"cost"}],
  "cost_usd": 0.0003, "x402": {"paid": true, "receipt": "..."} }
```

---

## 5. Honesty rules (carry the existing discipline)
- Node catalog `certification.status` (real/configured) must surface on each canvas node.
- If Arbiter finds no viable node → 503 with the real reason (already in the kernel).
- If a node is `configured` but missing its requirement (e.g., `OPENAI_API_KEY`) → show `NOT_CONFIGURED`, do not fake execution.
- Simulated vs live execution must be labeled in the SSE stream.

## 6. Build order + acceptance
1. `InteractiveSession` model + 4 session routes (PGL-stamped). **Accept:** open→run→close produces a verifiable PGL chain (`/genome/verify` events increment; pre+post certs linked).
2. `services/arbiter.py` + node-execution wiring + x402 + ledger event. **Accept:** each node run records a route decision + PGL `node_route` event; unpaid → 402; no viable node → 503.
3. Frontend canvas (sovereign-control-node): inline price tags, policy chips, PGL trail chip per node, live SSE.

## 7. Do NOT
- Do not rebuild the graph/run/stream/approve/deployment endpoints — they're real.
- Do not hardcode the Arbiter fleet in prod — load from registry.
- Do not let `_verify_payment` return True unconditionally — wire the real x402 verifier.
- Do not bypass the orchestrator/PGL for execution (no anonymous execution).
