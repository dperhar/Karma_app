"""add avatar_url to telegram_messenger_chats

Revision ID: zzzz_add_avatar_url_to_telegram_chats
Revises: 9ce114f5fc20
Create Date: 2025-08-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a5f1c7a9c0b1'
down_revision: Union[str, None] = '9ce114f5fc20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c['name'] for c in inspector.get_columns('telegram_messenger_chats')}
    if 'avatar_url' not in cols:
        with op.batch_alter_table('telegram_messenger_chats') as batch_op:
            batch_op.add_column(sa.Column('avatar_url', sa.String(), nullable=True, comment='Cached avatar path or URL'))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c['name'] for c in inspector.get_columns('telegram_messenger_chats')}
    if 'avatar_url' in cols:
        with op.batch_alter_table('telegram_messenger_chats') as batch_op:
            batch_op.drop_column('avatar_url')


