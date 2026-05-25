import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from backend.core.config.settings import settings
from sqlalchemy import text

print("DATABASE_URL:", settings.DATABASE_URL)

engine = create_async_engine(settings.DATABASE_URL)

async def check():
    async with engine.begin() as conn:
        # All tables across all schemas
        r = await conn.execute(text(
            "SELECT schemaname, tablename FROM pg_tables "
            "WHERE schemaname NOT IN ('pg_catalog','information_schema') "
            "ORDER BY schemaname, tablename"
        ))
        rows = r.fetchall()
        print(f"Total tables in DB: {len(rows)}")
        for schema, table in rows:
            print(f"  {schema}.{table}")

        # Check what DB we're connected to
        r2 = await conn.execute(text("SELECT current_database(), current_schema()"))
        db, schema = r2.fetchone()
        print(f"\nConnected to DB: {db}, schema: {schema}")

asyncio.run(check())
