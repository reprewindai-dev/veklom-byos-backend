import asyncio
import threading
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, String
from sqlalchemy.pool import StaticPool

class Base(DeclarativeBase):
    pass

class TestTable(Base):
    __tablename__ = "test_table"
    id = Column(Integer, primary_key=True)
    name = Column(String)

db_url = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(
    db_url,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database setup complete. Created tables.")

def run_in_thread(loop):
    asyncio.set_event_loop(loop)
    loop.run_until_complete(query_db("Thread Loop"))

async def query_db(label):
    try:
        async with async_session() as session:
            from sqlalchemy import select
            res = await session.execute(select(TestTable))
            print(f"[{label}] Query succeeded! Rows: {res.scalars().all()}")
    except Exception as e:
        print(f"[{label}] Query failed: {type(e).__name__}: {e}")

async def main():
    await setup_db()
    await query_db("Main Loop")
    
    # Start thread with its own loop
    new_loop = asyncio.new_event_loop()
    t = threading.Thread(target=run_in_thread, args=(new_loop,))
    t.start()
    t.join()

if __name__ == "__main__":
    asyncio.run(main())
