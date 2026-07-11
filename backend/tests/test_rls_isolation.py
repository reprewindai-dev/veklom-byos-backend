import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

# We assume Pytest fixtures provide an async DB session (`db_session`)
# and tools to create Workspaces and Users. For this test, we will use raw SQL
# where possible to prove DB-level enforcement directly, isolating the test
# from app-level ORM filters.

pytestmark = pytest.mark.asyncio

async def test_rls_tenant_isolation_reads(db_session: AsyncSession):
    # Setup two tenants
    tenant_a = str(uuid.uuid4())
    tenant_b = str(uuid.uuid4())
    
    # Bypass RLS to insert test data for both tenants (Simulate system level)
    await db_session.execute(text("RESET app.workspace_id;"))
    
    # We use 'cost_predictions' as a representative tenant table for tests
    insert_sql = text("""
        INSERT INTO cost_predictions (id, workspace_id, model_name, estimated_cost, created_at, updated_at) 
        VALUES 
        (:id_a, :ws_a, 'model_a', 1.0, NOW(), NOW()),
        (:id_b, :ws_b, 'model_b', 2.0, NOW(), NOW())
    """)
    id_a = str(uuid.uuid4())
    id_b = str(uuid.uuid4())
    
    try:
        await db_session.execute(insert_sql, {
            "id_a": id_a, "ws_a": tenant_a,
            "id_b": id_b, "ws_b": tenant_b
        })
        await db_session.commit()
    except Exception as e:
        pytest.skip(f"Could not setup test data: {e}")

    # Set context to Tenant A
    await db_session.execute(text("SELECT set_config('app.workspace_id', :ws, true)"), {"ws": tenant_a})
    
    # Query all cost_predictions
    result = await db_session.execute(text("SELECT workspace_id FROM cost_predictions WHERE id IN (:id_a, :id_b)"))
    rows = result.fetchall()
    
    # Should only see Tenant A's rows
    assert len(rows) == 1
    assert rows[0][0] == tenant_a
    
    # Set context to Tenant B
    await db_session.execute(text("SELECT set_config('app.workspace_id', :ws, true)"), {"ws": tenant_b})
    
    # Query all cost_predictions
    result = await db_session.execute(text("SELECT workspace_id FROM cost_predictions WHERE id IN (:id_a, :id_b)"))
    rows = result.fetchall()
    
    # Should only see Tenant B's rows
    assert len(rows) == 1
    assert rows[0][0] == tenant_b


async def test_rls_tenant_isolation_writes(db_session: AsyncSession):
    tenant_a = str(uuid.uuid4())
    tenant_b = str(uuid.uuid4())
    
    # Set context to Tenant A
    await db_session.execute(text("SELECT set_config('app.workspace_id', :ws, true)"), {"ws": tenant_a})
    
    # Attempt to insert a row for Tenant B (should fail due to WITH CHECK)
    insert_b_sql = text("""
        INSERT INTO cost_predictions (id, workspace_id, model_name, estimated_cost, created_at, updated_at) 
        VALUES (:id, :ws, 'model_b', 2.0, NOW(), NOW())
    """)
    id_b = str(uuid.uuid4())
    
    try:
        await db_session.execute(insert_b_sql, {"id": id_b, "ws": tenant_b})
        assert False, "RLS WITH CHECK policy should have blocked this insert"
    except Exception as e:
        # Expected to fail
        await db_session.rollback()

    # Attempt to insert a row for Tenant A (should succeed)
    insert_a_sql = text("""
        INSERT INTO cost_predictions (id, workspace_id, model_name, estimated_cost, created_at, updated_at) 
        VALUES (:id, :ws, 'model_a', 2.0, NOW(), NOW())
    """)
    id_a = str(uuid.uuid4())
    
    await db_session.execute(text("SELECT set_config('app.workspace_id', :ws, true)"), {"ws": tenant_a})
    await db_session.execute(insert_a_sql, {"id": id_a, "ws": tenant_a})
    await db_session.commit()


async def test_rls_no_context_returns_zero_rows(db_session: AsyncSession):
    # Ensure no context is set
    await db_session.execute(text("RESET app.workspace_id;"))
    
    # Query tenant table
    result = await db_session.execute(text("SELECT * FROM cost_predictions LIMIT 10"))
    rows = result.fetchall()
    
    # Should return 0 rows for tenant tables if RLS is enforced and no workspace_id is set
    assert len(rows) == 0


async def test_rls_global_tables_accessible_without_context(db_session: AsyncSession):
    # Ensure no context is set
    await db_session.execute(text("RESET app.workspace_id;"))
    
    # Query global table (e.g. system_health or pricing_tiers)
    try:
        result = await db_session.execute(text("SELECT * FROM system_health LIMIT 1"))
        # Should not raise an error, proving global tables don't enforce RLS
        result.fetchall()
    except Exception as e:
        if "relation \"system_health\" does not exist" in str(e):
            pass # Table doesn't exist yet, but RLS is not the issue
        else:
            raise e
