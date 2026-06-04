from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.billing import Subscription
from backend.db.models.workspace import Workspace

async def get_workspace_plan(db: AsyncSession, workspace_id: str) -> str:
    subscription = await db.scalar(
        select(Subscription)
        .where(
            Subscription.workspace_id == workspace_id,
            Subscription.status.in_(["active", "trialing"])
        )
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )

    if subscription:
        return subscription.plan

    workspace = await db.scalar(
        select(Workspace).where(Workspace.id == workspace_id)
    )

    if workspace and workspace.license_tier:
        return workspace.license_tier

    return "free"
