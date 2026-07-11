# Veklom Python SDK

Official Python client and CLI for the [Veklom Sovereign AI Hub](https://veklom.com).

---

## Installation

```bash
pip install veklom            # SDK only
pip install "veklom[cli]"     # SDK + veklom CLI (adds coloured output)
```

Or install straight from the repo:

```bash
pip install "sdk/python[cli]"          # from repo root
pip install -e "sdk/python[cli]"       # editable / dev mode
```

---

## Quick Start

### Set your API key

```bash
export VEKLOM_API_KEY="your-bearer-token"
# Optional: override for self-hosted
export VEKLOM_BASE_URL="http://localhost:80/api/v1"
```

---

## CLI

After installation the `veklom` command is available globally.

### One-shot ask (streams by default)

```bash
veklom ask "What is Veklom?"
veklom ask "Summarise governance in three bullet points" --model gemini-2.5-flash
veklom ask "Write a haiku" --no-stream --verbose
```

### Interactive chat REPL

```bash
veklom chat
veklom chat --session my-project --model llama-3.1-8b-instant
```

Inside the REPL:
- Type your message and press Enter
- `/clear` — reset session memory
- `exit` / Ctrl-C — quit

### List models

```bash
veklom models
veklom models --json
```

### Provider routing table

```bash
veklom providers
```

### Health check

```bash
veklom status
```

### Global flags

| Flag | Description |
|---|---|
| `--key TOKEN` | API key / Bearer token (overrides env var) |
| `--base-url URL` | Override API base URL |
| `--json` | Print raw JSON output |
| `-v / --verbose` | Show governance metadata (provider, latency, cost, audit_id) |

---

## Python SDK

### Synchronous

```python
from veklom import VeklomClient

client = VeklomClient(api_key="your-key")

# One-shot completion
resp = client.complete("Explain governed AI in one sentence.")
print(resp["response_text"])
print(f"Latency: {resp['latency_ms']}ms | Cost: ${resp['cost_usd']}")

# Streaming
for chunk in client.complete_stream("Write a haiku about governance."):
    print(chunk, end="", flush=True)

# Multi-turn chat (Redis-backed, 20-msg / 24h)
r1 = client.chat("Hi! What do you do?", session_id="demo")
r2 = client.chat("Tell me more.", session_id="demo")

# Cached inference (hot/warm tiers)
resp = client.inference("Classify this intent: 'deploy the model'")

# Metadata
print(client.models())
print(client.providers())
print(client.health())
```

### Async

```python
import asyncio
from veklom import AsyncVeklomClient

async def main():
    async with AsyncVeklomClient(api_key="your-key") as client:
        # Regular call
        resp = await client.complete("Hello, Veklom!")
        print(resp["response_text"])

        # Streaming
        async for chunk in client.complete_stream("Write a haiku."):
            print(chunk, end="", flush=True)

asyncio.run(main())
```

---

## Response Shape

All completion calls return a dict like:

```json
{
  "id": "run_42",
  "response_text": "...",
  "provider": "groq",
  "model": "llama-3.1-8b-instant",
  "latency_ms": 312,
  "cost_usd": 0.000002,
  "audit_id": 42,
  "policy": {"status": "passed", "policy_id": "outbound.public.v3"},
  "input_tokens": 18,
  "output_tokens": 64
}
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `VEKLOM_API_KEY` | — | Bearer token for auth |
| `VEKLOM_BASE_URL` | `https://veklom.com/api/v1` | API base URL |
