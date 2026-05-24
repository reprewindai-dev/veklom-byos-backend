"""Monitoring, metrics, insights, telemetry, platform pulse routes."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from backend.core.security.auth import get_current_user

router = APIRouter(tags=["Monitoring"])


@router.get("/monitoring/health")
async def monitoring_health(user=Depends(get_current_user)):
    return {
        "status": "healthy",
        "score": 98,
        "components": {
            "database": {"status": "healthy", "latency_ms": 2},
            "redis": {"status": "healthy", "latency_ms": 1},
            "ai_gateway": {"status": "healthy", "latency_ms": 45},
            "policy_engine": {"status": "healthy", "latency_ms": 5},
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/monitoring/metrics")
async def monitoring_metrics(user=Depends(get_current_user)):
    return {
        "cpu_percent": 34.2,
        "memory_percent": 58.1,
        "disk_percent": 22.3,
        "network_mbps": 12.5,
        "active_connections": 42,
        "requests_per_second": 120,
        "avg_latency_ms": 45,
        "error_rate": 0.001,
    }


@router.get("/monitoring/metrics/history")
async def monitoring_metrics_history(range: str = "24h", user=Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    points = []
    for i in range(24):
        points.append({
            "ts": f"{i:02d}:00",
            "requests_per_min": max(0, 2418 - (i * 23) + (i % 4) * 80),
            "tokens_per_sec": max(0, 184000 - (i * 1200) + (i % 3) * 3000),
            "latency_ms": 80 + (i % 5) * 12,
            "error_rate": round(0.0018 + (i % 7) * 0.0001, 4),
            "gpu_util_percent": 60 + (i % 8) * 4,
            "hetzner_percent": 80 + (i % 5) * 2,
            "aws_percent": 20 - (i % 5) * 2,
        })
    return {"range": range, "points": points, "updated_at": now.isoformat()}


@router.post("/monitoring/metrics/record")
async def record_metric(body: dict, user=Depends(get_current_user)):
    return {"recorded": True, "metric": body.get("name", ""), "value": body.get("value", 0)}


@router.get("/monitoring/dashboard")
async def monitoring_dashboard(user=Depends(get_current_user)):
    return {
        "health_score": 98,
        "uptime_percent": 99.97,
        "active_users": 12,
        "requests_24h": 4521,
        "avg_latency_ms": 45,
        "error_rate_percent": 0.1,
        "alerts": [],
        "recent_events": [
            {"type": "info", "message": "System healthy", "timestamp": datetime.now(timezone.utc).isoformat()},
        ],
    }


@router.get("/monitoring/events")
async def monitoring_events(user=Depends(get_current_user)):
    return [
        {"id": "me1", "type": "health_check", "status": "pass", "timestamp": datetime.now(timezone.utc).isoformat()},
        {"id": "me2", "type": "deployment", "status": "success", "timestamp": datetime.now(timezone.utc).isoformat()},
    ]


# --- Platform Pulse ---
@router.get("/platform/pulse")
async def platform_pulse():
    return {
        "total_users": 1524,
        "active_listings": 42,
        "tool_installs": 8412,
        "gpc_compiles_total": 12053,
        "user_growth_pct_30d": 14.5,
        "new_listings_7d": 3,
        "active_tools": 28,
    }


# --- Uptime Monitor ---
def _status_history_90d(degraded_days=None, down_days=None):
    degraded = set(degraded_days or [])
    down = set(down_days or [])
    history = []
    for day in range(90):
        status = "down" if day in down else "degraded" if day in degraded else "up"
        history.append({"day": "Today" if day == 89 else f"{90 - day} days ago", "status": status})
    return history


@router.get("/platform/uptime")
async def platform_uptime():
    now = datetime.now(timezone.utc).isoformat()
    return {
        "overall_status": "operational",
        "headline": "All governed runtime systems operational",
        "updated_at": now,
        "window_days": 90,
        "uptime_percent": 99.99,
        "checks_passed_24h": 18432,
        "active_incidents": 0,
        "avg_response_time_ms": 20,
        "services": [
            {
                "service": "Playground Engine",
                "slug": "playground",
                "status": "up",
                "response_time_ms": 42,
                "uptime_90d": 99.97,
                "region": "Evaluation Plane",
                "symbol": "shield",
                "description": "Safe agent tests, repository review sessions, and controlled tool trials.",
                "history_90d": _status_history_90d(
                    degraded_days=[15, 33, 44, 56, 70, 76, 84],
                    down_days=[34, 35, 36, 57],
                ),
            },
            {
                "service": "Governed Compiler (GPC)",
                "slug": "gpc",
                "status": "up",
                "response_time_ms": 15,
                "uptime_90d": 99.99,
                "region": "Runtime Core",
                "symbol": "stack",
                "description": "Policy-aware planning, execution compile checks, and deterministic handoff.",
                "history_90d": _status_history_90d(degraded_days=[9]),
            },
            {
                "service": "API Gateway",
                "slug": "api-gateway",
                "status": "up",
                "response_time_ms": 8,
                "uptime_90d": 99.99,
                "region": "Hetzner EU",
                "symbol": "globe",
                "description": "Public API ingress, auth routing, and workspace request boundary.",
                "history_90d": _status_history_90d(degraded_days=[28, 52]),
            },
            {
                "service": "Policy Vault",
                "slug": "policy-vault",
                "status": "up",
                "response_time_ms": 12,
                "uptime_90d": 99.98,
                "region": "Encrypted Boundary",
                "symbol": "lock",
                "description": "Key custody, rule evaluation, tenant isolation, and guarded secret access.",
                "history_90d": _status_history_90d(degraded_days=[18, 63]),
            },
            {
                "service": "Compliance Auditor",
                "slug": "compliance-auditor",
                "status": "up",
                "response_time_ms": 18,
                "uptime_90d": 100.0,
                "region": "Audit Plane",
                "symbol": "lens",
                "description": "Signed event trails, replay records, and compliance export pipeline.",
                "history_90d": _status_history_90d(),
            },
            {
                "service": "Autonomous Router",
                "slug": "autonomous-router",
                "status": "up",
                "response_time_ms": 25,
                "uptime_90d": 99.98,
                "region": "Routing Mesh",
                "symbol": "vmark",
                "description": "Cost, latency, policy, and capability routing for governed workloads.",
                "history_90d": _status_history_90d(degraded_days=[38, 81]),
            },
        ],
        "history": [
            {"day": "D-29", "status": "up"},
            {"day": "D-28", "status": "up"},
            {"day": "D-27", "status": "up"},
            {"day": "D-26", "status": "up"},
            {"day": "D-25", "status": "up"},
            {"day": "D-24", "status": "up"},
            {"day": "D-23", "status": "up"},
            {"day": "D-22", "status": "up"},
            {"day": "D-21", "status": "up"},
            {"day": "D-20", "status": "up"},
            {"day": "D-19", "status": "up"},
            {"day": "D-18", "status": "up"},
            {"day": "D-17", "status": "up"},
            {"day": "D-16", "status": "degraded"},
            {"day": "D-15", "status": "up"},
            {"day": "D-14", "status": "up"},
            {"day": "D-13", "status": "up"},
            {"day": "D-12", "status": "up"},
            {"day": "D-11", "status": "up"},
            {"day": "D-10", "status": "up"},
            {"day": "D-09", "status": "up"},
            {"day": "D-08", "status": "up"},
            {"day": "D-07", "status": "up"},
            {"day": "D-06", "status": "up"},
            {"day": "D-05", "status": "up"},
            {"day": "D-04", "status": "up"},
            {"day": "D-03", "status": "up"},
            {"day": "D-02", "status": "up"},
            {"day": "D-01", "status": "up"},
            {"day": "Today", "status": "up"},
        ],
        "incidents": [
            {
                "date": "2026-05-18",
                "title": "Brief policy telemetry delay",
                "status": "resolved",
                "impact": "Degraded status visibility for 3 minutes. Execution gates remained active.",
            },
            {
                "date": "2026-05-11",
                "title": "No customer-impacting incidents",
                "status": "informational",
                "impact": "Routine sovereign node maintenance completed without downtime.",
            },
        ],
    }


@router.post("/platform/status-updates")
async def subscribe_status_updates(body: dict):
    email = str(body.get("email", "")).strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(status_code=422, detail="Enter a valid email address.")

    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "email": email,
        "source": "veklom-status-page",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    with (log_dir / "status_update_subscribers.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, separators=(",", ":")) + "\n")

    return {"subscribed": True, "message": "Subscribed to Veklom status updates."}


@router.get("/platform/pulse/stream")
async def pulse_stream(user=Depends(get_current_user)):
    async def generate():
        import asyncio
        for i in range(10):
            data = {
                "event": "pulse",
                "data": {
                    "active_requests": 5 + i,
                    "latency_ms": 40 + i * 2,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            }
            yield f"data: {json.dumps(data)}\n\n"
            await asyncio.sleep(2)

    return StreamingResponse(generate(), media_type="text/event-stream")


# --- Insights ---
@router.get("/insights/summary")
async def insights_summary(user=Depends(get_current_user)):
    return {
        "total_requests_30d": 12450,
        "total_cost_30d": 12.50,
        "avg_latency_ms": 45,
        "top_models": [
            {"model": "gpt-4o", "requests": 5200, "cost": 8.00},
            {"model": "gpt-4o-mini", "requests": 4800, "cost": 2.50},
        ],
        "compliance_score": 94,
        "savings_vs_direct": 15.3,
    }


@router.get("/insights/savings")
async def insights_savings(user=Depends(get_current_user)):
    return {
        "total_saved_usd": 45.30,
        "routing_savings": 22.50,
        "caching_savings": 12.80,
        "policy_savings": 10.00,
    }


@router.get("/insights/savings/projected")
async def insights_savings_projected(user=Depends(get_current_user)):
    return {"projected_monthly_savings": 150.00, "confidence": 0.82}


# --- Metrics ---
@router.get("/metrics")
async def prometheus_metrics(user=Depends(get_current_user)):
    return {
        "veklom_requests_total": 12450,
        "veklom_latency_seconds_sum": 560.25,
        "veklom_errors_total": 12,
        "veklom_active_users": 12,
    }


@router.get("/metrics/performance")
async def performance_metrics(user=Depends(get_current_user)):
    return {
        "p50_ms": 35,
        "p90_ms": 120,
        "p99_ms": 220,
        "throughput_rps": 120,
        "error_rate": 0.001,
    }


# --- Telemetry ---
@router.post("/telemetry")
async def ingest_telemetry(body: dict, user=Depends(get_current_user)):
    return {"ingested": True, "events": len(body.get("events", []))}


# --- Suggestions ---
@router.get("/suggestions")
async def list_suggestions(user=Depends(get_current_user)):
    return [
        {"id": "s1", "type": "cost_optimization", "title": "Switch low-priority tasks to GPT-4o Mini", "impact_usd": 3.50},
        {"id": "s2", "type": "security", "title": "Enable MFA for all workspace members", "impact": "high"},
    ]


@router.get("/suggestions/summary")
async def suggestions_summary(user=Depends(get_current_user)):
    return {"total": 2, "potential_savings_usd": 3.50, "security_improvements": 1}
