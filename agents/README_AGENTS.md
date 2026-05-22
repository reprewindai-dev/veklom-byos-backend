# Veklom Agents

This directory contains the Level-3 autonomous agent implementation for the Veklom platform.

## Files

| File | Purpose |
|---|---|
| `agent_loop.py` | Core THINK → ACT → OBSERVE → ITERATE loop |

## How the Agent Works

```
Goal received
    │
    ▼
[THINK]  LLM reasons, decides which tool to call
    │
    ▼
[ACT]    Tool is called (backend health, workflow, vendor list, etc.)
    │
    ▼
[OBSERVE] Result returned to LLM memory
    │
    ▼
[ITERATE?] LLM judges: goal achieved? → DONE : loop again
```

## Quick Start

```bash
# 1. Set env vars
export VEKLOM_API_URL=https://veklom.com/api/v1
export VEKLOM_API_KEY=your_jwt_here
export OPENAI_API_KEY=your_openai_key_here

# 2. Install deps
pip install openai httpx

# 3. Run
python agents/agent_loop.py
```

## Adding New Tools

1. Write an `async def tool_<name>(...)` function in `agent_loop.py`.
2. Add it to `TOOL_MAP`.
3. Add its JSON Schema to `TOOL_SCHEMAS`.

The agent will automatically discover and use it on the next run.

## IronGrid MCP Gateway

See `irongrid/server.py` — this is the FastMCP server that exposes
`execute_governed_workflow` as an MCP tool consumable by Cursor,
Claude Desktop, and any 120-agent workforce.

Mount config: `irongrid/mcp_client_config.json`
