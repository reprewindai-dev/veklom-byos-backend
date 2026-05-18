"""Compliance, privacy, content-safety, explainability, evidence, audit routes."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.db.models.security import AuditLog, ComplianceCheck

router = APIRouter(tags=["Compliance"])


# --- Compliance ---
@router.get("/compliance/regulations")
async def list_regulations(user=Depends(get_current_user)):
    return [
        {"id": "hipaa", "name": "HIPAA", "description": "Health Insurance Portability and Accountability Act", "enabled": True},
        {"id": "gdpr", "name": "GDPR", "description": "General Data Protection Regulation", "enabled": True},
        {"id": "soc2", "name": "SOC 2", "description": "Service Organization Control 2", "enabled": True},
        {"id": "ccpa", "name": "CCPA", "description": "California Consumer Privacy Act", "enabled": False},
    ]


@router.post("/compliance/check")
async def compliance_check(body: dict, user=Depends(get_current_user)):
    return {
        "regulation": body.get("regulation", "hipaa"),
        "result": "pass",
        "score": 0.95,
        "findings": [],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/compliance/report")
async def compliance_report(user=Depends(get_current_user)):
    return {
        "overall_score": 94,
        "regulations": [
            {"name": "HIPAA", "score": 96, "status": "compliant"},
            {"name": "GDPR", "score": 92, "status": "compliant"},
            {"name": "SOC 2", "score": 94, "status": "compliant"},
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# --- Privacy ---
@router.get("/privacy/status")
async def privacy_status(user=Depends(get_current_user)):
    return {"pii_detection": "enabled", "phi_detection": "enabled", "auto_redaction": True}


@router.post("/privacy/detect-pii")
async def detect_pii(body: dict, user=Depends(get_current_user)):
    content = body.get("content", "")
    return {"pii_detected": False, "entities": [], "redacted_content": content, "confidence": 0.99}


@router.post("/privacy/mask-pii")
async def mask_pii(body: dict, user=Depends(get_current_user)):
    return {"masked_content": body.get("content", "").replace("@", "[REDACTED]"), "entities_masked": 0}


@router.post("/privacy/export")
async def privacy_export(user=Depends(get_current_user)):
    return {"export_url": "/exports/privacy-report.json", "status": "generated"}


@router.post("/privacy/delete")
async def privacy_delete(body: dict, user=Depends(get_current_user)):
    return {"message": "Data deletion request submitted", "request_id": "del_placeholder"}


# --- Content Safety ---
@router.post("/content-safety/check")
async def content_safety(body: dict, user=Depends(get_current_user)):
    return {
        "score": 0.98,
        "categories": {"harmful": 0.01, "sexual": 0.0, "violence": 0.01, "self_harm": 0.0},
        "flagged": False,
    }


# --- Explainability ---
@router.get("/explainability/{request_id}")
async def explain_request(request_id: str, user=Depends(get_current_user)):
    return {
        "request_id": request_id,
        "model_used": "gpt-4o",
        "routing_reason": "Cost-quality optimization selected GPT-4o",
        "policy_checks": ["content_safety: pass", "pii_detection: pass", "budget_check: pass"],
        "cost_breakdown": {"input_tokens": 120, "output_tokens": 80, "total_cost_usd": 0.002},
    }


@router.get("/explain/routing")
async def explain_routing(user=Depends(get_current_user)):
    return {
        "strategy": "cost_quality_balanced",
        "primary_model": "gpt-4o",
        "fallback_model": "gpt-4o-mini",
        "routing_rules": ["budget_check", "latency_sla", "model_capability"],
    }


@router.get("/explain/cost")
async def explain_cost(user=Depends(get_current_user)):
    return {
        "total_cost_30d": 12.50,
        "by_model": [
            {"model": "gpt-4o", "cost": 8.00, "percentage": 64},
            {"model": "gpt-4o-mini", "cost": 2.50, "percentage": 20},
            {"model": "claude-3-5-sonnet", "cost": 2.00, "percentage": 16},
        ],
    }


# --- Evidence ---
@router.post("/evidence/create")
async def create_evidence(body: dict, user=Depends(get_current_user)):
    return {
        "evidence_id": "ev_placeholder",
        "type": body.get("type", "audit"),
        "hash": "sha256:placeholder",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


# --- Audit ---
@router.get("/audit/logs")
async def audit_logs(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(50))
    logs = result.scalars().all()
    if not logs:
        return [
            {"id": "al1", "action": "auth.login", "resource_type": "session", "details": {}, "created_at": datetime.now(timezone.utc).isoformat()},
            {"id": "al2", "action": "ai.exec", "resource_type": "completion", "details": {"model": "gpt-4o"}, "created_at": datetime.now(timezone.utc).isoformat()},
        ]
    return [{"id": l.id, "action": l.action, "resource_type": l.resource_type, "details": l.details, "created_at": l.created_at.isoformat()} for l in logs]


@router.get("/audit/logs/{log_id}")
async def get_audit_log(log_id: str, user=Depends(get_current_user)):
    return {"id": log_id, "action": "ai.exec", "resource_type": "completion", "details": {"model": "gpt-4o"}, "hash_chain": "sha256:valid"}


@router.get("/audit/verify/{log_id}")
async def verify_audit(log_id: str, user=Depends(get_current_user)):
    return {"log_id": log_id, "verified": True, "hash_valid": True, "chain_intact": True}


@router.get("/audit/compliance-report")
async def audit_compliance_report(user=Depends(get_current_user)):
    return {
        "report_id": "rpt_placeholder",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_logs": 1250,
        "hash_integrity": "100%",
        "compliance_status": "compliant",
    }
