"""add pre_execution_cert_id to banker_payments

Revision ID: 20260810_1000_1234abcd5678
Revises: 25abacea7e65
Create Date: 2026-08-10 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '1234abcd5678'
down_revision: Union[str, None] = '25abacea7e65'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Add pre_execution_cert_id if not exists
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col['name'] for col in inspector.get_columns('banker_payments')]
    if 'pre_execution_cert_id' not in columns:
        op.add_column('banker_payments', sa.Column('pre_execution_cert_id', sa.String(length=255), nullable=True))

def downgrade() -> None:
    op.drop_column('banker_payments', 'pre_execution_cert_id')
