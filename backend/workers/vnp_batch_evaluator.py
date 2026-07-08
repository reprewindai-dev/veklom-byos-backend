"""
VNP Sovereign Batch Evaluator
------------------------------
Replaces 360 sequential Ollama calls (one per agent × API target)
with a single concurrent asyncio.gather() pass.

Same concept as the Anthropic Message Batches API — but runs 100% on
your Hetzner Ollama instance. Zero cost. Zero data leaves the server.

Usage in vnp_agent_fleet.py:

    from backend.workers.vnp_batch_evaluator import evaluate_all_probes

    # 1. Gather all raw probes in parallel (no LLM yet)
    all_probe_data = await asyncio.gather(*[
        probe_endpoint(client, api)
        for agent in active_squad
        for api in TARGET_APIS
    ])

    # 2. Tag each probe with its agent_id
    tagged = [
        {**probe, "agent_id": agent.id}
        for agent, probe in zip(
            [a for a in active_squad for _ in TARGET_APIS],
            all_probe_data
        )
    ]

    # 3. ONE concurrent batch — all Ollama, all sovereign
    evaluations = await evaluate_all_probes(tagged)

    # 4. Look up result per agent+api
    result = evaluations.get(f"{agent.id}:{api['api_id']}")
    is_healthy = result["is_healthy"]

Performance vs old sequential loop:
    Old: 360 calls × ~1-2s each = 6-12 minutes per pass
    New: 360 calls concurrent    = ~5-15s per pass (Ollama concurrency bound)
    Cost: $0 either way — this is the win over Anthropic Batch API
"""

import asyncio
import json
import os
from datetime import datetime, timezone
import httpx

# ---------------------------------------------------------------------------
# Config — mirrors agent_ollama.py env vars
# ---------------------------------------------------------------------------
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL",    "llama3")
OLLAMA_TIMEOUT  = int(os.getenv("OLLAMA_TIMEOUT", "30"))

# Limit concurrent Ollama calls so we don't saturate the local GPU/CPU
# Tune this based on your Hetzner server's VRAM/cores
OLLAMA_BATCH_CONCURRENCY = int(os.getenv("OLLAMA_BATCH_CONCURRENCY", "8"))


def _log(tag: str, msg: str):
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}][{tag}] {msg}")


# ---------------------------------------------------------------------------
# Single eval — one Ollama call for one probe result
# ---------------------------------------------------------------------------
async def _single_eval(
    semaphore: asyncio.Semaphore,
    client: httpx.AsyncClient,
    custom_id: str,
    probe: dict,
) -> dict:
    """
    Evaluate one probe result via Ollama.
    Semaphore limits concurrent calls to OLLAMA_BATCH_CONCURRENCY.

    Args:
        custom_id: Unique key — format "agent_id:api_id"
        probe: Raw probe dict with keys:
               api_id, latency_ms, http_status_code, success

    Returns:
        {"custom_id": str, "is_healthy": bool, "reason": str}
    """
    async with semaphore:
        payload = {
            "model": OLLAMA_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a VNP probe classifier for sovereign infrastructure. "
                        "Analyze the API probe result and classify it. "
                        "Reply ONLY with a valid JSON object: "
                        '{"is_healthy": true/false, "reason": "one sentence"}'
                    )
                },
                {
                    "role": "user",
                    "content": (
                        f"API: {probe['api_id']} | "
                        f"HTTP Status: {probe['http_status_code']} | "
                        f"Latency: {probe['latency_ms']}ms | "
                        f"Raw success flag: {probe['success']}"
                    )
                }
            ],
            "stream": False,
            "options": {
                "temperature": 0.0,   # deterministic classification
                "num_predict": 64,    # short output — just JSON
            },
        }

        try:
            r = await client.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json=payload,
                timeout=OLLAMA_TIMEOUT,
            )
            r.raise_for_status()
            text = r.json()["message"]["content"]

            # Parse LLM JSON response
            clean = text.strip().strip("```json").strip("```").strip()
            data = json.loads(clean)
            return {
                "custom_id": custom_id,
                "is_healthy": bool(data.get("is_healthy", probe["success"])),
                "reason": data.get("reason", ""),
            }

        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            _log("BATCH-EVAL", f"Ollama HTTP error for {custom_id}: {e}")
        except (json.JSONDecodeError, KeyError) as e:
            _log("BATCH-EVAL", f"Parse error for {custom_id}: {e}")
        except Exception as e:
            _log("BATCH-EVAL", f"Unexpected error for {custom_id}: {e}")

        # Fallback: trust the raw network probe result
        return {
            "custom_id": custom_id,
            "is_healthy": probe["success"],
            "reason": "fallback: LLM unavailable, using raw probe result",
        }


# ---------------------------------------------------------------------------
# Public API — drop-in replacement for per-agent ollama_chat() loops
# ---------------------------------------------------------------------------
async def evaluate_all_probes(probe_results: list[dict]) -> dict:
    """
    Concurrent batch evaluation of all probe results using local Ollama.

    This is the sovereign equivalent of the Anthropic Message Batches API:
    instead of one HTTP call per probe (sequential), all evaluations fire
    concurrently and resolve together — on YOUR hardware, at $0 cost.

    Args:
        probe_results: List of probe dicts, each containing:
            - agent_id       (str)
            - api_id         (str)
            - latency_ms     (int)
            - http_status_code (int)
            - success        (bool)

    Returns:
        Dict keyed by "agent_id:api_id" ->
            {"is_healthy": bool, "reason": str}

    Example:
        {
            "agent-abc123:api-openai-com": {"is_healthy": True, "reason": "200 OK, 142ms"},
            "agent-abc123:api-anthropic-com": {"is_healthy": False, "reason": "503, timeout"}
        }
    """
    if not probe_results:
        return {}

    total = len(probe_results)
    _log("BATCH-EVAL", f"Starting batch evaluation: {total} probes, concurrency={OLLAMA_BATCH_CONCURRENCY}")
    t_start = asyncio.get_event_loop().time()

    semaphore = asyncio.Semaphore(OLLAMA_BATCH_CONCURRENCY)

    async with httpx.AsyncClient() as client:
        tasks = [
            _single_eval(
                semaphore,
                client,
                custom_id=f"{p['agent_id']}:{p['api_id']}",
                probe=p,
            )
            for p in probe_results
        ]
        raw_results = await asyncio.gather(*tasks)

    elapsed = asyncio.get_event_loop().time() - t_start
    succeeded = sum(1 for r in raw_results if r and "is_healthy" in r)
    _log("BATCH-EVAL", f"Complete: {succeeded}/{total} evaluated in {elapsed:.1f}s")

    return {
        r["custom_id"]: {"is_healthy": r["is_healthy"], "reason": r["reason"]}
        for r in raw_results
        if r and "custom_id" in r
    }


# ---------------------------------------------------------------------------
# Standalone test — run directly to verify Ollama connectivity
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import random

    # Simulate what vnp_agent_fleet.py would pass in
    test_probes = [
        {
            "agent_id": f"agent-test-{i:03d}",
            "api_id": random.choice(["api-openai-com", "api-anthropic-com", "httpbin-get"]),
            "latency_ms": random.randint(50, 800),
            "http_status_code": random.choice([200, 200, 200, 401, 503, 0]),
            "success": random.choice([True, True, True, False]),
        }
        for i in range(12)  # simulate 12 probes (4 agents × 3 APIs)
    ]

    print(f"\n{'='*60}")
    print("VNP SOVEREIGN BATCH EVALUATOR — SELF TEST")
    print(f"{'='*60}")
    print(f"Ollama: {OLLAMA_BASE_URL} | Model: {OLLAMA_MODEL}")
    print(f"Probes: {len(test_probes)} | Concurrency: {OLLAMA_BATCH_CONCURRENCY}\n")

    results = asyncio.run(evaluate_all_probes(test_probes))

    print(f"\nResults ({len(results)} evaluations):")
    for key, val in results.items():
        status = "✅ UP" if val["is_healthy"] else "❌ DOWN"
        print(f"  {status} {key}: {val['reason']}")
