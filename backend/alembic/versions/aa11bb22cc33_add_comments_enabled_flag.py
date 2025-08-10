"""add_comments_enabled_flag

Revision ID: aa11bb22cc33
Revises: 4a6dc26a8d51
Create Date: 2025-08-08 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'aa11bb22cc33'
down_revision: Union[str, None] = '4a6dc26a8d51'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('telegram_messenger_chats', schema=None) as batch_op:
        batch_op.add_column(sa.Column('comments_enabled', sa.Boolean(), nullable=False, server_default=sa.text('FALSE')))


def downgrade() -> None:
    with op.batch_alter_table('telegram_messenger_chats', schema=None) as batch_op:
        batch_op.drop_column('comments_enabled') 