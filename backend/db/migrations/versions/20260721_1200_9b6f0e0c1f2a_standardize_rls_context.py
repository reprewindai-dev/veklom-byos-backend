"""standardize RLS tenant context and remove bypass policies"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "9b6f0e0c1f2a"
down_revision: Union[str, None] = "cb82d08a68fe"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for table_name in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        if "workspace_id" not in columns:
            continue
        op.execute(f'ALTER TABLE "{table_name}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{table_name}" FORCE ROW LEVEL SECURITY')
        op.execute(f'DROP POLICY IF EXISTS tenant_isolation_policy ON "{table_name}"')
        op.execute(f'DROP POLICY IF EXISTS tenant_isolation ON "{table_name}"')
        op.execute(
            f'''CREATE POLICY tenant_isolation ON "{table_name}"
                AS PERMISSIVE FOR ALL
                USING (workspace_id::text = current_setting('app.workspace_id', true))
                WITH CHECK (workspace_id::text = current_setting('app.workspace_id', true))'''
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for table_name in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        if "workspace_id" in columns:
            op.execute(f'DROP POLICY IF EXISTS tenant_isolation ON "{table_name}"')
