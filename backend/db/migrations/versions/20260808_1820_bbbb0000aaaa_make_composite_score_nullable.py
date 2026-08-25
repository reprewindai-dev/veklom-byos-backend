"""make composite score nullable

Revision ID: bbbb0000aaaa
Revises: 9b6f0e0c1f2a
Create Date: 2026-08-08 18:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bbbb0000aaaa'
down_revision: Union[str, None] = '9b6f0e0c1f2a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Alter Column Type to make it nullable and drop default 100.0
    op.alter_column('vnp_apis', 'current_composite_score',
               existing_type=sa.Float(),
               nullable=True,
               server_default=None)

    # 2. Alter Column stability_rating default to 'Unmeasured'
    op.alter_column('vnp_apis', 'stability_rating',
               existing_type=sa.String(length=50),
               server_default=sa.text("'Unmeasured'::character varying"))
               
    # 3. Data Migration: For existing records, don't blindly convert every 100.0 to null.
    # Null only records for which the database has no valid measurement evidence.
    op.execute(
        """
        UPDATE vnp_apis
        SET current_composite_score = NULL,
            stability_rating = 'Unmeasured'
        WHERE current_composite_score = 100.0
        AND id NOT IN (
            SELECT DISTINCT api_id 
            FROM vnp_probe_events
        )
        """
    )


def downgrade() -> None:
    op.alter_column('vnp_apis', 'current_composite_score',
               existing_type=sa.Float(),
               nullable=False,
               server_default=sa.text('100.0'))
    op.alter_column('vnp_apis', 'stability_rating',
               existing_type=sa.String(length=50),
               server_default=sa.text("'Stable'::character varying"))
