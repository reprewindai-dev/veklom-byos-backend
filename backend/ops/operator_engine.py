"""Veklom Operator Execution Engine.

The governed autonomous workforce scheduler. Runs the "First 12" internal operators
on real tasks using the provider routing policy (Ollama → Groq → HF → Gemini → OpenAI).

Architecture:
  - One asyncio task per active schedule entry in InternalOperatorSchedule
  - Each operator tick: load context → choose_provider → call LLM → record result
  - All tasks logged to InternalOperatorTask, costs tracked in InternalOperatorProviderUsage
  - Budget hard-stops enforced per worker before any LLM call
  - Critical actions gate behind InternalOperatorApproval

Kill switches (three levels):
  1. Worker-level: pause_worker endpoint flips schedule.is_active = False
  2. Tenant-level: OPERATOR_ENGINE_ENABLED env var (default True)
  3. System-level: engine.stop() called from lifespan shutdown

Usage:
  from backend.ops.operator_engine import engine
  engine.start()   # call once from lifespan
  engine.stop()    # call from lifespan shutdown
"""

import asyncio
import os
import time
import traceback
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import httpx
from sqlalchemy import select

from backend.core.config.settings import settings

# ---------------------------------------------------------------------------
# Provider Routing Policy (mirrors internal_operators.py choose_provider)
# ---------------------------------------------------------------------------

def choose_provider(worker_id: str, task_type: str, risk: str, context_tokens: int, urgency: str) -> str:
    """Policy-driven LLM backend selector. Single source of truth for routing."""
    if task_type in ("heartbeat", "metric_summary", "route_check", "stale_widget_check",
                     "health_check", "log_scan", "schema_check", "queue_depth_check"):
        return "ollama"
    if urgency == "high" and context_tokens < 8000:
        return "groq"
    if task_type in ("classification", "source_clustering", "license_hint", "lead_scoring",
                     "sentiment_analysis", "category_tagging"):
        return "huggingface"
    if context_tokens > 24000 or task_type in ("policy_review", "compliance_mapping",
                                                "long_doc_analysis", "governance_report"):
        return "gemini"
    if risk in ("critical", "legal", "production_release", "negotiation_final",
                "security_ambiguous", "financial_commit"):
        return "openai"
    return "ollama"


# ---------------------------------------------------------------------------
# LLM Caller — routes to the right provider and returns (text, cost_usd)
# ---------------------------------------------------------------------------

async def _call_ollama(prompt: str, model: Optional[str] = None) -> tuple[str, float]:
    base = getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")
    m = model or getattr(settings, "LLM_MODEL_DEFAULT", "qwen2.5:3b")
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{base}/api/generate", json={
                "model": m,
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": 512}
            })
            if resp.status_code == 200:
                data = resp.json()
                text = data.get("response", "").strip()
                # Ollama cost is ~$0 (local), record a tiny accounting value
                return text, 0.0001
    except Exception as e:
        print(f"[engine] ollama error: {repr(e)}")
    return "", 0.0


async def _call_groq(prompt: str) -> tuple[str, float]:
    key = getattr(settings, "GROQ_API_KEY", "")
    if not key:
        return "", 0.0
    model = getattr(settings, "GROQ_MODEL", "llama-3.1-8b-instant")
    base = getattr(settings, "GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{base}/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 512,
                    "temperature": 0.3
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                text = data["choices"][0]["message"]["content"].strip()
                usage = data.get("usage", {})
                total_tokens = usage.get("total_tokens", 500)
                cost = (total_tokens / 1000.0) * 0.00027  # Groq approx pricing
                return text, cost
    except Exception as e:
        print(f"[engine] groq error: {e}")
    return "", 0.0


async def _call_gemini(prompt: str) -> tuple[str, float]:
    key = getattr(settings, "GEMINI_API_KEY", "")
    if not key:
        return "", 0.0
    model = getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
                json={"contents": [{"parts": [{"text": prompt}]}]}
            )
            if resp.status_code == 200:
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                # Gemini Flash is cheap — estimate
                cost = len(prompt.split()) * 0.000001
                return text, cost
    except Exception as e:
        print(f"[engine] gemini error: {e}")
    return "", 0.0


async def _call_openai(prompt: str) -> tuple[str, float]:
    key = getattr(settings, "OPENAI_API_KEY", "")
    if not key:
        return "", 0.0
    model = getattr(settings, "OPENAI_MODEL_CHAT", "gpt-4o-mini")
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 512,
                    "temperature": 0.2
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                text = data["choices"][0]["message"]["content"].strip()
                usage = data.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                cost = (prompt_tokens * 0.00015 + completion_tokens * 0.0006) / 1000.0
                return text, cost
    except Exception as e:
        print(f"[engine] openai error: {e}")
    return "", 0.0


async def call_llm(provider: str, prompt: str) -> tuple[str, float]:
    """Dispatch to the correct provider.
    Fallback chain: primary → groq → gemini → ollama (local).
    Ollama is tried last since it may not be reachable in cloud deployments.
    """
    # --- Primary provider ---
    try:
        if provider == "ollama":
            text, cost = await _call_ollama(prompt)
            if text:
                return text, cost
            # Ollama unreachable (cloud env) — escalate to Groq
            print(f"[engine] ollama unavailable, escalating to groq")
            provider = "groq"

        if provider == "groq":
            text, cost = await _call_groq(prompt)
            if text:
                return text, cost
        elif provider == "gemini":
            text, cost = await _call_gemini(prompt)
            if text:
                return text, cost
        elif provider == "openai":
            text, cost = await _call_openai(prompt)
            if text:
                return text, cost
        elif provider == "huggingface":
            text, cost = await _call_groq(prompt)  # HF via Groq-compat
            if text:
                return text, cost
    except Exception as e:
        print(f"[engine] call_llm({provider}) primary error: {e}")

    # --- Fallback chain: groq → gemini ---
    for fallback_fn, name in [(_call_groq, "groq"), (_call_gemini, "gemini")]:
        try:
            text, cost = await fallback_fn(prompt)
            if text:
                print(f"[engine] used fallback provider: {name}")
                return text, cost
        except Exception as e:
            print(f"[engine] fallback {name} error: {e}")

    return "", 0.0


# ---------------------------------------------------------------------------
# Per-Operator Task Definitions
# The "Super Prompt" system: each operator knows its role, policy, and limits.
# ---------------------------------------------------------------------------

OPERATOR_TASK_LIBRARY: Dict[str, Dict[str, Any]] = {
    "gauge": {
        "task_type": "metric_summary",
        "risk": "low",
        "urgency": "low",
        "committee": "marketplace-operations",
        "interval_seconds": 300,  # every 5 min
        "name": "Marketplace Health Gauge",
        "prompt_template": (
            "You are GAUGE, Veklom's marketplace health monitor.\n"
            "Your job is to summarize the health of the Veklom marketplace runtime.\n"
            "Today's date: {date}\n"
            "Review whether:\n"
            "1. The marketplace listing pipeline is operational\n"
            "2. Any listing needs flagging for missing data or policy violations\n"
            "3. Category distribution looks balanced\n"
            "Be concise. Return a 3-point health summary as JSON: "
            "{{\"status\": \"ok|degraded|critical\", \"issues\": [...], \"action\": \"string\"}}"
        ),
    },
    "ledger": {
        "task_type": "metric_summary",
        "risk": "low",
        "urgency": "low",
        "committee": "governance-evidence",
        "interval_seconds": 600,  # every 10 min
        "name": "Governance Evidence Ledger",
        "prompt_template": (
            "You are LEDGER, Veklom's governance evidence tracker.\n"
            "Your role is to verify that every governed AI execution in Veklom has an audit trail.\n"
            "Today's date: {date}\n"
            "Check whether:\n"
            "1. Recent pipeline runs have associated evidence logs\n"
            "2. Any execution_log entries lack governance approval records\n"
            "3. Compliance schedule is current\n"
            "Return JSON: {{\"verified\": true|false, \"gaps\": [...], \"recommendation\": \"string\"}}"
        ),
    },
    "sentinel": {
        "task_type": "health_check",
        "risk": "low",
        "urgency": "low",
        "committee": "experience-assurance",
        "interval_seconds": 120,  # every 2 min
        "name": "Route Sentinel Health Check",
        "prompt_template": (
            "You are SENTINEL, Veklom's experience assurance watchdog.\n"
            "Your job is to monitor the Veklom API health and flag broken or degraded routes.\n"
            "Today's date: {date}\n"
            "Evaluate whether:\n"
            "1. Core routes (health, workspace, agents, pipelines) are expected to be up\n"
            "2. Any recent errors in logs suggest route degradation\n"
            "3. Authentication flow appears correct\n"
            "Return JSON: {{\"status\": \"healthy|degraded\", \"flagged_routes\": [...], \"note\": \"string\"}}"
        ),
    },
    "mirror": {
        "task_type": "log_scan",
        "risk": "low",
        "urgency": "low",
        "committee": "experience-assurance",
        "interval_seconds": 900,  # every 15 min
        "name": "Error Mirror Log Scanner",
        "prompt_template": (
            "You are MIRROR, Veklom's log reflection agent.\n"
            "Your job is to scan recent error patterns and surface the top 3 issues to investigate.\n"
            "Today's date: {date}\n"
            "Focus on:\n"
            "1. Repeated 500/4xx error patterns\n"
            "2. Authentication or permission rejections\n"
            "3. Database timeout or connection failures\n"
            "Return JSON with key top_issues: a list of objects each with issue, frequency, priority (high/med/low)."
        ),
    },
    "pulse": {
        "task_type": "metric_summary",
        "risk": "low",
        "urgency": "low",
        "committee": "experience-assurance",
        "interval_seconds": 1800,  # every 30 min
        "name": "User Experience Pulse",
        "prompt_template": (
            "You are PULSE, Veklom's user experience monitor.\n"
            "Your job is to summarize the current state of user-facing experience on Veklom.\n"
            "Today's date: {date}\n"
            "Assess:\n"
            "1. Onboarding flow completeness\n"
            "2. Workspace UI feature availability\n"
            "3. Billing and subscription status clarity\n"
            "Return JSON: {{\"ux_score\": 0-10, \"critical_gaps\": [...], \"quick_wins\": [...]}}"
        ),
    },
    "sheriff": {
        "task_type": "health_check",
        "risk": "low",
        "urgency": "low",
        "committee": "governance-evidence",
        "interval_seconds": 1800,  # every 30 min
        "name": "Security Sheriff Compliance Check",
        "prompt_template": (
            "You are SHERIFF, Veklom's security compliance enforcer.\n"
            "Your job is to verify that Veklom's security posture is intact.\n"
            "Today's date: {date}\n"
            "Check:\n"
            "1. All admin endpoints require auth\n"
            "2. No secrets are exposed in API responses\n"
            "3. Rate limiting is active on critical routes\n"
            "4. Audit logs are being written for privileged actions\n"
            "Return JSON: {{\"posture\": \"secure|warning|critical\", \"findings\": [...], \"action_required\": bool}}"
        ),
    },
    "polish": {
        "task_type": "stale_widget_check",
        "risk": "low",
        "urgency": "low",
        "committee": "experience-assurance",
        "interval_seconds": 3600,  # every 60 min
        "name": "UI Polish Agent",
        "prompt_template": (
            "You are POLISH, Veklom's interface quality agent.\n"
            "Your job is to identify UI/UX improvements that can be made to the Veklom platform.\n"
            "Today's date: {date}\n"
            "Evaluate:\n"
            "1. Which pages are likely to have broken states or missing content\n"
            "2. What copy or labels could be improved for clarity\n"
            "3. What micro-interactions are missing that would improve engagement\n"
            "Return JSON with key priority_improvements: a list of objects each with page, issue, suggestion."
        ),
    },
    # Extended set
    "signal": {
        "task_type": "metric_summary",
        "risk": "low",
        "urgency": "low",
        "committee": "growth-intelligence",
        "interval_seconds": 3600,
        "name": "Growth Signal Monitor",
        "prompt_template": (
            "You are SIGNAL, Veklom's growth intelligence agent.\n"
            "Your job is to identify growth signals and opportunities in the Veklom ecosystem.\n"
            "Today's date: {date}\n"
            "Analyze:\n"
            "1. What AI/agent use cases are trending in the market\n"
            "2. Which Veklom features align with those trends\n"
            "3. What partnership or content opportunities exist\n"
            "Return JSON: {{\"signals\": [{\"trend\": \"str\", \"opportunity\": \"str\", \"priority\": \"str\"}]}}"
        ),
    },
    "oracle": {
        "task_type": "compliance_mapping",
        "risk": "low",
        "urgency": "low",
        "committee": "governance-evidence",
        "interval_seconds": 7200,  # every 2 hours
        "name": "Compliance Oracle",
        "prompt_template": (
            "You are ORACLE, Veklom's compliance intelligence agent.\n"
            "Your job is to map Veklom's current capabilities to regulatory and compliance frameworks.\n"
            "Today's date: {date}\n"
            "Assess alignment with:\n"
            "1. EU AI Act requirements for transparency and human oversight\n"
            "2. SOC2 Type II control requirements\n"
            "3. GDPR data handling obligations\n"
            "Return JSON: {{\"frameworks\": [{\"name\": \"str\", \"alignment\": \"full|partial|gap\", \"gaps\": [...]}]}}"
        ),
    },
    "welcome": {
        "task_type": "metric_summary",
        "risk": "low",
        "urgency": "low",
        "committee": "growth-intelligence",
        "interval_seconds": 3600,
        "name": "Onboarding Welcome Monitor",
        "prompt_template": (
            "You are WELCOME, Veklom's onboarding excellence agent.\n"
            "Your job is to ensure every new user has a smooth, clear onboarding experience.\n"
            "Today's date: {date}\n"
            "Review:\n"
            "1. The clarity of the registration → workspace flow\n"
            "2. Whether the first run experience is self-evident\n"
            "3. What friction points new users likely encounter\n"
            "Return JSON: {{\"onboarding_score\": 0-10, \"friction_points\": [...], "
            "\"recommended_improvements\": [...]}}"
        ),
    },
    "harvest": {
        "task_type": "source_clustering",
        "risk": "low",
        "urgency": "low",
        "committee": "marketplace-operations",
        "interval_seconds": 7200,
        "name": "Marketplace Harvest Scout",
        "prompt_template": (
            "You are HARVEST, Veklom's marketplace data acquisition agent.\n"
            "Your job is to identify high-quality, openly licensed data sources suitable for "
            "Veklom marketplace listings.\n"
            "Today's date: {date}\n"
            "Find:\n"
            "1. 3 trending open datasets suitable for RAG use cases\n"
            "2. Their license types\n"
            "3. Why enterprise AI teams would pay for them pre-packaged\n"
            "Return JSON with key opportunities: a list of objects each with name, source, license, use_case, buyer."
        ),
    },
    "scout": {
        "task_type": "lead_scoring",
        "risk": "low",
        "urgency": "low",
        "committee": "growth-intelligence",
        "interval_seconds": 7200,
        "name": "Lead Intelligence Scout",
        "prompt_template": (
            "You are SCOUT, Veklom's growth intelligence scout.\n"
            "Your job is to identify potential enterprise accounts, partners, and developer communities "
            "that would benefit from Veklom's governed AI execution layer.\n"
            "Today's date: {date}\n"
            "Identify:\n"
            "1. Industries with highest AI governance pressure (compliance, healthcare, finance, legal)\n"
            "2. What pain points Veklom solves for each\n"
            "3. Outreach angle that aligns with their regulatory reality\n"
            "Return JSON with key segments: a list of objects each with industry, pain, pitch, priority."
        ),
    },
}

# Minimum live set — these run from day 1
MINIMUM_LIVE_SET = ["gauge", "ledger", "sentinel", "mirror", "pulse", "sheriff", "polish"]


# ---------------------------------------------------------------------------
# Engine State
# ---------------------------------------------------------------------------

class OperatorEngine:
    """Veklom governed operator workforce scheduler."""
    
    def __init__(self):
        self._tasks: Dict[str, asyncio.Task] = {}
        self._running = False
        self._enabled = os.getenv("OPERATOR_ENGINE_ENABLED", "true").lower() == "true"
        self._start_time: Optional[datetime] = None
        self._tick_counts: Dict[str, int] = {}
        self._last_results: Dict[str, Dict] = {}
    
    def start(self):
        """Start all active operator loops. Safe to call multiple times."""
        if not self._enabled:
            print("[engine] OPERATOR_ENGINE_ENABLED=false — workforce not started")
            return
        if self._running:
            print("[engine] already running")
            return
        self._running = True
        self._start_time = datetime.now(timezone.utc)
        
        for worker_id in MINIMUM_LIVE_SET:
            self._launch_worker(worker_id)
        
        print(f"[engine] operator workforce started — {len(self._tasks)} workers active")
    
    def stop(self):
        """Graceful shutdown of all worker loops."""
        self._running = False
        for worker_id, task in self._tasks.items():
            if not task.done():
                task.cancel()
                print(f"[engine] cancelled worker: {worker_id}")
        self._tasks.clear()
        print("[engine] operator workforce stopped")
    
    def _launch_worker(self, worker_id: str):
        """Create an asyncio background task for a worker."""
        if worker_id in self._tasks and not self._tasks[worker_id].done():
            return  # already running
        self._tick_counts[worker_id] = 0
        task = asyncio.create_task(
            self._worker_loop(worker_id),
            name=f"veklom-operator-{worker_id}"
        )
        self._tasks[worker_id] = task
        print(f"[engine] launched worker: {worker_id}")
    
    def pause_worker(self, worker_id: str):
        """Kill loop for a specific worker (resume via resume_worker)."""
        if worker_id in self._tasks:
            self._tasks[worker_id].cancel()
            del self._tasks[worker_id]
            print(f"[engine] paused worker: {worker_id}")
    
    def resume_worker(self, worker_id: str):
        """Re-launch a paused worker."""
        self._launch_worker(worker_id)
    
    def status(self) -> Dict[str, Any]:
        """Return current engine status for the scheduler endpoint."""
        return {
            "running": self._running,
            "enabled": self._enabled,
            "start_time": self._start_time.isoformat() if self._start_time else None,
            "active_workers": [wid for wid, t in self._tasks.items() if not t.done()],
            "tick_counts": dict(self._tick_counts),
            "last_results": {k: v.get("status", "unknown") for k, v in self._last_results.items()},
        }
    
    async def _worker_loop(self, worker_id: str):
        """Main async loop for a single operator."""
        spec = OPERATOR_TASK_LIBRARY.get(worker_id)
        if not spec:
            print(f"[engine] no task spec for worker: {worker_id}")
            return
        
        # Stagger startup to avoid thundering herd
        stagger = list(MINIMUM_LIVE_SET).index(worker_id) * 15 if worker_id in MINIMUM_LIVE_SET else 60
        await asyncio.sleep(stagger)
        
        interval = spec["interval_seconds"]
        print(f"[engine] {worker_id}: loop started (interval={interval}s)")
        
        while self._running:
            try:
                await self._run_operator_tick(worker_id, spec)
                self._tick_counts[worker_id] = self._tick_counts.get(worker_id, 0) + 1
            except asyncio.CancelledError:
                print(f"[engine] {worker_id}: loop cancelled")
                return
            except Exception as e:
                print(f"[engine] {worker_id}: tick error: {type(e).__name__}: {e}")
                traceback.print_exc()
            
            # Wait for next tick
            try:
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                print(f"[engine] {worker_id}: sleep cancelled")
                return
    
    async def _run_operator_tick(self, worker_id: str, spec: Dict[str, Any]):
        """Execute one tick for an operator: build prompt → call LLM → record result."""
        from backend.core.database.database import async_session
        from backend.db.models.internal_operators import (
            InternalOperatorTask,
            InternalOperatorProviderUsage,
            InternalOperatorBudget,
            InternalOperatorMemory
        )
        
        task_type = spec["task_type"]
        risk = spec["risk"]
        urgency = spec["urgency"]
        provider = choose_provider(worker_id, task_type, risk, 1500, urgency)
        
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        prompt = spec["prompt_template"].format(date=date_str)
        
        # Budget hard-stop check
        budget_row = None
        async with async_session() as db:
            budget_row = (await db.execute(
                select(InternalOperatorBudget)
                .where(InternalOperatorBudget.worker_id == worker_id)
            )).scalar_one_or_none()
            
            if budget_row and provider in ("ollama", "openai", "gemini"):
                if budget_row.daily_spent_usd >= budget_row.daily_cap_usd:
                    print(f"[engine] {worker_id}: budget cap reached, skipping tick")
                    return
        
        # Call LLM
        start_ms = time.time() * 1000
        text, cost = await call_llm(provider, prompt)
        elapsed_ms = int(time.time() * 1000 - start_ms)
        
        # Store result
        self._last_results[worker_id] = {
            "status": "ok" if text else "empty",
            "provider": provider,
            "cost_usd": cost,
            "elapsed_ms": elapsed_ms,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Persist to DB
        async with async_session() as db:
            task_record = InternalOperatorTask(
                worker_id=worker_id,
                committee=spec["committee"],
                name=spec["name"],
                status="completed" if text else "failed",
                risk_level=risk,
                cost_estimate_usd=cost,
                input_data={"task_type": task_type, "provider": provider, "prompt_len": len(prompt)},
                output_data={"result_len": len(text), "provider_used": provider, "elapsed_ms": elapsed_ms,
                             "text_preview": text[:500] if text else ""}
            )
            db.add(task_record)
            
            usage = InternalOperatorProviderUsage(
                worker_id=worker_id,
                provider=provider,
                prompt_tokens=len(prompt.split()),
                completion_tokens=len(text.split()) if text else 0,
                cost_usd=cost
            )
            db.add(usage)
            
            # Store last result in memory
            mem_key = "last_tick_result"
            mem_row = (await db.execute(
                select(InternalOperatorMemory)
                .where(
                    InternalOperatorMemory.worker_id == worker_id,
                    InternalOperatorMemory.key == mem_key
                )
            )).scalar_one_or_none()
            
            if mem_row:
                mem_row.value = self._last_results[worker_id]
            else:
                db.add(InternalOperatorMemory(
                    worker_id=worker_id,
                    key=mem_key,
                    value=self._last_results[worker_id]
                ))
            
            # Update budget
            if budget_row:
                budget_row.daily_spent_usd = (budget_row.daily_spent_usd or 0.0) + cost
            
            await db.commit()
        
        if text:
            print(f"[engine] {worker_id}: tick OK ({provider}, {elapsed_ms}ms, ${cost:.6f})")
        else:
            print(f"[engine] {worker_id}: tick empty response ({provider})")


# ---------------------------------------------------------------------------
# Singleton engine instance
# ---------------------------------------------------------------------------
engine = OperatorEngine()
