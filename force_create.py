"""Force create all Veklom tables in the public schema."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from backend.core.config.settings import settings
from backend.core.database.database import Base
from sqlalchemy import text, inspect

# Register ALL models
import backend.db.models  # noqa: F401

async def run():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    
    print(f"Connected to: {settings.DATABASE_URL.split('@')[1]}")
    print(f"Tables registered in Base.metadata: {sorted(Base.metadata.tables.keys())}\n")

    async with engine.begin() as conn:
        # Get existing public tables
        r = await conn.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
        ))
        existing = {row[0] for row in r.fetchall()}
        print(f"Existing public tables ({len(existing)}): {sorted(existing)}\n")

        # Create all (skips existing)
        await conn.run_sync(Base.metadata.create_all)
        print("create_all ran.\n")

        # Verify after
        r2 = await conn.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
        ))
        after = {row[0] for row in r2.fetchall()}
        new_tables = after - existing
        print(f"New tables created ({len(new_tables)}): {sorted(new_tables)}")
        
        veklom_core = ['users','sessions','api_keys','workspaces','workspace_members',
                       'model_configs','exec_logs','audit_logs','security_events',
                       'pipelines','deployments','marketplace_listings','agents','agent_skills']
        print("\nVeklom core table status:")
        for t in veklom_core:
            status = "EXISTS" if t in after else "MISSING"
            print(f"  {t}: {status}")

    await engine.dispose()

asyncio.run(run())
