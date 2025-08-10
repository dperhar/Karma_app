"""Add draft comment model and persona fields

Revision ID: d8aa3a2236bd
Revises: 66f2c8cc2158
Create Date: 2025-05-26 13:40:16.073997

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8aa3a2236bd'
down_revision: Union[str, None] = '66f2c8cc2158'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create draft_comments table to support later migrations referencing it
    op.create_table(
        'draft_comments',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('original_message_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('persona_name', sa.String(), nullable=True),
        sa.Column('ai_model_used', sa.String(), nullable=True),
        sa.Column('original_post_url', sa.String(), nullable=True),
        sa.Column('original_post_content', sa.Text(), nullable=True),
        sa.Column('ai_context_summary', sa.Text(), nullable=True),
        sa.Column('original_post_text_preview', sa.Text(), nullable=True),
        sa.Column('draft_text', sa.Text(), nullable=False),
        sa.Column('edited_text', sa.Text(), nullable=True),
        sa.Column('final_text_to_post', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='DRAFT'),
        sa.Column('posted_telegram_message_id', sa.BigInteger(), nullable=True),
        sa.Column('generation_params', sa.JSON(), nullable=True),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['original_message_id'], ['telegram_messenger_messages.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
    )


def downgrade() -> None:
    op.drop_table('draft_comments')
