"""add_training_locked_at

Revision ID: fef856c068bf
Revises: 11aafac941ba
Create Date: 2026-08-24 23:22:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'fef856c068bf'
down_revision = '11aafac941ba'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Add missing column
    op.add_column('execution_logs', sa.Column('training_locked_at', postgresql.TIMESTAMP(timezone=True), nullable=True))
    
    # 2. Add missing indices
    op.create_index('idx_exec_log_dedupe_key', 'execution_logs', ['dedupe_key'], unique=False)
    op.create_index('idx_exec_log_gold_training', 'execution_logs', ['workspace_id', 'data_tier', 'eligible_for_training', 'training_locked_at', 'created_at'], unique=False)
    op.create_index('idx_exec_log_tier_created_at', 'execution_logs', ['data_tier', 'created_at'], unique=False)
    op.create_index('idx_exec_log_ws_tier_created', 'execution_logs', ['workspace_id', 'data_tier', 'created_at'], unique=False)
    op.create_index('ix_execution_logs_data_tier', 'execution_logs', ['workspace_id', 'data_tier'], unique=False)
    op.create_index('ix_execution_logs_evidence_pack_id', 'execution_logs', ['evidence_pack_id'], unique=False)
    op.create_index('ix_execution_logs_route_family', 'execution_logs', ['route_family'], unique=False)
    op.create_index('ix_exec_logs_workspace_provider', 'execution_logs', ['workspace_id', 'provider'], unique=False)

def downgrade() -> None:
    op.drop_index('ix_exec_logs_workspace_provider', table_name='execution_logs')
    op.drop_index('ix_execution_logs_route_family', table_name='execution_logs')
    op.drop_index('ix_execution_logs_evidence_pack_id', table_name='execution_logs')
    op.drop_index('ix_execution_logs_data_tier', table_name='execution_logs')
    op.drop_index('idx_exec_log_ws_tier_created', table_name='execution_logs')
    op.drop_index('idx_exec_log_tier_created_at', table_name='execution_logs')
    op.drop_index('idx_exec_log_gold_training', table_name='execution_logs')
    op.drop_index('idx_exec_log_dedupe_key', table_name='execution_logs')
    op.drop_column('execution_logs', 'training_locked_at')
