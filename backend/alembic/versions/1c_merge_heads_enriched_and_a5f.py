"""merge heads enriched and a5f

Revision ID: 1c_merge_heads
Revises: 1b_add_enriched_fields, a5f1c7a9c0b1
Create Date: 2025-08-12
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "1c_merge_heads"
down_revision = ("1b_add_enriched_fields", "a5f1c7a9c0b1")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass



