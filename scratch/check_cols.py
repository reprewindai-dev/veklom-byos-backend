import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from backend.core.config.settings import settings

engine = create_async_engine(settings.DATABASE_URL)

async def check():
    async with engine.begin() as conn:
        r = await conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='execution_logs'"))
        print([row[0] for row in r.fetchall()])

if __name__ == "__main__":
    asyncio.run(check())
