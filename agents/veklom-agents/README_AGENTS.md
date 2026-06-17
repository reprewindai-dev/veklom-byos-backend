# Veklom Agents — Ollama-First Sovereign AI

Ollama is the **primary and default** agent engine.
All inference runs on your Hetzner server.
Zero data leaves your sovereign infrastructure. Zero cost per call.

## Provider Priority

| Priority | File | Provider | Cost | Speed | Sovereignty |
|---|---|---|---|---|---|
| **1 (PRIMARY)** | `agent_ollama.py` | Ollama (local) | **$0.00** | ~500ms | **100% sovereign** |
| 2 | `agent_groq.py` | Groq cloud | ~$0.0001 | ~150ms | Cloud |
| 3 | `agent_loop.py` | OpenAI | ~$0.001 | ~800ms | Cloud |
| 4 | `agent_huggingface.py` | HuggingFace | Free tier | ~1-3s | Cloud/endpoint |

## Quick Start

### One-time Hetzner setup
```bash
bash agents/ollama_setup.sh
```
This installs Ollama, pulls llama3 + mistral + phi3, and verifies the API.

### Run the sovereign agent
```bash
# Default goal (health + vendors + revenue + nodes)
python agents/agent_ollama.py

# Custom goal via CLI
python agents/agent_ollama.py "List all tenants and check their Operating Reserve balances"
python agents/agent_ollama.py "Run a governed workflow for tenant demo-1 with intent 'Q2 compliance audit'"
python agents/agent_ollama.py "Check IronGrid node status and route a test payload"

# Via router (ollama is default)
python agents/agent_router.py
AGENT_GOAL="Get revenue summary" python agents/agent_router.py
```

### Switch models
```bash
OLLAMA_MODEL=mistral python agents/agent_ollama.py
OLLAMA_MODEL=phi3 python agents/agent_ollama.py
OLLAMA_MODEL=gemma2 python agents/agent_ollama.py
```

## Env Vars

```bash
# Ollama (sovereign — runs on Hetzner)
OLLAMA_BASE_URL=http://localhost:11434   # default
OLLAMA_MODEL=llama3                      # default
OLLAMA_TIMEOUT=120                       # seconds
VEKLOM_AGENT_PROVIDER=ollama             # default

# Veklom backend
VEKLOM_API_URL=https://veklom.com/api/v1
VEKLOM_API_KEY=your_jwt_here

# Debug
AGENT_DEBUG=1   # verbose LLM output
AGENT_MAX_ITER=10
```

## Tool Suite (15 tools wired to BYOS backend)

| Tool | Endpoint | What It Does |
|---|---|---|
| `health` | GET /health | BYOS backend health check |
| `list_vendors` | GET /marketplace/vendors | All marketplace vendors |
| `list_models` | GET /marketplace/models | All AI models in marketplace |
| `get_vendor` | GET /marketplace/vendors/:id | Specific vendor detail |
| `run_workflow` | POST /workflows/execute | Execute governed AI task + bill tenant |
| `get_workflow_status` | GET /workflows/:id/status | Check workflow progress |
| `list_tenants` | GET /tenants | All tenants |
| `get_tenant` | GET /tenants/:id | Tenant detail |
| `get_tenant_balance` | GET /tenants/:id/balance | Operating Reserve balance |
| `get_revenue_summary` | GET /billing/revenue/summary | Platform revenue totals |
| `get_audit_log` | GET /audit/log | Immutable SHA-256 audit trail |
| `get_node_status` | GET /irongrid/nodes | IronGrid node health |
| `route_to_node` | POST /irongrid/route | Route payload to optimal node |
| `ollama_list_models` | Ollama /api/tags | Models available locally |
| `ollama_pull_model` | Ollama /api/pull | Pull new model to Hetzner |

## Agent Architecture

```
Goal (CLI or API call)
    │
    ▼
[ROUTER] — VEKLOM_AGENT_PROVIDER (default: ollama)
    │
    ▼
[THINK]  Ollama LLM on Hetzner reasons, picks tool
    │
    ▼
[ACT]    Tool called → real BYOS backend endpoint hit
    │
    ▼
[OBSERVE] Result injected into LLM context
    │
    ▼
[ITERATE?] Done? → output answer : loop again
    │
    ▼
[AUDIT] SHA-256 session fingerprint written
    │
    ▼
Final structured output: {answer, iterations, audit_hash, sovereign: true}
```

## Adding New Tools

1. Write `async def tool_<name>(...)` in `agent_ollama.py`
2. Add to `TOOL_MAP`
3. Add one line to `TOOL_SCHEMA_TEXT`

All providers and the router pick it up instantly.
