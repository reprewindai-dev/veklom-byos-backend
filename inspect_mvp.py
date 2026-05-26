import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from backend.core.config.settings import settings
from sqlalchemy import text

engine = create_async_engine(settings.DATABASE_URL)

async def check():
    async with engine.begin() as conn:
        # Get all columns for mvp schema tables
        r = await conn.execute(text("""
            SELECT c.table_name, c.column_name, c.data_type, c.column_default, c.is_nullable
            FROM information_schema.columns c
            WHERE c.table_schema = 'mvp'
            ORDER BY c.table_name, c.ordinal_position
        """))
        rows = r.fetchall()
        current_table = None
        for table, col, dtype, default, nullable in rows:
            if table != current_table:
                current_table = table
                print(f"\n--- mvp.{table} ---")
            print(f"  {col}: {dtype} {'(nullable)' if nullable == 'YES' else '(required)'}")

asyncio.run(check())
