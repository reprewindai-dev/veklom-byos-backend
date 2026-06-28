from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
import time
import asyncio
from datetime import datetime
import random

router = APIRouter(prefix="/locks", tags=["locks"])

# --- In-Memory State ---
server_logs: List[Dict[str, Any]] = []
server_history: List[Dict[str, Any]] = []
server_active_locks: Dict[str, Dict[str, Any]] = {}

cumulative_acquires = 0
cumulative_successes = 0
cumulative_failures = 0
cumulative_expirations = 0

KEYSPACE_POOL = [
    'lock:user_auth:9021',
    'lock:payment_charge:115',
    'lock:inventory_sku_993',
    'lock:order_checkout:583',
    'lock:db_backup_worker',
    'lock:report_generator_v2',
    'lock:stripe_webhook_771',
    'lock:cache_warmup_leader'
]

# --- Seed State ---
def seed_state():
    global cumulative_acquires, cumulative_successes, cumulative_failures, cumulative_expirations
    now_ms = int(time.time() * 1000)
    for i in range(29, -1, -1):
        tick_time = datetime.fromtimestamp((now_ms - i * 1500) / 1000.0)
        time_label = tick_time.strftime("%H:%M:%S")
        
        successes = int(2 + random.random() * 5)
        failures = int(random.random() * 2)
        total_requests = successes + failures
        
        cumulative_acquires += total_requests
        cumulative_successes += successes
        cumulative_failures += failures

        server_history.append({
            "timeLabel": time_label,
            "successes": successes,
            "failures": failures,
            "avgLatency": round(0.8 + random.random() * 0.9, 2),
            "minLatency": round(0.3 + random.random() * 0.2, 2),
            "maxLatency": round(1.8 + random.random() * 1.5, 2),
            "totalRequests": total_requests,
            "p95Latency": round(1.5 + random.random() * 1.2, 2)
        })

    mock_keys = [
        'lock:user_auth:9021',
        'lock:payment_charge:115',
        'lock:inventory_sku_993'
    ]
    for index, key in enumerate(mock_keys):
        duration = 12000 + index * 4000
        server_active_locks[key] = {
            "key": key,
            "clientId": f"client:tx_env_{index + 1}a",
            "expiresAt": now_ms + duration,
            "durationMax": duration,
            "acquiredAt": now_ms - (duration * 0.2),
            "leaseHistory": [{"timestamp": now_ms - (duration * 0.2), "type": "acquire"}]
        }

    sys_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    server_logs.append({
        "id": "sys-0",
        "timestamp": sys_time,
        "type": "system",
        "operation": "SYSTEM",
        "key": "cluster",
        "message": "Unified Ingest API Receiver online. Ready to accept external telemetry logs at /api/locks/logs"
    })
    
    for idx, (k, l) in enumerate(server_active_locks.items()):
        l_time = datetime.fromtimestamp(l["acquiredAt"] / 1000.0).strftime("%H:%M:%S.%f")[:-3]
        server_logs.append({
            "id": f"sys-lock-seed-{idx}",
            "timestamp": l_time,
            "type": "success",
            "operation": "EVALSHA",
            "key": l["key"],
            "latency": 1.12,
            "message": f"Database Lock acquired externally for resource '{l['key']}'. Owner client: '{l['clientId']}', TTL: {l['durationMax']}ms"
        })

seed_state()

# --- Background Task ---
async def eviction_loop():
    global cumulative_expirations
    while True:
        await asyncio.sleep(0.5)
        now = int(time.time() * 1000)
        keys_to_delete = []
        for key, lock in server_active_locks.items():
            if now >= lock["expiresAt"]:
                keys_to_delete.append(key)
                
        for key in keys_to_delete:
            cumulative_expirations += 1
            del server_active_locks[key]
            server_logs.append({
                "id": f"sys-expiry-{now}-{key}",
                "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3],
                "type": "expired",
                "operation": "EXPIRED",
                "key": key,
                "message": f"Lease expired naturally. Lock target '{key}' released automatically on Redis cluster."
            })
            if len(server_logs) > 300:
                server_logs.pop(0)

# The loop must be started in main.py startup event or similar
eviction_task = None
def start_eviction_loop():
    global eviction_task
    if eviction_task is None:
        eviction_task = asyncio.create_task(eviction_loop())

# --- Models ---
class LogIngest(BaseModel):
    id: Optional[str] = None
    timestamp: Optional[str] = None
    type: Optional[str] = "success"
    key: Optional[str] = "lock:generic_res"
    latency: Optional[Union[float, str]] = 1.0
    operation: Optional[str] = "EVALSHA"
    message: Optional[str] = None
    clientId: Optional[str] = None
    client: Optional[str] = None
    duration: Optional[int] = None
    ttl: Optional[int] = None

# --- Endpoints ---

@router.get("/logs")
async def get_logs():
    # Start loop lazily if not started
    start_eviction_loop()
    
    return {
        "status": "ok",
        "logs": server_logs,
        "history": server_history,
        "activeLocks": server_active_locks,
        "stats": {
            "cumulativeAcquires": cumulative_acquires,
            "cumulativeSuccesses": cumulative_successes,
            "cumulativeFailures": cumulative_failures,
            "cumulativeExpirations": cumulative_expirations,
            "runningTicks": len(server_history)
        }
    }

@router.post("/logs")
async def post_logs(request: Request):
    global cumulative_acquires, cumulative_successes, cumulative_failures, cumulative_expirations
    start_eviction_loop()
    
    body = await request.json()
    if not body:
        raise HTTPException(status_code=400, detail="Missing telemetry request payload")

    events = body if isinstance(body, list) else [body]
    right_now = datetime.now()
    timestamp_str = right_now.strftime("%H:%M:%S.%f")[:-3]
    time_label_str = right_now.strftime("%H:%M:%S")
    now_ms = int(time.time() * 1000)

    for evt_raw in events:
        evt = LogIngest(**evt_raw) if isinstance(evt_raw, dict) else evt_raw
        lock_type = evt.type or "success"
        key_str = evt.key or "lock:generic_res"
        
        try:
            latency_num = float(evt.latency) if evt.latency is not None else 1.0
        except:
            latency_num = 1.0
            
        operation_str = evt.operation or "EVALSHA"
        message_str = evt.message or f"{lock_type.upper()} - Key '{key_str}' accessed."
        client_id_str = evt.clientId or evt.client or f"client:tx_{random.randint(1000, 9999)}"
        
        try:
            duration_num = int(evt.duration) if evt.duration is not None else (int(evt.ttl) if evt.ttl is not None else 10000)
        except:
            duration_num = 10000

        log_item = {
            "id": evt.id or f"ingest-{now_ms}-{random.randint(1000, 9999)}",
            "timestamp": evt.timestamp or timestamp_str,
            "type": lock_type,
            "message": message_str,
            "latency": latency_num,
            "operation": operation_str,
            "key": key_str
        }

        cumulative_acquires += 1
        if lock_type == "success":
            cumulative_successes += 1
            server_active_locks[key_str] = {
                "key": key_str,
                "clientId": client_id_str,
                "acquiredAt": now_ms,
                "expiresAt": now_ms + duration_num,
                "durationMax": duration_num,
                "leaseHistory": [{"timestamp": now_ms, "type": "acquire"}]
            }
        elif lock_type == "failed":
            cumulative_failures += 1
        elif lock_type == "expired":
            cumulative_expirations += 1
            if key_str in server_active_locks:
                del server_active_locks[key_str]
        elif operation_str == "DEL" or lock_type in ["released", "release"]:
            if key_str in server_active_locks:
                del server_active_locks[key_str]

        server_logs.append(log_item)
        if len(server_logs) > 300:
            server_logs.pop(0)

        # Update timeseries tick map
        active_tick = next((t for t in server_history if t["timeLabel"] == time_label_str), None)
        if not active_tick:
            active_tick = {
                "timeLabel": time_label_str,
                "successes": 0,
                "failures": 0,
                "avgLatency": latency_num,
                "minLatency": latency_num,
                "maxLatency": latency_num,
                "totalRequests": 0,
                "p95Latency": latency_num
            }
            server_history.append(active_tick)
            if len(server_history) > 40:
                server_history.pop(0)

        active_tick["totalRequests"] += 1
        if lock_type == "success":
            active_tick["successes"] += 1
        if lock_type == "failed":
            active_tick["failures"] += 1

        current_total = active_tick["totalRequests"]
        if current_total == 1:
            active_tick["avgLatency"] = latency_num
            active_tick["minLatency"] = latency_num
            active_tick["maxLatency"] = latency_num
            active_tick["p95Latency"] = latency_num
        else:
            active_tick["avgLatency"] = round((active_tick["avgLatency"] * (current_total - 1) + latency_num) / current_total, 2)
            active_tick["minLatency"] = round(min(active_tick["minLatency"], latency_num), 2)
            active_tick["maxLatency"] = round(max(active_tick["maxLatency"], latency_num), 2)
            active_tick["p95Latency"] = round(active_tick["avgLatency"] * 1.35 + (latency_num - active_tick["avgLatency"] if latency_num > active_tick["avgLatency"] else 0), 2)

    return {
        "status": "success",
        "ingestedCount": len(events),
        "cumulativeAcquires": cumulative_acquires
    }

@router.delete("/lock/{key}")
async def delete_lock(key: str):
    start_eviction_loop()
    if key in server_active_locks:
        owner_token = server_active_locks[key]["clientId"]
        del server_active_locks[key]
        
        server_logs.append({
            "id": f"manual-release-{int(time.time() * 1000)}",
            "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3],
            "type": "expired",
            "operation": "DEL",
            "key": key,
            "message": f"FORCE EVICTED - Lock key '{key}' purged manually. Released owner client token: '{owner_token}'"
        })
        return {"status": "success", "message": f"Locked target {key} released."}
    else:
        raise HTTPException(status_code=404, detail="Lock key not currently leased.")

@router.delete("/logs")
async def clear_logs():
    global cumulative_acquires, cumulative_successes, cumulative_failures, cumulative_expirations
    global server_logs, server_history, server_active_locks
    
    server_logs.clear()
    server_logs.append({
        "id": f"flush-{int(time.time() * 1000)}",
        "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3],
        "type": "system",
        "operation": "FLUSHALL",
        "key": "global",
        "message": "Server telemetry buffer was cleared manually via dashboard control."
    })
    server_history.clear()
    server_active_locks.clear()
    cumulative_acquires = 0
    cumulative_successes = 0
    cumulative_failures = 0
    cumulative_expirations = 0
    
    return {"status": "cleared"}
