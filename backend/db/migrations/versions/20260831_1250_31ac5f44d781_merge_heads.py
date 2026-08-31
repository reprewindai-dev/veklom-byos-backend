"""merge heads

Revision ID: 31ac5f44d781
Revises: 7b2f6ea50d81, 8fbb4a18276e
Create Date: 2026-08-31 12:50:36.045844

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '31ac5f44d781'
down_revision: Union[str, None] = ('7b2f6ea50d81', '8fbb4a18276e')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
