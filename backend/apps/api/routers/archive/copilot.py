"""Copilot / AI assistant registry endpoints."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from backend.core.security.auth import get_current_user
from backend.core.ai.provider_router import run_completion, normalize_messages

router = APIRouter(prefix="/copilot", tags=["Copilot"])


@router.get("/registry")
async def copilot_registry(user=Depends(get_current_user)):
    return {
        "copilots": [
            {
                "id": "veklom-code-reviewer",
                "name": "Code Review Copilot",
                "description": "Reviews code for security, compliance, and policy violations",
                "model": "llama3.2:latest",
                "status": "active",
                "capabilities": ["code_review", "security_scan", "policy_check"],
            },
            {
                "id": "veklom-policy-advisor",
                "name": "Policy Advisor",
                "description": "Explains policy decisions and suggests compliant alternatives",
                "model": "llama3.2:latest",
                "status": "active",
                "capabilities": ["policy_explain", "compliance_advice"],
            },
            {
                "id": "veklom-proactive-assistant",
                "name": "Proactive Workspace Assistant",
                "description": "Proactively suggests actions, money-saving tips, and guides users through the workspace",
                "model": "llama3.2:latest",
                "status": "active",
                "capabilities": ["proactive_suggestions", "money_saving", "page_guidance", "reminders"],
            },
        ],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/recent-decisions")
async def copilot_recent_decisions(user=Depends(get_current_user)):
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    return {
        "decisions": [
            {
                "id": f"dec_{i:04d}",
                "action": action,
                "result": result,
                "policy": policy,
                "copilot_id": "veklom-policy-advisor",
                "ts": (now - timedelta(minutes=i * 7)).isoformat(),
            }
            for i, (action, result, policy) in enumerate([
                ("code_review", "approved", "passed"),
                ("inference_request", "executed", "passed"),
                ("pipeline_trigger", "blocked", "policy_violation"),
                ("evidence_export", "approved", "passed"),
                ("compliance_check", "approved", "passed"),
            ])
        ],
        "total": 5,
        "updated_at": now.isoformat(),
    }


@router.get("/registry/{copilot_id}")
async def get_copilot(copilot_id: str, user=Depends(get_current_user)):
    return {
        "id": copilot_id,
        "status": "active",
        "model": "llama3.2:latest",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/suggestions")
async def proactive_suggestions(body: dict, user=Depends(get_current_user)):
    """
    Proactive suggestions using Ollama for RAG-based guidance.
    
    Context-aware suggestions based on:
    - Current page/route
    - User activity
    - Workspace state
    - Money-saving opportunities
    """
    page = body.get("page", "overview")
    context = body.get("context", {})
    
    # Build context-aware prompt for Ollama
    page_guidance = {
        "overview": "You're on the Overview page. Suggest actions to improve operational efficiency, monitor spend, and optimize resource usage.",
        "playground": "You're on the Playground page. Suggest model choices, prompt optimizations, and cost-saving tips for AI inference.",
        "marketplace": "You're on the Marketplace page. Suggest relevant products based on workspace needs and compliance requirements.",
        "models": "You're on the Models page. Suggest model deployments, cost comparisons, and performance optimizations.",
        "pipelines": "You're on the Pipelines page. Suggest pipeline optimizations, automation opportunities, and monitoring improvements.",
        "deployments": "You're on the Deployments page. Suggest deployment strategies, scaling options, and cost optimizations.",
        "vault": "You're on the Vault page. Suggest security best practices, key rotation strategies, and access control improvements.",
        "compliance": "You're on the Compliance page. Suggest compliance frameworks, audit preparations, and policy improvements.",
        "monitoring": "You're on the Monitoring page. Suggest alert configurations, log analysis strategies, and performance tracking.",
        "billing": "You're on the Billing page. Suggest cost-saving strategies, budget optimizations, and spend analysis.",
        "team": "You're on the Team page. Suggest team management best practices, access control strategies, and onboarding improvements.",
        "settings": "You're on the Settings page. Suggest configuration optimizations, security settings, and workspace improvements.",
    }
    
    base_prompt = page_guidance.get(page, "You're in the Veklom workspace. Suggest helpful actions and improvements.")
    
    money_saving_context = """
Money-saving opportunities to consider:
- Use Ollama (local, free) instead of paid providers for routine tasks
- Set spend caps to prevent unexpected costs
- Use caching to reduce repeated inference calls
- Optimize prompt length to reduce token usage
- Batch similar requests together
- Review and remove unused deployments
- Use cost-optimized models for non-critical tasks
"""
    
    full_prompt = f"""{base_prompt}

{money_saving_context}

Provide 3-5 specific, actionable suggestions. Be concise and practical.
Format as a JSON array with objects having: "action", "benefit", "priority" (high/medium/low)."""
    
    try:
        result = await run_completion(
            {"messages": [{"role": "user", "content": full_prompt}], "model": "llama3.2:latest"},
            stream=False
        )
        
        content = result.payload.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        return {
            "page": page,
            "suggestions": content,
            "model": "llama3.2:latest",
            "provider": "ollama",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        # Fallback to static suggestions if Ollama fails
        fallback_suggestions = [
            {"action": "Review your spend cap settings", "benefit": "Prevent unexpected costs", "priority": "high"},
            {"action": "Use Ollama for routine inference tasks", "benefit": "Free local inference, no API costs", "priority": "high"},
            {"action": "Enable caching for repeated prompts", "benefit": "Reduce costs by up to 80%", "priority": "medium"},
            {"action": "Check marketplace for cost-saving tools", "benefit": "Find optimization products", "priority": "medium"},
        ]
        
        return {
            "page": page,
            "suggestions": fallback_suggestions,
            "model": "fallback",
            "provider": "static",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "note": "Ollama unavailable, using fallback suggestions",
        }


@router.get("/money-saving-tips")
async def money_saving_tips(user=Depends(get_current_user)):
    """Static money-saving tips that are always available."""
    return {
        "tips": [
            {
                "category": "Inference",
                "tip": "Use Ollama (llama3.2:latest) for all routine tasks - it's free and runs locally",
                "savings": "100% of inference costs for routine workloads",
                "priority": "high",
            },
            {
                "category": "Caching",
                "tip": "Enable hot/warm caching for repeated prompts - reduces API calls by up to 80%",
                "savings": "Up to 80% reduction in repeated inference costs",
                "priority": "high",
            },
            {
                "category": "Spend Caps",
                "tip": "Set daily and monthly spend caps to prevent unexpected bill spikes",
                "savings": "Prevents runaway costs, no unexpected bills",
                "priority": "high",
            },
            {
                "category": "Model Selection",
                "tip": "Use smaller models (llama3.2:latest) for simple tasks, reserve larger models only for complex reasoning",
                "savings": "Reduce per-call costs by 10-100x depending on task",
                "priority": "medium",
            },
            {
                "category": "Prompt Optimization",
                "tip": "Optimize prompt length and remove unnecessary context to reduce token usage",
                "savings": "Reduce costs by 20-50% through prompt efficiency",
                "priority": "medium",
            },
            {
                "category": "Deployments",
                "tip": "Review and remove unused deployments to avoid ongoing costs",
                "savings": "Eliminate waste from idle resources",
                "priority": "medium",
            },
            {
                "category": "Batching",
                "tip": "Batch similar inference requests together to improve efficiency",
                "savings": "Reduce overhead and improve throughput",
                "priority": "low",
            },
        ],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
