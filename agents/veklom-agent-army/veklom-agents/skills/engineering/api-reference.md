# API Reference Quick Guide

## All 43 Router Files
backend/apps/api/routers/:
auth.py, workspace.py, ai_execution.py, billing.py, subscriptions.py,
marketplace_v1.py, pipelines.py, compliance.py, audit.py, security.py,
kill_switch.py, locker.py, routing.py, autonomous.py, monitoring.py,
telemetry.py, insights.py, deployments.py, edge.py, admin.py,
webhooks.py, demo.py, support_bot.py, herald.py, ...

## Standard Endpoint Pattern
```python
from fastapi import APIRouter, Depends, HTTPException
from backend.core.auth import get_current_user
from backend.db.models import User
from backend.db.session import get_db

router = APIRouter(prefix="/api/v1", tags=["your-tag"])

@router.get("/your-endpoint", summary="What it does")
async def your_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Implementation
    return {"result": "data"}
```

## Register in main.py
```python
from backend.apps.api.routers import your_router
app.include_router(your_router.router)
```

## Standard Error Format
```python
raise HTTPException(
    status_code=400,
    detail={"error": "human message", "code": "ERROR_CODE"}
)
```

## Pagination Standard
```python
# All list endpoints must support:
@router.get("/items")
async def list_items(page: int = 1, page_size: int = 20):
    offset = (page - 1) * page_size
    return {"items": [...], "total": N, "page": page, "page_size": page_size}
```
