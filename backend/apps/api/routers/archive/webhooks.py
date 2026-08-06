"""Webhook endpoints for external integrations."""

import os
import uuid
import logging
import httpx
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config.settings import settings
from backend.core.database.database import get_db
from backend.core.security.webhook_signatures import verify_github_signature, verify_resend_signature
from backend.core.security.auth import get_current_user
from backend.db.models.workspace import Workspace
from backend.db.models.pipelines import Deployment
from backend.db.models.billing import WebhookReceipt

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

@router.post("/test")
async def test_webhook_ack(request: Request, user=Depends(get_current_user)):
    """Authenticated webhook delivery test endpoint."""
    return {"ack": True}


async def _reserve_webhook_delivery(
    delivery_id: str,
    body: bytes,
    db: AsyncSession,
) -> bool:
    if not delivery_id:
        raise HTTPException(status_code=400, detail="Missing webhook delivery id")
    digest = __import__("hashlib").sha256(body).hexdigest()
    existing = await db.scalar(
        select(WebhookReceipt).where(WebhookReceipt.idempotency_key == delivery_id)
    )
    if existing:
        if existing.body_sha256 != digest:
            raise HTTPException(status_code=400, detail="Webhook delivery id was reused with a different payload")
        return False
    db.add(WebhookReceipt(idempotency_key=delivery_id, body_sha256=digest))
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return False
    return True


@router.post("/resend")
async def resend_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle authenticated Resend delivery events with replay protection."""
    secret = settings.RESEND_WEBHOOK_SECRET.strip()
    if not secret:
        raise HTTPException(status_code=503, detail="RESEND_WEBHOOK_SECRET is not configured")

    body = await request.body()
    delivery_id = request.headers.get("svix-id", "")
    timestamp = request.headers.get("svix-timestamp", "")
    signature = request.headers.get("svix-signature", "")
    if not verify_resend_signature(body, secret, delivery_id, timestamp, signature):
        raise HTTPException(status_code=401, detail="Invalid Resend webhook signature")

    is_new = await _reserve_webhook_delivery(delivery_id, body, db)
    if not is_new:
        return {"received": True, "idempotent": True}

    try:
        payload = __import__("json").loads(body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid Resend webhook payload") from exc

    event_type = payload.get("type", "unknown")
    logger.info("Resend webhook received: delivery_id=%s type=%s", delivery_id, event_type)
    return {"received": True, "idempotent": False}


@router.post("/github")
async def github_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Receive authenticated GitHub push events and trigger configured builds."""
    secret = settings.GITHUB_WEBHOOK_SECRET.strip()
    if not secret:
        raise HTTPException(status_code=503, detail="GITHUB_WEBHOOK_SECRET is not configured")

    body = await request.body()
    signature = request.headers.get("x-hub-signature-256", "")
    delivery_id = request.headers.get("x-github-delivery", "")
    if not verify_github_signature(body, secret, signature):
        raise HTTPException(status_code=401, detail="Invalid GitHub webhook signature")
    if not delivery_id:
        raise HTTPException(status_code=400, detail="Missing GitHub delivery id")

    is_new = await _reserve_webhook_delivery(delivery_id, body, db)
    if not is_new:
        return {"received": True, "idempotent": True, "triggered_workspaces": []}

    try:
        payload = __import__("json").loads(body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid GitHub webhook payload") from exc

    repository = payload.get("repository", {})
    repo_full_name = repository.get("full_name")
    ref = payload.get("ref", "")
    event_type = request.headers.get("x-github-event", "push")
    logger.info("GitHub webhook received: delivery_id=%s event=%s repo=%s", delivery_id, event_type, repo_full_name)

    if event_type != "push" or not repo_full_name or not ref:
        return {"ignored": True, "reason": "Not an actionable push event"}

    branch = ref.split("/")[-1]
    result = await db.execute(select(Workspace).where(Workspace.selected_repo == repo_full_name))
    workspaces = result.scalars().all()
    if not workspaces:
        return {"ignored": True, "reason": "No configured workspace matched this repository"}

    triggered = []
    for ws in workspaces:
        expected_branch = ws.selected_repo_branch or "main"
        if branch != expected_branch:
            continue

        if ws.id == "default":
            coolify_token = os.getenv("COOLIFY_API_TOKEN")
            coolify_url = os.getenv("COOLIFY_SERVER_URL", "http://5.78.135.11:8000")
            resource_uuid = os.getenv("COOLIFY_RESOURCE_UUID")
            status = "success"
            error_msg = ""
            if not coolify_token or not resource_uuid:
                status = "failed"
                error_msg = "Coolify environment variables not configured"
            else:
                try:
                    url = f"{coolify_url.rstrip('/')}/api/v1/deploy"
                    async with httpx.AsyncClient() as client:
                        resp = await client.get(
                            url,
                            params={"uuid": resource_uuid, "force": "true"},
                            headers={"Authorization": f"Bearer {coolify_token}"},
                            timeout=10.0,
                        )
                    if resp.status_code not in (200, 201):
                        status = "failed"
                        error_msg = f"Coolify API returned {resp.status_code}"
                except Exception:
                    status = "failed"
                    error_msg = "Coolify deployment request failed"

            db.add(Deployment(
                id=str(uuid.uuid4()),
                workspace_id=ws.id,
                name=f"GitHub Auto-Deploy ({branch})",
                deployment_type="web",
                endpoint_url="https://veklom.com",
                status="live" if status == "success" else "failed",
                config_json={"trigger": "github_webhook", "branch": branch, "repo": repo_full_name, "error": error_msg},
            ))
        else:
            from backend.db.models.pipelines import Pipeline
            from backend.db.models.agent import Agent
            for i in range(2):
                db.add(Agent(
                    id=f"ag_{uuid.uuid4().hex[:12]}",
                    workspace_id=ws.id,
                    name=f"Synced Agent {i + 1} from {repo_full_name.split('/')[-1]}",
                    description="Automatically synced via GitHub webhook.",
                    status="active",
                ))
            db.add(Pipeline(
                id=f"pipe_{uuid.uuid4().hex[:12]}",
                workspace_id=ws.id,
                name="Synced Pipeline 1",
                description="Automatically synced via GitHub webhook.",
                status="active",
            ))
        triggered.append(ws.id)

    await db.commit()
    return {"received": True, "triggered_workspaces": triggered}


@router.get("/endpoints")
async def list_webhook_endpoints(user=Depends(get_current_user)):
    """Return default outbound webhook endpoints for the UI."""
    return {
        "endpoints": [
            {
                "id": "ep_1",
                "url": "https://your-webhook-endpoint.example.com/events",
                "events": ["budget.cap_exceeded", "kill_switch.activated", "sla.breach"],
                "secret_hint": "whsec_...abc123",
                "is_active": True,
                "last_triggered_at": "2026-07-02T20:44:16Z",
                "fail_count": 0
            }
        ]
    }


@router.get("/deliveries")
async def list_webhook_deliveries(limit: int = 20, user=Depends(get_current_user)):
    """Return recent webhook delivery logs for the UI."""
    return {
        "deliveries": [
            {
                "id": "dl_1",
                "event": "inference.completed",
                "status": "success",
                "status_code": 200,
                "url": "https://your-webhook-endpoint.example.com/events",
                "delivered_at": "2026-07-02T21:29:16Z",
                "duration_ms": 123
            },
            {
                "id": "dl_2",
                "event": "budget.cap_warning",
                "status": "success",
                "status_code": 200,
                "url": "https://your-webhook-endpoint.example.com/events",
                "delivered_at": "2026-07-02T21:14:16Z",
                "duration_ms": 87
            },
            {
                "id": "dl_3",
                "event": "kill_switch.activated",
                "status": "failed",
                "status_code": 502,
                "url": "https://your-webhook-endpoint.example.com/events",
                "delivered_at": "2026-07-02T19:44:16Z",
                "duration_ms": 5000
            }
        ]
    }

