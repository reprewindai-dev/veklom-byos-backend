"""Controlled smoke-test auth bootstrap routes."""

import hmac
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.apps.api.routers.auth import _get_or_create_eval_user
from backend.core.config.settings import settings
from backend.core.database.database import get_db
from backend.core.security.auth import create_access_token

router = APIRouter(prefix="/smoke", tags=["Smoke"])


@router.post("/eval-token")
async def smoke_eval_token(
    request: Request,
    body: dict = None,
    db: AsyncSession = Depends(get_db),
):
    if not settings.SMOKE_TEST_ENABLED:
        raise HTTPException(status_code=404, detail="Not found")

    configured_secret = (settings.SMOKE_TEST_SECRET or "").strip()
    if not configured_secret:
        raise HTTPException(status_code=403, detail="Forbidden")

    body = body or {}
    supplied_secret = (
        request.headers.get("x-smoke-test-secret")
        or request.headers.get("x-smoke-secret")
        or body.get("secret")
        or ""
    ).strip()
    if not supplied_secret or not hmac.compare_digest(supplied_secret, configured_secret):
        raise HTTPException(status_code=403, detail="Forbidden")

    fingerprint = (body.get("fingerprint") or "smoke-eval").strip()[:64]
    requested_role = (body.get("user_role") or "admin").strip().lower()
    if requested_role not in {"viewer", "user", "admin", "owner", "super_admin"}:
        requested_role = "admin"

    user = await _get_or_create_eval_user(db, fingerprint=f"smoke-{fingerprint}")
    if (user.role or "").lower() != requested_role:
        user.role = requested_role
        user.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(user)

    access_token = create_access_token(data={"sub": user.id})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "workspace_id": user.workspace_id,
        "user_role": user.role,
    }

