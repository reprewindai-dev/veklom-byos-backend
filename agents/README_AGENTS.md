# Veklom Agents — Multi-Provider AI Agent System

Full Level-3 autonomous agent implementation across 4 LLM providers.
Every agent runs the same THINK → ACT → OBSERVE → ITERATE loop.
Only the LLM inference backend changes.

## Provider Comparison

| File | Provider | Cost | Latency | Best For |
|---|---|---|---|---|
| `agent_loop.py` | OpenAI GPT-4o-mini | ~$0.001/call | ~800ms | Best tool-calling accuracy |
| `agent_groq.py` | Groq Llama 3.3 70B | ~$0.0001/call | ~150ms | High-throughput pipelines |
| `agent_ollama.py` | Ollama (local) | $0.00 | ~500ms | 100% sovereign, no data leaves Hetzner |
| `agent_huggingface.py` | HuggingFace Inference | Free tier / endpoint | ~1-3s | Open model experimentation |

## Quick Start

### Use the Router (recommended)

```bash
# Run with Groq (default — fastest)
VEKLOM_AGENT_PROVIDER=groq python agents/agent_router.py

# Run with Ollama (local / sovereign)
VEKLOM_AGENT_PROVIDER=ollama OLLAMA_MODEL=llama3 python agents/agent_router.py

# Run with HuggingFace
VEKLOM_AGENT_PROVIDER=huggingface HF_MODEL=mistralai/Mistral-7B-Instruct-v0.3 python agents/agent_router.py

# Run with OpenAI
VEKLOM_AGENT_PROVIDER=openai python agents/agent_router.py

# Custom goal
AGENT_GOAL="List all vendors and check which ones have active contracts" \
  VEKLOM_AGENT_PROVIDER=groq python agents/agent_router.py
```

### Run a specific provider directly

```bash
python agents/agent_ollama.py
python agents/agent_groq.py
python agents/agent_huggingface.py
```

## Required Env Vars by Provider

### All providers
```
VEKLOM_API_URL=https://veklom.com/api/v1
VEKLOM_API_KEY=your_jwt_here
```

### OpenAI
```
OPENAI_API_KEY=sk-...
```

### Groq
```
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile
```
Get key: https://console.groq.com

### Ollama (Hetzner local)
```
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
```
Install: `curl -fsSL https://ollama.com/install.sh | sh && ollama pull llama3`

### HuggingFace
```
HF_API_TOKEN=hf_...
HF_MODEL=mistralai/Mistral-7B-Instruct-v0.3
HF_ENDPOINT_URL=https://your-endpoint.huggingface.cloud  # optional private endpoint
```
Get token: https://huggingface.co/settings/tokens

## Agent Architecture

```
Agent Goal
    │
    ▼
[ROUTER] — selects provider via VEKLOM_AGENT_PROVIDER
    │
    ▼
[THINK]  LLM reasons, picks a tool (or says DONE)
    │
    ▼
[ACT]    Tool called: check_backend_health | run_governed_workflow | list_vendors
    │
    ▼
[OBSERVE] Result injected into LLM context
    │
    ▼
[ITERATE?] LLM judges: goal met? → DONE : loop again (max 10 iterations)
    │
    ▼
[FINAL OUTPUT] — structured result returned
```

## Adding New Tools

1. Write `async def tool_<name>(...)` in any agent file.
2. Add to `TOOL_MAP`.
3. Add JSON schema to `TOOL_SCHEMAS` (OpenAI/Groq) or `TOOL_DESCRIPTIONS` (Ollama/HF).

All 4 providers pick up the new tool automatically.

## IronGrid MCP Gateway

See `irongrid/server.py` — exposes `execute_governed_workflow` as an MCP tool
consumable by Cursor, Claude Desktop, and any IDE workforce.

Mount config: `irongrid/mcp_client_config.json`
