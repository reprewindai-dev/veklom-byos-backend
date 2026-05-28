"""Add payment and webhook tables

Revision ID: 001_add_payment_tables
Revises: 
Create Date: 2026-05-28

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_add_payment_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create payments table
    op.create_table(
        'payments',
        sa.Column('order_id', sa.String(64), primary_key=True, nullable=False),
        sa.Column('user_hash', sa.String(64), nullable=False, index=True),
        sa.Column('user_id', sa.String(36), nullable=False, index=True),
        sa.Column('workspace_id', sa.String(36), default='', index=True),
        sa.Column('expected_amount', sa.Float, nullable=False),
        sa.Column('token_contract', sa.String(64), nullable=False),
        sa.Column('chain_id', sa.Integer, nullable=False),
        sa.Column('status', sa.String(32), default='pending'),
        sa.Column('tx_hash', sa.String(128), nullable=True),
        sa.Column('confirmations', sa.Integer, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()')),
    )
    
    # Create orders table
    op.create_table(
        'orders',
        sa.Column('order_id', sa.String(64), primary_key=True, nullable=False, unique=True),
        sa.Column('amount', sa.Float, nullable=False),
        sa.Column('currency', sa.String(16), default='USD'),
        sa.Column('user_id', sa.String(36), nullable=False, index=True),
        sa.Column('workspace_id', sa.String(36), default='', index=True),
        sa.Column('status', sa.String(32), default='pending'),
        sa.Column('tx_hash', sa.String(128), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()')),
    )
    
    # Create ledger table
    op.create_table(
        'ledger',
        sa.Column('id', sa.String(36), primary_key=True, nullable=False),
        sa.Column('tx_hash', sa.String(128), nullable=True, index=True),
        sa.Column('order_id', sa.String(64), nullable=False, index=True),
        sa.Column('amount', sa.Float, nullable=False),
        sa.Column('direction', sa.String(32), nullable=False),
        sa.Column('note', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    
    # Create webhook_receipts table
    op.create_table(
        'webhook_receipts',
        sa.Column('idempotency_key', sa.String(128), primary_key=True, nullable=False),
        sa.Column('body_sha256', sa.String(64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    
    # Create recon_findings table
    op.create_table(
        'recon_findings',
        sa.Column('tx_hash', sa.String(128), primary_key=True, nullable=False),
        sa.Column('ledger_sum', sa.Float, nullable=False),
        sa.Column('chain_sum', sa.Float, nullable=False),
        sa.Column('detected_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )


def downgrade() -> None:
    op.drop_table('recon_findings')
    op.drop_table('webhook_receipts')
    op.drop_table('ledger')
    op.drop_table('orders')
    op.drop_table('payments')
