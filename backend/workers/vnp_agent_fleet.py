"""
VNP Agent Fleet Daemon
----------------------
Replaces Cloudflare Workers. Runs locally and utilizes the 120 AgentIdentities
from the PGL as the data-plane Prober Nodes.

Each agent probes target APIs, uses Persistent Redis Conversation Memory to 
detect trends, signs its judgment with Ed25519, and submits to the VNP Ingest API.
"""

import asyncio
import time
import json
import httpx
import sys
import os
import hashlib
import uuid
from datetime import datetime, timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from nacl.signing import SigningKey
from nacl.encoding import HexEncoder

from backend.core.database.database import async_session
from backend.db.models.agent import AgentIdentity
from backend.core.memory.conversation import ConversationMemory
from agents.agent_ollama import ollama_chat, log

# VNP Routing Ingest endpoint
INGESTION_URL = "http://127.0.0.1:8088/api/v1/ingest/probe-events"

# Target APIs to probe
TARGET_APIS = [
    {"api_id": "api-openai-com", "url": "https://api.openai.com/v1/models"},
    {"api_id": "api-anthropic-com", "url": "https://api.anthropic.com/v1/models"},
    {"api_id": "httpbin-get", "url": "https://httpbin.org/get"}
]

def generate_agent_key(agent_id: str) -> SigningKey:
    """
    Generate a deterministic Ed25519 keypair from the agent's ID.
    This ensures agents have consistent identities without needing DB migrations.
    """
    seed = hashlib.sha256(agent_id.encode('utf-8')).digest()
    return SigningKey(seed)

async def probe_endpoint(client: httpx.AsyncClient, api: dict) -> dict:
    """Raw network probe."""
    start_time = time.time()
    try:
        response = await client.get(api["url"], timeout=5.0)
        latency_ms = int((time.time() - start_time) * 1000)
        success = response.status_code < 500
        status_code = response.status_code
    except httpx.RequestError:
        latency_ms = int((time.time() - start_time) * 1000)
        success = False
        status_code = 0
        
    return {
        "api_id": api["api_id"],
        "latency_ms": latency_ms,
        "http_status_code": status_code,
        "success": success
    }

async def agent_evaluate_probe(agent: AgentIdentity, probe_data: dict) -> dict:
    """
    Uses Conversation Memory and Ollama to evaluate the probe result.
    """
    conv_id = f"vnp-probe-{agent.id}-{probe_data['api_id']}"
    workspace_id = agent.tenant_id
    
    # Load recent memory
    history = await ConversationMemory.get_history(workspace_id, conv_id)
    
    messages = [{"role": "system", "content": "You are a VNP Routing Agent. Analyze the API probe latency and status. If status is >=500 or 0, it's DOWN. Otherwise, it is UP. Reply only with a JSON object: {\"is_healthy\": true/false, \"reason\": \"...\"}"}]
    
    for h in history:
        messages.append({"role": h["role"], "content": h["content"]})
        
    prompt = f"Pinged {probe_data['api_id']}. Latency: {probe_data['latency_ms']}ms. Status: {probe_data['http_status_code']}. Are we healthy?"
    messages.append({"role": "user", "content": prompt})
    
    # Execute LLM via agent_ollama primitive
    try:
        response_text = await ollama_chat(messages)
    except Exception as e:
        log("AGENT", f"Ollama failed for {agent.id}: {e}")
        # Fallback heuristic if LLM fails
        return {"is_healthy": probe_data["success"]}
        
    # Save memory
    new_msgs = [
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": response_text}
    ]
    await ConversationMemory.add_messages(workspace_id, conv_id, new_msgs)
    
    # Parse LLM response
    is_healthy = probe_data["success"]
    try:
        clean = response_text.strip().strip('```json').strip('```').strip()
        data = json.loads(clean)
        if "is_healthy" in data:
            is_healthy = bool(data["is_healthy"])
    except json.JSONDecodeError:
        pass
        
    return {"is_healthy": is_healthy, "reason": response_text}

async def run_agent_probe(client: httpx.AsyncClient, agent: AgentIdentity, api: dict):
    # 1. Network Probe
    probe_data = await probe_endpoint(client, api)
    
    # 2. Cognitive Evaluation
    eval_data = await agent_evaluate_probe(agent, probe_data)
    
    # 3. Construct Canonical JSON and Cryptographic Signing
    region = agent.metadata_json.get("region", "local-enclave")
    
    event_payload = {
        "event_id": f"probe-{uuid.uuid4()}",
        "event_type": "probe",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "producer": {
            "worker_id": agent.id,
            "region": region,
            "runtime": "ollama"
        },
        "target": {
            "api_id": api["api_id"],
            "region_code": "unknown",
            "endpoint_url": api["url"]
        },
        "measurement": {
            "total_ms": probe_data["latency_ms"],
            "success": eval_data["is_healthy"],
            "status_code": probe_data["http_status_code"],
            "timeout": False,
            "error_class": None,
            "dns_ms": None,
            "connect_ms": None,
            "tls_ms": None,
            "ttfb_ms": None
        }
    }
    
    # Canonicalize using standard JSON deterministic encoding
    canonical_data = json.dumps(event_payload, separators=(',', ':'), sort_keys=True).encode('utf-8')
    
    signing_key = generate_agent_key(agent.id)
    import base64
    public_key_b64 = base64.b64encode(signing_key.verify_key.encode()).decode('utf-8')
    signature_bytes = signing_key.sign(canonical_data).signature
    sig_b64 = base64.b64encode(signature_bytes).decode('utf-8')
    
    event_payload["signature"] = {
        "alg": "Ed25519",
        "key_id": public_key_b64,
        "sig": sig_b64
    }
    
    batch = {
        "batch_id": str(uuid.uuid4()),
        "events": [event_payload]
    }
    
    # 4. Submit to Control Plane
    try:
        response = await client.post(
            INGESTION_URL,
            json=batch,
            timeout=5.0
        )
        if response.status_code == 201:
            log("VNP-FLEET", f"[{agent.id}] Successfully evaluated and ingested {api['api_id']} (Latency: {latency}ms, Healthy: {eval_data['is_healthy']})")
        else:
            log("VNP-FLEET", f"[{agent.id}] Ingest failed: HTTP {response.status_code} - {response.text}")
    except httpx.RequestError as e:
        log("VNP-FLEET", f"[{agent.id}] Ingest unreachable: {e}")

async def run_fleet_loop():
    print("🚀 Initializing VNP Agent Army Fleet Daemon...")
    
    async with async_session() as db:
        result = await db.execute(
            select(AgentIdentity).where(
                AgentIdentity.metadata_json.op('->>')('vnp_role') == 'prober_node'
            )
        )
        agents = result.scalars().all()
        
    if not agents:
        print("❌ No VNP Prober Agents found in PGL. Please run backend/scripts/register_vnp_fleet.py first.")
        return
        
    print(f"✅ Loaded {len(agents)} VNP Prober Agents from PGL.")
    
    # For testing and avoiding rate-limiting our local Ollama, we'll only run a subset
    # In production, this would be distributed across physical nodes
    active_squad = agents[:3]
    print(f"⚡ Deploying Squad Alpha (first {len(active_squad)} agents) for active probing...")
    
    async with httpx.AsyncClient() as client:
        while True:
            print(f"\n[{time.strftime('%H:%M:%S')}] Waking up squad for telemetry pass...")
            
            tasks = []
            for agent in active_squad:
                for api in TARGET_APIS:
                    tasks.append(run_agent_probe(client, agent, api))
                    
            await asyncio.gather(*tasks)
            
            print("💤 Telemetry pass complete. Squad resting for 30s...")
            await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(run_fleet_loop())
