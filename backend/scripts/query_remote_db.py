import asyncio
from backend.core.database.database import async_session
from sqlalchemy import text

async def main():
    async with async_session() as session:
        result = await session.execute(text("SELECT count(*) FROM execution_logs"))
        print("TOTAL RUNS LOGS:", result.scalar())
        
        result2 = await session.execute(text("SELECT count(*) FROM safety_incidents"))
        print("TOTAL SAFETY INCIDENTS:", result2.scalar())

if __name__ == "__main__":
    asyncio.run(main())
