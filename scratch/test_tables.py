import asyncio
from backend.core.database.database import engine, Base
from backend.db.models.provider import ProviderKey
from backend.db.models.user import User
from sqlalchemy import inspect

async def f():
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(
            bind=sync_conn,
            tables=[User.__table__, ProviderKey.__table__]
        ))
    async with engine.connect() as conn:
        tables = await conn.run_sync(lambda c: inspect(c).get_table_names())
        print("Created tables:", tables)

asyncio.run(f())
