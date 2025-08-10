"""restore header for revision 66f2c8cc2158 (no-op)

Revision ID: 66f2c8cc2158
Revises: 02065227fdc1
Create Date: 2024-05-26 13:30:12.866418

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '66f2c8cc2158'
down_revision: Union[str, None] = '02065227fdc1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # historical migration restored as no-op
    pass


def downgrade() -> None:
    # historical migration restored as no-op
    pass
