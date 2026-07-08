"""Database engine and session management."""

from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from backend.core.config.settings import settings

db_url = settings.DATABASE_URL
if not db_url or not db_url.strip() or "sqlite" in db_url:
    raise ValueError("A valid PostgreSQL DATABASE_URL is required. SQLite is not supported due to pgvector/JSONB requirements.")

try:
    engine = create_async_engine(
        db_url,
        echo=settings.DEBUG,
        future=True,
        pool_size=20,
        max_overflow=15,
        pool_timeout=30,
        pool_pre_ping=True,
        pool_recycle=1800,
        connect_args={"timeout": 10, "command_timeout": 10},
    )
except Exception as e:
    print(f"WARNING: Database engine creation failed: {e}")
    raise e

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
print(f"DATABASE ENGINE INITIALIZED: ID={id(engine)}, URL={db_url}")


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_session():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_db_status():
    try:
        async with async_session() as session:
            await session.execute("SELECT 1" if "sqlite" not in settings.DATABASE_URL else __import__("sqlalchemy").text("SELECT 1"))
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
