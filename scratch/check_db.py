import asyncio
# Import all models to configure the mapper registry
import backend.db.models
from backend.db.models.plugin import WorkspacePlugin # Explicitly import to ensure relationship is loaded
from backend.core.database.database import async_session
from backend.db.models.internal_operators import InternalOperatorTask
from sqlalchemy import select, func

async def q():
    async with async_session() as db:
        cnt = await db.scalar(select(func.count(InternalOperatorTask.id)))
        print('Total DB operator task rows:', cnt)
        
        recent = await db.execute(
            select(InternalOperatorTask)
            .order_by(InternalOperatorTask.created_at.desc())
            .limit(10)
        )
        print('Recent tasks:')
        for t in recent.scalars():
            print(f"- Worker: {t.worker_id}, Status: {t.status}, Provider: {t.input_data.get('provider') if t.input_data else 'unknown'}, Cost: {t.cost_estimate_usd}, Created: {t.created_at}")

asyncio.run(q())
