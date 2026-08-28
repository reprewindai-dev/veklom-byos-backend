"""Database engine and session management."""

from contextlib import asynccontextmanager
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from backend.core.config.settings import settings

db_url = settings.DATABASE_URL


def _mask_database_url(url: str) -> str:
    try:
        parts = urlsplit(url)
        if not parts.password:
            return url
        username = parts.username or ""
        host = parts.hostname or ""
        port = f":{parts.port}" if parts.port else ""
        auth = f"{username}:***@" if username else "***@"
        return urlunsplit((parts.scheme, f"{auth}{host}{port}", parts.path, parts.query, parts.fragment))
    except Exception:
        return "<masked>"
if settings.APP_ENV != "test" and (not db_url or not db_url.strip() or "sqlite" in db_url):
    raise ValueError(
        "A valid PostgreSQL DATABASE_URL is required. SQLite is not supported due to pgvector/JSONB requirements."
    )

try:
    connect_args = {}
    if "sqlite" in db_url:
        connect_args = {"timeout": 3}
    else:
        connect_args = {"timeout": 3, "command_timeout": 5}

    engine_options = {
        "echo": settings.DEBUG,
        "future": True,
        "connect_args": connect_args,
    }
    if settings.APP_ENV == "test":
        # asyncpg connections are tied to their event loop; pytest creates several.
        engine_options["poolclass"] = NullPool
    else:
        engine_options.update(
            pool_size=5,
            max_overflow=10,
            pool_timeout=10,
            pool_pre_ping=True,
            pool_recycle=1800,
        )
    engine = create_async_engine(db_url, **engine_options)
except Exception as e:
    print(f"WARNING: Database engine creation failed: {e}")
    raise e

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
print(f"DATABASE ENGINE INITIALIZED: ID={id(engine)}, URL={_mask_database_url(db_url)}")


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


async def set_tenant_session(db: AsyncSession, workspace_id: str) -> None:
    """
    Sets the current Postgres session variable for RLS enforcement.
    Uses SELECT set_config(..., true) so it is local to the current transaction.
    """
    await db.execute(
        text("SELECT set_config('app.workspace_id', :workspace_id, true)"),
        {"workspace_id": str(workspace_id)},
    )


async def reset_tenant_session(db: AsyncSession) -> None:
    """Clear the request-scoped PostgreSQL RLS workspace context."""
    await db.execute(text("RESET app.workspace_id"))


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
            await session.execute(text("SELECT 1"))
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
