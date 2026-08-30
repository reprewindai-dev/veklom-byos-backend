"""Merge multiple heads

Revision ID: 2c4090ba99cb
Revises: 003_add_index_created_at_exec_logs, e0e73231e786
Create Date: 2026-06-23 18:03:06.566155

"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = '2c4090ba99cb'
down_revision: Union[str, None] = ('003_add_index_created_at_exec_logs', 'e0e73231e786')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
