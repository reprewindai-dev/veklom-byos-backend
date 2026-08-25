"""merge heads

Revision ID: fa72be9b2ba0
Revises: d51e758d7678, f2c68494b79b
Create Date: 2026-07-11 19:04:33.178945

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fa72be9b2ba0'
down_revision: Union[str, None] = ('d51e758d7678', 'f2c68494b79b')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
