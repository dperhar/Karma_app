"""add gemini enum value

Revision ID: 7a391da17120
Revises: 124263f8e860
Create Date: 2025-08-14 08:00:12.717966

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '7a391da17120'
down_revision: Union[str, None] = '124263f8e860'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
	# Add GEMINI_2_5_PRO to airequestmodel enum if missing
	enum_name = 'airequestmodel'
	conn = op.get_bind()
	# Check current labels
	labels = conn.execute(sa.text("""
		SELECT e.enumlabel
		FROM pg_type t
		JOIN pg_enum e ON t.oid = e.enumtypid
		JOIN pg_namespace n ON n.oid = t.typnamespace
		WHERE t.typname = :enum
		ORDER BY e.enumsortorder
	"""), {"enum": enum_name}).fetchall()
	labels = [row[0] for row in labels]
	if 'GEMINI_2_5_PRO' not in labels:
		op.execute(sa.text("ALTER TYPE airequestmodel ADD VALUE IF NOT EXISTS 'GEMINI_2_5_PRO'"))

	# Ensure users.preferred_ai_model column uses the updated enum
	op.alter_column('users', 'preferred_ai_model', type_=postgresql.ENUM('GPT_4_1','GPT_4_1_MINI','GPT_4_1_NANO','CLAUDE_3_7_SONNET','CLAUDE_3_5_HAIKU','GEMINI_2_5_PRO', name='airequestmodel'), existing_nullable=True)
	# Ensure ai_requests.model column uses the updated enum
	op.alter_column('ai_requests', 'model', type_=postgresql.ENUM('GPT_4_1','GPT_4_1_MINI','GPT_4_1_NANO','CLAUDE_3_7_SONNET','CLAUDE_3_5_HAIKU','GEMINI_2_5_PRO', name='airequestmodel'), existing_nullable=False)


def downgrade() -> None:
	# Downgrade: cannot easily remove an enum value in Postgres; noop
	pass
