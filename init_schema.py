"""Initialize all database tables for Veklom."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from backend.core.config.settings import settings
from backend.core.database.database import Base

# Import ALL models to register them with Base.metadata
import backend.db.models  # noqa: F401

async def init_schema():
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        before = set(Base.metadata.tables.keys())
        print(f"[init] Tables registered in metadata: {len(before)}")
        for t in sorted(before):
            print(f"  - {t}")
        await conn.run_sync(Base.metadata.create_all)
        print("[init] create_all completed")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(init_schema())
