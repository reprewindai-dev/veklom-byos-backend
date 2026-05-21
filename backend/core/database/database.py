"""Database engine and session management."""

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from backend.core.config.settings import settings

# Use SQLite by default for simplicity
engine = create_async_engine(
    "sqlite+aiosqlite:////tmp/veklom.db",
    echo=settings.DEBUG,
    future=True,
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    try:
        async with async_session() as session:
            try:
                yield session
            finally:
                await session.close()
    except Exception as e:
        import traceback
        error_detail = f"Database connection error: {str(e)}\nTraceback: {traceback.format_exc()}"
        print(error_detail)
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")


async def get_db_status():
    try:
        async with async_session() as session:
            await session.execute("SELECT 1" if "sqlite" not in settings.DATABASE_URL else __import__("sqlalchemy").text("SELECT 1"))
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
