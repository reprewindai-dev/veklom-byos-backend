import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from backend.core.config.settings import settings
from sqlalchemy import text

engine = create_async_engine(settings.DATABASE_URL)

async def run():
    async with engine.begin() as conn:
        await conn.execute(text(
            "ALTER TABLE exec_logs ADD COLUMN IF NOT EXISTS policy_id VARCHAR(128)"
        ))
        print("exec_logs.policy_id column ensured")

asyncio.run(run())
