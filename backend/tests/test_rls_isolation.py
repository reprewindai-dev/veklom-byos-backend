import uuid
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.core.database.database import Base, engine
from backend.db.models.ai import CostPrediction
from backend.db.models.monitoring import SystemHealth

pytestmark = pytest.mark.asyncio

RLS_TEST_ROLE = "ci_rls_test_app"
TEST_TABLES = (CostPrediction.__table__, SystemHealth.__table__)


async def _set_workspace(db_session: AsyncSession, workspace_id: str) -> None:
    await db_session.execute(
        text("SELECT set_config('app.workspace_id', :workspace_id, true)"),
        {"workspace_id": workspace_id},
    )


async def _seed_cost_predictions(*workspace_ids: str) -> None:
    """Insert test data with the database owner before switching to the app role."""
    rows = [
        {"id": str(uuid.uuid4()), "workspace_id": workspace_id}
        for workspace_id in workspace_ids
    ]
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                INSERT INTO cost_predictions (id, workspace_id, predicted_cost, created_at)
                VALUES (:id, :workspace_id, 1.0, NOW())
                """
            ),
            rows,
        )


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Prepare a minimal PostgreSQL schema and test through a non-superuser role."""
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(bind=sync_conn, tables=TEST_TABLES)
        )
        await conn.execute(text("TRUNCATE TABLE cost_predictions"))
        await conn.execute(text("ALTER TABLE cost_predictions ENABLE ROW LEVEL SECURITY"))
        await conn.execute(text("ALTER TABLE cost_predictions FORCE ROW LEVEL SECURITY"))
        await conn.execute(text("DROP POLICY IF EXISTS tenant_isolation_cost_predictions ON cost_predictions"))
        await conn.execute(
            text(
                """
                CREATE POLICY tenant_isolation_cost_predictions ON cost_predictions
                USING (workspace_id = current_setting('app.workspace_id', true))
                WITH CHECK (workspace_id = current_setting('app.workspace_id', true))
                """
            )
        )
        await conn.execute(
            text(
                f"""
                DO $$
                BEGIN
                    CREATE ROLE {RLS_TEST_ROLE} NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
                EXCEPTION
                    WHEN duplicate_object THEN NULL;
                END
                $$
                """
            )
        )
        await conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {RLS_TEST_ROLE}"))
        await conn.execute(text(f"GRANT SELECT, INSERT ON cost_predictions TO {RLS_TEST_ROLE}"))
        await conn.execute(text(f"GRANT SELECT ON system_health TO {RLS_TEST_ROLE}"))

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        await session.execute(text(f"SET ROLE {RLS_TEST_ROLE}"))
        await session.commit()
        assert await session.scalar(text("SELECT current_user")) == RLS_TEST_ROLE
        yield session
        await session.rollback()
        await session.execute(text("RESET ROLE"))


async def test_rls_tenant_isolation_reads(db_session: AsyncSession):
    tenant_a = str(uuid.uuid4())
    tenant_b = str(uuid.uuid4())
    await _seed_cost_predictions(tenant_a, tenant_b)

    await _set_workspace(db_session, tenant_a)
    result = await db_session.execute(text("SELECT workspace_id FROM cost_predictions"))
    assert {row[0] for row in result.fetchall()} == {tenant_a}

    await _set_workspace(db_session, tenant_b)
    result = await db_session.execute(text("SELECT workspace_id FROM cost_predictions"))
    assert {row[0] for row in result.fetchall()} == {tenant_b}


async def test_rls_tenant_isolation_writes(db_session: AsyncSession):
    tenant_a = str(uuid.uuid4())
    tenant_b = str(uuid.uuid4())

    await _set_workspace(db_session, tenant_a)
    with pytest.raises(DBAPIError):
        await db_session.execute(
            text(
                """
                INSERT INTO cost_predictions (id, workspace_id, predicted_cost, created_at)
                VALUES (:id, :workspace_id, 2.0, NOW())
                """
            ),
            {"id": str(uuid.uuid4()), "workspace_id": tenant_b},
        )
    await db_session.rollback()
    assert await db_session.scalar(text("SELECT current_user")) == RLS_TEST_ROLE

    await _set_workspace(db_session, tenant_a)
    await db_session.execute(
        text(
            """
            INSERT INTO cost_predictions (id, workspace_id, predicted_cost, created_at)
            VALUES (:id, :workspace_id, 1.0, NOW())
            """
        ),
        {"id": str(uuid.uuid4()), "workspace_id": tenant_a},
    )
    await db_session.commit()


async def test_rls_no_context_returns_zero_rows(db_session: AsyncSession):
    await _seed_cost_predictions(str(uuid.uuid4()))
    await db_session.execute(text("RESET app.workspace_id"))

    result = await db_session.execute(text("SELECT * FROM cost_predictions"))
    assert result.fetchall() == []


async def test_rls_global_tables_accessible_without_context(db_session: AsyncSession):
    await db_session.execute(text("RESET app.workspace_id"))
    result = await db_session.execute(text("SELECT * FROM system_health LIMIT 1"))
    result.fetchall()
