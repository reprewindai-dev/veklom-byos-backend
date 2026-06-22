import re

with open("backend/apps/api/routers/monitoring.py", "r") as f:
    content = f.read()

# Add redis_cache import
if "from backend.core.services.redis_cache import redis_cache" not in content:
    content = content.replace(
        "from backend.core.database.database import get_db",
        "from backend.core.database.database import get_db\nfrom backend.core.services.redis_cache import redis_cache"
    )

# Patch platform_uptime
new_uptime_func = """
@router.get("/platform/uptime")
async def platform_uptime(db: AsyncSession = Depends(get_db)):
    \"\"\"Real platform status: live component health, incident-derived 90d history,
    real traffic. No simulated numbers. Where there is no historical probe store,
    the basis is stated explicitly rather than inventing a 99.99%.\"\"\"

    cached = await redis_cache.get("platform:uptime:metrics")
    if cached:
        return json.loads(cached)

    now = datetime.now(timezone.utc)
    components = await _component_health(db)
    history, active_incidents, uptime_pct = await _incident_history_90d(db)
    traffic = await _traffic_metrics(db, minutes=60)

    # 24h checks = execution_logs in the last 24h (the real governed-call volume).
    since_24h = now - timedelta(hours=24)
    checks_24h = (await db.scalar(
        select(func.count()).select_from(ExecutionLog).where(ExecutionLog.created_at >= since_24h)
    )) or 0

    unhealthy = any(c.get("status") == "unhealthy" for c in components.values())
    degraded = any(c.get("status") in ("degraded", "unknown") for c in components.values())
    overall = "down" if unhealthy else ("degraded" if degraded else "operational")
    headline = ("Service disruption detected" if unhealthy else
                "Operating with degraded components" if degraded else
                "All governed runtime systems operational")

    services = []
    for d in _SERVICE_DEFS:
        comp = components.get(d["component"], {})
        services.append({
            "service": d["service"], "slug": d["slug"], "region": d["region"], "symbol": d["symbol"],
            "description": d["description"],
            "status": _STATUS_MAP.get(comp.get("status", "unknown"), "degraded"),
            "response_time_ms": comp.get("latency_ms"),
            "uptime_90d": uptime_pct,
            "history_90d": history,
        })

    # Real incidents from incident_logs (most recent first).
    inc_rows = (await db.execute(
        select(IncidentLog).where(IncidentLog.created_at >= (now - timedelta(days=90)))
        .order_by(IncidentLog.created_at.desc()).limit(20)
    )).scalars().all()
    incidents = [{
        "date": i.created_at.date().isoformat() if i.created_at else None,
        "title": (i.message or "Incident")[:120],
        "status": "resolved" if i.resolved else "active",
        "severity": i.severity,
    } for i in inc_rows]

    result = {
        "overall_status": overall,
        "headline": headline,
        "updated_at": now.isoformat(),
        "window_days": 90,
        "uptime_percent": uptime_pct,
        "uptime_basis": "derived from incident_logs (no sub-day probe store); 100% = no recorded incident days",
        "process_uptime_seconds": int((now - _PROCESS_START_WALL).total_seconds()),
        "checks_passed_24h": int(checks_24h),
        "active_incidents": active_incidents,
        "avg_response_time_ms": traffic["avg_latency_ms"],
        "components": components,
        "services": services,
        "incidents": incidents,
    }

    await redis_cache.set("platform:uptime:metrics", json.dumps(result), ttl=300) # cache for 5 minutes

    return result
"""

# Replace the original platform_uptime
content = re.sub(
    r'@router\.get\("/platform/uptime"\)\nasync def platform_uptime\(.*?\n    return \{.*?\n    \}',
    new_uptime_func,
    content,
    flags=re.DOTALL
)

with open("backend/apps/api/routers/monitoring.py", "w") as f:
    f.write(content)
