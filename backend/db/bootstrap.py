"""Fail-closed bootstrap for a brand-new Veklom BYOS database.

This is intentionally separate from application startup. Runtime startup never
creates or alters schema. Existing databases continue to use ``alembic upgrade
head``. A brand-new database uses this one-time bootstrap to materialize the
canonical SQLAlchemy schema and stamp the current Alembic head, because the
legacy revision history begins after a pre-Alembic application schema already
existed and is therefore not a valid empty-database bootstrap path.

Safety properties:
* refuses any non-empty application schema;
* creates only on PostgreSQL;
* creates required schemas/extensions explicitly;
* verifies every table registered in Base.metadata exists after creation;
* stamps Alembic only after successful schema verification.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from backend.core.config.settings import settings
from backend.core.database.database import Base, engine

# Import all model modules so Base.metadata is complete before bootstrap.
import backend.db.models  # noqa: F401,E402


class BootstrapRefused(RuntimeError):
    """Raised when a database is not safe to bootstrap."""


_ALLOWED_PREEXISTING_TABLES = {"alembic_version"}
_APPLICATION_SCHEMAS = {"public", "mission_lock"}


def _alembic_config() -> Config:
    root = Path(__file__).resolve().parent
    return Config(str(root / "migrations" / "alembic.ini"))


def _verify_metadata_tables(sync_connection) -> None:
    inspector = inspect(sync_connection)
    missing: list[str] = []
    for table in Base.metadata.sorted_tables:
        schema = table.schema or "public"
        if not inspector.has_table(table.name, schema=schema):
            missing.append(f"{schema}.{table.name}")
    if missing:
        joined = ", ".join(sorted(missing))
        raise BootstrapRefused(f"Bootstrap verification failed; missing tables: {joined}")


async def _existing_application_tables() -> list[str]:
    query = text(
        """
        SELECT n.nspname AS schema_name, c.relname AS table_name
        FROM pg_class AS c
        JOIN pg_namespace AS n ON n.oid = c.relnamespace
        WHERE c.relkind IN ('r', 'p')
          AND n.nspname IN ('public', 'mission_lock')
        ORDER BY n.nspname, c.relname
        """
    )
    async with engine.connect() as connection:
        rows = (await connection.execute(query)).all()
    return [
        f"{row.schema_name}.{row.table_name}"
        for row in rows
        if row.table_name not in _ALLOWED_PREEXISTING_TABLES
    ]


async def bootstrap_fresh_database() -> None:
    if not settings.DATABASE_URL.startswith("postgresql"):
        raise BootstrapRefused("Fresh database bootstrap requires PostgreSQL")

    existing = await _existing_application_tables()
    if existing:
        preview = ", ".join(existing[:12])
        if len(existing) > 12:
            preview += f", ... (+{len(existing) - 12} more)"
        raise BootstrapRefused(
            "Refusing fresh bootstrap because application tables already exist: "
            f"{preview}. Existing databases must use 'alembic upgrade head'."
        )

    async with engine.begin() as connection:
        await connection.execute(text("CREATE SCHEMA IF NOT EXISTS mission_lock"))
        await connection.execute(text('CREATE EXTENSION IF NOT EXISTS "vector"'))
        await connection.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
        await connection.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        await connection.run_sync(Base.metadata.create_all, checkfirst=False)
        await connection.run_sync(_verify_metadata_tables)

    # Stamping happens only after the schema transaction commits and verification
    # succeeds. Alembic then owns all future schema transitions.
    await asyncio.to_thread(command.stamp, _alembic_config(), "head")


async def _main() -> None:
    await bootstrap_fresh_database()
    print("Fresh PostgreSQL schema bootstrapped and stamped at Alembic head.")


if __name__ == "__main__":
    asyncio.run(_main())
