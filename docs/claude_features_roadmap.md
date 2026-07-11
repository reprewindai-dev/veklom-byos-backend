# Claude API Features → Veklom Sovereign Implementations

This document maps every major Anthropic Claude API feature to its
equivalent sovereign implementation inside `veklom-byos-backend`.

Philosophy: **Same pattern, zero cloud cost, zero data leakage.**
Ollama runs on Hetzner. Users get the same capabilities.
We keep the margin.

---

## ✅ Implemented

### 1. Message Batches API → `vnp_batch_evaluator.py`
**Claude version:** Submit 100k requests in one call, processed async, 50% cheaper.  
**Our version:** `asyncio.gather()` + Semaphore concurrency control over local Ollama.  
**Benefit to users:** VNP fleet probes evaluate 360 agents in ~10s instead of 6-12 min.  
**Benefit to us:** $0 inference cost vs $0.50/MTok even at batch pricing.

---

## 🗺️ Roadmap — Features to Mine from Claude Docs

### 2. Prompt Caching → Veklom Context Cache
**Claude version:** Cache large system prompts for 5 min (ephemeral) or 1 hour (extended).
Reuses tokens, cuts costs 90%+ on repeated prompts.  
**Our version:** Redis-backed prompt prefix cache in `core/memory/`.  
For VNP fleet: the system prompt is identical across all 360 agent evals.
Cache it in Redis once, inject for every `ollama_chat()` call.  
**Benefit to users:** Faster agent responses on repeated workflows.  
**Benefit to us:** Ollama context loading is the bottleneck — caching cuts GPU time.

### 3. Extended Thinking → Veklom Deep Reasoning Mode
**Claude version:** Claude internally "thinks" before answering. Better on complex tasks.
Billed per thinking token.  
**Our version:** Multi-step chain-of-thought injected into system prompt:
```python
system = (
    "Think step by step before answering. "
    "First output <thinking>...</thinking> then your final answer."
)
```
Already partially done in `run_agent()`. Make it a flag: `deep_reasoning=True`.  
**Benefit to users:** Better quality on complex treasury/SLA decisions.  
**Benefit to us:** Differentiator — 'Deep Mode' as a premium tier toggle.

### 4. Tool Use / Function Calling → Veklom TOOL_MAP
**Claude version:** Structured `tools=[]` parameter, Claude decides when to call.  
**Our version:** Already implemented in `agent_ollama.py` via `TOOL_MAP` + JSON parsing.  
**Gap:** No formal schema validation. Claude enforces strict input/output schemas.  
**Action:** Add Pydantic models for each tool's input/output. Validate before dispatch.

### 5. Vision / Multimodal → Veklom Multimodal Ingest
**Claude version:** Pass base64 images in `content` blocks alongside text.  
**Our version:** Ollama supports `llava`, `bakllava`, `moondream` for local vision.  
**Action:** Add `tool_analyze_image(image_path: str)` to `TOOL_MAP`.
Vendors can upload API screenshots; agents diagnose visually.  
**Benefit to users:** Visual SLA breach evidence (screenshot of error page).  
**Benefit to us:** Premium feature — vision-powered incident reports.

### 6. Computer Use → Veklom Headless Browser Agent
**Claude version:** Claude controls a virtual desktop — clicks, types, navigates.  
**Our version:** `playwright` + local Chromium on Hetzner.  
**Action:** Add `tool_browser_navigate(url)`, `tool_browser_click(selector)`,
`tool_browser_screenshot()` to TOOL_MAP.  
**Benefit to users:** Agents can actually test vendor API web portals end-to-end.  
**Benefit to us:** No one else in the VNP space has headless browser agents.

### 7. Files API → Veklom Document Store
**Claude version:** Upload PDFs/CSVs once, reference by file_id across many requests.  
**Our version:** MinIO or local disk + file_id in Postgres.  
**Action:** `POST /api/v1/files/upload` → returns `file_id`.  
Agents reference `file_id` instead of re-embedding documents every call.  
**Benefit to users:** Upload vendor SLA contracts once; agents reference forever.  
**Benefit to us:** Sticky data = sticky users.

### 8. Streaming → Veklom SSE Agent Stream
**Claude version:** `stream=True` returns tokens as they're generated.  
**Our version:** Ollama supports `stream=True` natively.  
**Action:** Add `/api/v1/agent/stream` endpoint using FastAPI `StreamingResponse`.  
```python
async def stream_agent(goal: str):
    async with httpx.AsyncClient() as client:
        async with client.stream('POST', f'{OLLAMA_BASE_URL}/api/chat',
                                 json={**payload, 'stream': True}) as r:
            async for chunk in r.aiter_text():
                yield f'data: {chunk}\n\n'
```
**Benefit to users:** See agent thinking in real-time in the Veklom UI.  
**Benefit to us:** Premium UX differentiator.

### 9. Model Context Protocol (MCP) → Veklom Tool Marketplace
**Claude version:** Standardized protocol for connecting external tools to Claude.
Third parties publish MCP servers; Claude connects dynamically.  
**Our version:** `TOOL_MAP` is already this — a dynamic tool registry.  
**Action:** Expose `TOOL_MAP` as an MCP-compatible server endpoint so ANY
MCP-aware client (Claude Desktop, Cursor, etc.) can use Veklom tools.  
**Benefit to users:** Their Claude Desktop can call Veklom BYOS endpoints directly.  
**Benefit to us:** Veklom becomes an MCP server in the ecosystem.

### 10. Rate Limit Handling → Veklom Queue & Retry
**Claude version:** 429s with retry-after headers.  
**Our version:** No rate limits on local Ollama — but GPU can saturate.  
**Action:** The Semaphore in `vnp_batch_evaluator.py` is the foundation.
Expand to a Redis-backed priority queue for all agent calls.
High-priority (treasury/SLA) jumps the queue. Background (analytics) waits.  
**Benefit to users:** SLA breach detection is never delayed by analytics jobs.  
**Benefit to us:** Predictable GPU utilization = no crashes at peak load.

---

## Priority Order

| # | Feature | Effort | User Impact | Revenue Impact |
|---|---------|--------|-------------|----------------|
| 1 | Prompt Caching (Redis) | Low | High (speed) | Medium (GPU savings) |
| 2 | Streaming SSE | Medium | High (UX) | High (premium) |
| 3 | Extended Thinking flag | Low | Medium | High (premium tier) |
| 4 | MCP Server endpoint | Medium | High (ecosystem) | High (distribution) |
| 5 | Vision (llava) | Medium | Medium | High (premium) |
| 6 | Files API | Medium | Medium | Medium (stickiness) |
| 7 | Tool Schema Validation | Low | Low | Low (reliability) |
| 8 | Browser Agent | High | High | High (unique) |

---

*Last updated: auto-generated by AI pair programming session*  
*Reference: https://platform.claude.com/docs/en/build-with-claude/batch-processing*
