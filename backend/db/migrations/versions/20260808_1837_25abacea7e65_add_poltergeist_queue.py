"""add_poltergeist_queue

Revision ID: 25abacea7e65
Revises: bbbb0000aaaa
Create Date: 2026-08-08 18:37:17.925259

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = '25abacea7e65'
down_revision: Union[str, None] = 'bbbb0000aaaa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'manufacturing_jobs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('target_repository', sa.String(), nullable=False, index=True),
        sa.Column('target_commit', sa.String(), nullable=False),
        sa.Column('status', sa.String(32), nullable=False, server_default='DETECTED', index=True),
        sa.Column('metadata', JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    op.create_table(
        'manufacturing_transitions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('job_id', UUID(as_uuid=True), sa.ForeignKey('manufacturing_jobs.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('from_status', sa.String(), nullable=True),
        sa.Column('to_status', sa.String(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('manufacturing_transitions')
    op.drop_table('manufacturing_jobs')
