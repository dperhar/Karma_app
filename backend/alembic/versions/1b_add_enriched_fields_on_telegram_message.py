"""add enriched fields on telegram message

Revision ID: 1b_add_enriched_fields
Revises: 06f470a082c1
Create Date: 2025-08-12
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "1b_add_enriched_fields"
down_revision = "06f470a082c1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("telegram_messenger_messages") as batch_op:
        batch_op.add_column(sa.Column("language", sa.String(length=8), nullable=True))
        batch_op.add_column(sa.Column("link_urls", postgresql.JSON(astext_type=sa.Text()), nullable=True))
        batch_op.add_column(sa.Column("named_entities", postgresql.JSON(astext_type=sa.Text()), nullable=True))
        batch_op.add_column(sa.Column("tokens", postgresql.JSON(astext_type=sa.Text()), nullable=True))
        batch_op.add_column(sa.Column("rhetorical_type", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("env_quadrant", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("style_snapshot", postgresql.JSON(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("telegram_messenger_messages") as batch_op:
        batch_op.drop_column("style_snapshot")
        batch_op.drop_column("env_quadrant")
        batch_op.drop_column("rhetorical_type")
        batch_op.drop_column("tokens")
        batch_op.drop_column("named_entities")
        batch_op.drop_column("link_urls")
        batch_op.drop_column("language")


