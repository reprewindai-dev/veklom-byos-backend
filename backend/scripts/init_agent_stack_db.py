import asyncio
from backend.core.database.database import engine
from backend.db.models.agent_stack import Base

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Agent stack tables created successfully!")

if __name__ == "__main__":
    asyncio.run(main())
