import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.db.models.task_intake import TaskIntake

router = APIRouter(tags=["Tasks"])


class TaskIntakeRequest(BaseModel):
    email: str
    task: str
    round: int
    nonce: str
    secret: str
    brief: Optional[str] = None
    checks: Optional[List[Dict[str, Any]]] = None
    evaluation_url: Optional[str] = None


class TaskIntakeResponse(BaseModel):
    id: str
    status: str
    message: str


@router.post("/intake", response_model=TaskIntakeResponse)
async def submit_task(payload: TaskIntakeRequest, db: AsyncSession = Depends(get_db)):
    # 1. Require & verify secret
    expected_secret = os.getenv("TASK_INTAKE_SECRET", "default_secret")

    if payload.secret != expected_secret:
        # If per-tenant logic requires looking up the user's workspace secret, that would go here.
        # For now, strict enforcement of the expected secret.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid task secret"
        )

    # 2. Store nonce and reject replays.
    existing = await db.execute(
        select(TaskIntake).where(TaskIntake.nonce == payload.nonce)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Replay detected: nonce already used",
        )

    # 3. Store task
    new_task = TaskIntake(
        email=payload.email,
        task=payload.task,
        round=payload.round,
        nonce=payload.nonce,
        secret=payload.secret,
        brief=payload.brief,
        checks=payload.checks,
        evaluation_url=str(payload.evaluation_url) if payload.evaluation_url else None,
        status="PENDING",
    )
    db.add(new_task)
    await db.flush()
    await db.commit()

    return TaskIntakeResponse(
        id=new_task.id, status="success", message="Task received successfully"
    )
