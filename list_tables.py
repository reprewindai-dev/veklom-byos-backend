import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from backend.core.config.settings import settings
from sqlalchemy import text

engine = create_async_engine(settings.DATABASE_URL)

async def check():
    async with engine.begin() as conn:
        r = await conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"))
        tables = [row[0] for row in r.fetchall()]
        print(f"Total: {len(tables)}")
        for t in tables:
            print(t)

asyncio.run(check())
