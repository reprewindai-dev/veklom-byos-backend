import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from backend.core.config.settings import settings
from sqlalchemy import text

engine = create_async_engine(settings.DATABASE_URL)

async def check():
    async with engine.begin() as conn:
        r = await conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"))
        tables = [row[0] for row in r.fetchall()]
        veklom = ['users','exec_logs','workspaces','audit_logs','agents','pipelines','deployments','sessions','api_keys','marketplace_listings','budget_rules']
        found = [t for t in tables if t in veklom]
        print('Veklom tables found:', found)
        print('Total tables:', len(tables))

asyncio.run(check())
