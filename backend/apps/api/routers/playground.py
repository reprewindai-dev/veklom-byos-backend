"""Playground routes — sessions, prompts, tools, response-format."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.db.models.playground import PlaygroundPrompt, PlaygroundSession

router = APIRouter(tags=["Playground"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _session_dict(s: PlaygroundSession) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "model": s.model,
        "mode": s.mode,
        "system_prompt": s.system_prompt,
        "messages": s.messages or [],
        "tools": s.tools or [],
        "response_format": s.response_format,
        "policy": s.policy,
        "tags": s.tags or [],
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


def _prompt_dict(p: PlaygroundPrompt) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "slug": p.slug or p.name,
        "version": p.version,
        "body": p.body,
        "system_prompt": p.system_prompt,
        "response_format": p.response_format,
        "policy": p.policy,
        "tools": p.tools or [],
        "tags": p.tags or [],
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


def _available_tools() -> list:
    return [
        {"id": "compliance.fetch", "name": "compliance.fetch", "status": "enabled", "description": "Fetch compliance regulations and control requirements", "schema": '{"type":"object","properties":{"regulation":{"type":"string"},"control_id":{"type":"string"}}}', "scope": "compliance:read", "mockable": True},
        {"id": "vault.read", "name": "vault.read", "status": "enabled", "description": "Read secrets from the Veklom sovereign vault", "schema": '{"type":"object","properties":{"key":{"type":"string"},"scope":{"type":"string"}}}', "scope": "vault:read", "mockable": True},
        {"id": "audit.log", "name": "audit.log", "status": "enabled", "description": "Write structured audit entries", "schema": '{"type":"object","properties":{"action":{"type":"string"},"resource":{"type":"string"}}}', "scope": "audit:write", "mockable": True},
        {"id": "rag.query", "name": "rag.query", "status": "enabled", "description": "Query the retrieval pipeline (pgvector / Qdrant / Weaviate)", "schema": '{"type":"object","properties":{"query":{"type":"string"},"index":{"type":"string"},"top_k":{"type":"integer"}}}', "scope": "retrieval:read", "mockable": True},
        {"id": "http.fetch", "name": "http.fetch", "status": "enabled", "description": "Make authenticated HTTP requests to external APIs", "schema": '{"type":"object","properties":{"url":{"type":"string"},"method":{"type":"string"}}}', "scope": "network:egress", "mockable": False},
        {"id": "code.execute", "name": "code.execute", "status": "disabled", "description": "Execute sandboxed Python code (requires elevated plan)", "schema": '{"type":"object","properties":{"code":{"type":"string"},"language":{"type":"string"}}}', "scope": "compute:execute", "mockable": False},
    ]


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------

@router.get("/playground/sessions")
async def list_sessions(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PlaygroundSession)
        .where(PlaygroundSession.workspace_id == (user.workspace_id or ""))
        .order_by(PlaygroundSession.updated_at.desc())
        .limit(50)
    )
    sessions = result.scalars().all()
    return [_session_dict(s) for s in sessions]


@router.post("/playground/sessions")
async def create_session(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    s = PlaygroundSession(
        user_id=user.id,
        workspace_id=user.workspace_id or "",
        name=body.get("name", "New Session"),
        model=body.get("model", ""),
        mode=body.get("mode", "chat"),
        system_prompt=body.get("system_prompt", ""),
        messages=body.get("messages", []),
        tools=body.get("tools", []),
        response_format=body.get("response_format", "text"),
        policy=body.get("policy", ""),
        tags=body.get("tags", []),
        created_at=now,
        updated_at=now,
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return _session_dict(s)


@router.get("/playground/sessions/{session_id}")
async def get_session(session_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PlaygroundSession).where(
            PlaygroundSession.id == session_id,
            PlaygroundSession.workspace_id == (user.workspace_id or ""),
        )
    )
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    return _session_dict(s)


@router.patch("/playground/sessions/{session_id}")
async def update_session(session_id: str, body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PlaygroundSession).where(
            PlaygroundSession.id == session_id,
            PlaygroundSession.workspace_id == (user.workspace_id or ""),
        )
    )
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    for field in ("name", "model", "mode", "system_prompt", "messages", "tools", "response_format", "policy", "tags"):
        if field in body:
            setattr(s, field, body[field])
    s.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return _session_dict(s)


@router.delete("/playground/sessions/{session_id}")
async def delete_session(session_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PlaygroundSession).where(
            PlaygroundSession.id == session_id,
            PlaygroundSession.workspace_id == (user.workspace_id or ""),
        )
    )
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    await db.delete(s)
    await db.commit()
    return {"deleted": True, "id": session_id}


@router.post("/playground/sessions/{session_id}/branch")
async def branch_session(session_id: str, body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PlaygroundSession).where(
            PlaygroundSession.id == session_id,
            PlaygroundSession.workspace_id == (user.workspace_id or ""),
        )
    )
    orig = result.scalar_one_or_none()
    if not orig:
        raise HTTPException(status_code=404, detail="Session not found")
    now = datetime.now(timezone.utc)
    branch = PlaygroundSession(
        user_id=user.id,
        workspace_id=user.workspace_id or "",
        name=body.get("name", f"{orig.name} (branch)"),
        model=orig.model,
        mode=orig.mode,
        system_prompt=orig.system_prompt,
        messages=list(orig.messages or []),
        tools=list(orig.tools or []),
        response_format=orig.response_format,
        policy=orig.policy,
        tags=list(orig.tags or []),
        created_at=now,
        updated_at=now,
    )
    db.add(branch)
    await db.commit()
    await db.refresh(branch)
    return _session_dict(branch)


@router.patch("/playground/sessions/{session_id}/tools")
async def update_session_tools(session_id: str, body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PlaygroundSession).where(
            PlaygroundSession.id == session_id,
            PlaygroundSession.workspace_id == (user.workspace_id or ""),
        )
    )
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    s.tools = body.get("tools", s.tools)
    s.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"id": session_id, "tools": s.tools}


@router.patch("/playground/sessions/{session_id}/response-format")
async def update_response_format(session_id: str, body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PlaygroundSession).where(
            PlaygroundSession.id == session_id,
            PlaygroundSession.workspace_id == (user.workspace_id or ""),
        )
    )
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    s.response_format = body.get("response_format", s.response_format)
    s.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"id": session_id, "response_format": s.response_format}


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

@router.get("/playground/prompts")
async def list_prompts(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PlaygroundPrompt)
        .where(PlaygroundPrompt.workspace_id == (user.workspace_id or ""))
        .order_by(PlaygroundPrompt.created_at.desc())
        .limit(100)
    )
    prompts = result.scalars().all()
    return [_prompt_dict(p) for p in prompts]


@router.post("/playground/prompts")
async def create_prompt(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    now = datetime.now(timezone.utc)
    p = PlaygroundPrompt(
        user_id=user.id,
        workspace_id=user.workspace_id or "",
        name=name,
        slug=body.get("slug", name.lower().replace(" ", ".")),
        version=body.get("version", "v1"),
        body=body.get("body", ""),
        system_prompt=body.get("system_prompt", ""),
        response_format=body.get("response_format", "text"),
        policy=body.get("policy", ""),
        tools=body.get("tools", []),
        tags=body.get("tags", []),
        created_at=now,
        updated_at=now,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return _prompt_dict(p)


@router.get("/playground/prompts/{prompt_id}")
async def get_prompt(prompt_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PlaygroundPrompt).where(
            PlaygroundPrompt.id == prompt_id,
            PlaygroundPrompt.workspace_id == (user.workspace_id or ""),
        )
    )
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return _prompt_dict(p)


@router.patch("/playground/prompts/{prompt_id}")
async def update_prompt(prompt_id: str, body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PlaygroundPrompt).where(
            PlaygroundPrompt.id == prompt_id,
            PlaygroundPrompt.workspace_id == (user.workspace_id or ""),
        )
    )
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Prompt not found")
    for field in ("name", "slug", "version", "body", "system_prompt", "response_format", "policy", "tools", "tags"):
        if field in body:
            setattr(p, field, body[field])
    p.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return _prompt_dict(p)


@router.delete("/playground/prompts/{prompt_id}")
async def delete_prompt(prompt_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PlaygroundPrompt).where(
            PlaygroundPrompt.id == prompt_id,
            PlaygroundPrompt.workspace_id == (user.workspace_id or ""),
        )
    )
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Prompt not found")
    await db.delete(p)
    await db.commit()
    return {"deleted": True, "id": prompt_id}


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@router.get("/playground/tools")
async def list_tools(user=Depends(get_current_user)):
    return {"tools": _available_tools(), "total": len(_available_tools())}


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------

@router.post("/playground/inference")
async def run_inference(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Execute inference using the session configuration."""
    session_id = body.get("session_id")
    message = body.get("message", "")
    
    if not message:
        raise HTTPException(status_code=400, detail="message is required")
    
    # If session_id provided, load session context
    session_context = {}
    if session_id:
        result = await db.execute(
            select(PlaygroundSession).where(
                PlaygroundSession.id == session_id,
                PlaygroundSession.workspace_id == (user.workspace_id or ""),
            )
        )
        s = result.scalar_one_or_none()
        if s:
            session_context = {
                "model": s.model,
                "system_prompt": s.system_prompt,
                "messages": s.messages or [],
                "tools": s.tools or [],
                "response_format": s.response_format,
            }
    
    # Call real AI completion
    from backend.apps.api.routers.ai import run_completion
    
    t0 = __import__("time").monotonic()
    result = await run_completion({
        "model": session_context.get("model", body.get("model", "qwen2.5:3b")),
        "messages": [{"role": "user", "content": message}],
        "system": session_context.get("system_prompt", ""),
    }, stream=False)
    latency_ms = int((__import__("time").monotonic() - t0) * 1000)
    
    data = result.payload
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    usage = data.get("usage", {})
    
    response = {
        "id": f"msg_{datetime.now(timezone.utc).timestamp()}",
        "role": "assistant",
        "content": content,
        "model": data.get("model", session_context.get("model", "unknown")),
        "provider": result.provider,
        "usage": {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
        },
        "finish_reason": "stop",
        "latency_ms": latency_ms,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    
    # If session provided, append messages to session
    if session_id and session_context:
        result = await db.execute(
            select(PlaygroundSession).where(
                PlaygroundSession.id == session_id,
                PlaygroundSession.workspace_id == (user.workspace_id or ""),
            )
        )
        s = result.scalar_one_or_none()
        if s:
            s.messages = s.messages or []
            s.messages.append({"role": "user", "content": message})
            s.messages.append({"role": "assistant", "content": response["content"]})
            s.updated_at = datetime.now(timezone.utc)
            await db.commit()
    
    return response
