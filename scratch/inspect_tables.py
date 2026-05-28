import asyncio
from backend.core.database.database import engine
from sqlalchemy import text

async def main():
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
        tables = sorted([r[0] for r in res.fetchall()])
        print("\n=== Database Tables ===")
        for t in tables:
            print(f"- {t}")
        print("=======================\n")

if __name__ == "__main__":
    asyncio.run(main())
