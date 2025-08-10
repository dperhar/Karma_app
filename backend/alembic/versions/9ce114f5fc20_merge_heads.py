"""merge heads

Revision ID: 9ce114f5fc20
Revises: a1b2c3d4e5f6, aa11bb22cc33
Create Date: 2025-08-08 07:20:40.065794

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9ce114f5fc20'
down_revision: Union[str, None] = ('a1b2c3d4e5f6', 'aa11bb22cc33')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
