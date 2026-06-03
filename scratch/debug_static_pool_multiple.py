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
    print("Database setup complete.")

async def first_request():
    async with async_session() as session:
        t = TestTable(id=1, name="first")
        session.add(t)
        await session.commit()
    print("First request complete (committed & session closed).")

def run_in_thread(loop, label):
    asyncio.set_event_loop(loop)
    loop.run_until_complete(query_db(label))

async def query_db(label):
    try:
        async with async_session() as session:
            from sqlalchemy import select
            res = await session.execute(select(TestTable))
            print(f"[{label}] Query succeeded! Rows: {[r.name for r in res.scalars().all()]}")
    except Exception as e:
        print(f"[{label}] Query failed: {type(e).__name__}: {e}")

async def main():
    await setup_db()
    
    # Thread 1 does first request (insert & commit)
    loop1 = asyncio.new_event_loop()
    t1 = threading.Thread(target=lambda: loop1.run_until_complete(first_request()))
    t1.start()
    t1.join()

    # Thread 2 does query
    loop2 = asyncio.new_event_loop()
    t2 = threading.Thread(target=run_in_thread, args=(loop2, "Request 2 Thread"))
    t2.start()
    t2.join()

    # Thread 3 does query
    loop3 = asyncio.new_event_loop()
    t3 = threading.Thread(target=run_in_thread, args=(loop3, "Request 3 Thread"))
    t3.start()
    t3.join()

if __name__ == "__main__":
    asyncio.run(main())
