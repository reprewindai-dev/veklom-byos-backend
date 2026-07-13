"""drop repo risk gate

Revision ID: drop_repo_gate_1234
Revises: fa72be9b2ba0
Create Date: 2026-07-13 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'drop_repo_gate_1234'
down_revision = 'fa72be9b2ba0'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Drop repo risk gate tables
    op.drop_index('ix_repo_risk_gate_events_run_id', table_name='repo_risk_gate_events')
    op.drop_table('repo_risk_gate_events')
    
    op.drop_index('ix_repo_risk_gate_runs_id', table_name='repo_risk_gate_runs')
    op.drop_index('ix_repo_risk_gate_runs_workspace_id', table_name='repo_risk_gate_runs')
    op.drop_table('repo_risk_gate_runs')

def downgrade() -> None:
    pass
