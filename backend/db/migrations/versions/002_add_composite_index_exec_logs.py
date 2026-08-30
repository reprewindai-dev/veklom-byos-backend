"""Add composite index for execution logs

Revision ID: 002_add_composite_index_exec_logs
Revises: 001_add_payment_tables
Create Date: 2024-05-24 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '002_add_composite_index_exec_logs'
down_revision: Union[str, None] = '001_add_payment_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        'ix_exec_logs_workspace_provider',
        'execution_logs',
        ['workspace_id', 'provider'],
        unique=False
    )

def downgrade() -> None:
    op.drop_index('ix_exec_logs_workspace_provider', table_name='execution_logs')
