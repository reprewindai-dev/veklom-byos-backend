"""add payment schema

Revision ID: e1f84351b689
Revises: e0e73231e786
Create Date: 2026-07-10 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e1f84351b689'
down_revision: Union[str, None] = 'e0e73231e786'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'payments',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('payment_object_type', sa.String(length=64), nullable=False),
        sa.Column('payment_object_id', sa.BigInteger(), nullable=False),
        sa.Column('from_address', sa.String(length=42), nullable=False),
        sa.Column('to_address', sa.String(length=42), nullable=False),
        sa.Column('asset', sa.String(length=16), nullable=False),
        sa.Column('amount', sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column('tx_hash', sa.String(length=66), nullable=True),
        sa.Column('chain_id', sa.BigInteger(), nullable=True),
        sa.Column('block_number', sa.BigInteger(), nullable=True),
        sa.Column('gas_used', sa.BigInteger(), nullable=True),
        sa.Column('settled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('payment_object_type', 'payment_object_id', name='uq_payment_object')
    )
    op.create_index('ix_payments_from_status', 'payments', ['from_address', 'status'], unique=False)
    op.create_index(op.f('ix_payments_tx_hash'), 'payments', ['tx_hash'], unique=False)
    
    op.drop_table('agent_wallet_ledger')

def downgrade() -> None:
    op.drop_index(op.f('ix_payments_tx_hash'), table_name='payments')
    op.drop_index('ix_payments_from_status', table_name='payments')
    op.drop_table('payments')
