from alembic import op

# revision identifiers, used by Alembic.
revision = '003_add_index_created_at_exec_logs'
down_revision = '002_add_composite_index_exec_logs'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index('ix_execution_logs_created_at', 'execution_logs', ['created_at'])


def downgrade():
    op.drop_index('ix_execution_logs_created_at', table_name='execution_logs')
