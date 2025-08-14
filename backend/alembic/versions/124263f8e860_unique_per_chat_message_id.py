"""unique per chat message id

Revision ID: 124263f8e860
Revises: 1c_merge_heads
Create Date: 2025-08-14 07:33:20.195287

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '124263f8e860'
down_revision: Union[str, None] = '1c_merge_heads'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Safely replace global unique(telegram_id) with per-chat unique(chat_id, telegram_id)
    try:
        op.drop_constraint('telegram_messenger_messages_telegram_id_key', 'telegram_messenger_messages', type_='unique')
    except Exception:
        pass
    op.create_unique_constraint('uix_msg_chat_telegram_id', 'telegram_messenger_messages', ['chat_id', 'telegram_id'])


def downgrade() -> None:
    # Revert to global unique(telegram_id)
    try:
        op.drop_constraint('uix_msg_chat_telegram_id', 'telegram_messenger_messages', type_='unique')
    except Exception:
        pass
    op.create_unique_constraint('telegram_messenger_messages_telegram_id_key', 'telegram_messenger_messages', ['telegram_id'])
