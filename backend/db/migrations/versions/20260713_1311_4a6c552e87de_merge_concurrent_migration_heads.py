"""merge concurrent migration heads

Revision ID: 4a6c552e87de
Revises: 5340720ec7f0, drop_repo_gate_1234
Create Date: 2026-07-13 13:11:29.402616

"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = '4a6c552e87de'
down_revision: Union[str, None] = ('5340720ec7f0', 'drop_repo_gate_1234')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
