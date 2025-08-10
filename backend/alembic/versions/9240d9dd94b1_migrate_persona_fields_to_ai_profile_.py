"""migrate_persona_fields_to_ai_profile_and_add_celery_support

Revision ID: 9240d9dd94b1
Revises: 3599bc0c0a99
Create Date: 2025-06-09 18:27:32.978800

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9240d9dd94b1'
down_revision: Union[str, None] = '3599bc0c0a99'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add persona fields to ai_profiles table
    op.add_column('ai_profiles', sa.Column('persona_name', sa.String(), nullable=True, comment='User-defined or AI-suggested persona name'))
    op.add_column('ai_profiles', sa.Column('user_system_prompt', sa.Text(), nullable=True, comment='AI system prompt derived from the user\'s topics/interests'))
    
    # Migrate data from users to ai_profiles
    # First, create a connection to execute raw SQL
    connection = op.get_bind()
    
    # Get all users with persona data
    users_with_persona = connection.execute(sa.text("""
        SELECT id, persona_name, user_system_prompt 
        FROM users 
        WHERE persona_name IS NOT NULL OR user_system_prompt IS NOT NULL
    """)).fetchall()
    
    # For each user with persona data, update their ai_profile or create one
    for user in users_with_persona:
        user_id, persona_name, user_system_prompt = user
        
        # Check if ai_profile exists
        ai_profile_exists = connection.execute(sa.text("""
            SELECT id FROM ai_profiles WHERE user_id = :user_id
        """), {"user_id": user_id}).fetchone()
        
        if ai_profile_exists:
            # Update existing ai_profile
            connection.execute(sa.text("""
                UPDATE ai_profiles 
                SET persona_name = :persona_name, user_system_prompt = :user_system_prompt
                WHERE user_id = :user_id
            """), {
                "persona_name": persona_name,
                "user_system_prompt": user_system_prompt,
                "user_id": user_id
            })
        else:
            # Create new ai_profile
            from uuid import uuid4
            ai_profile_id = uuid4().hex
            connection.execute(sa.text("""
                INSERT INTO ai_profiles (id, user_id, persona_name, user_system_prompt, analysis_status, created_at, updated_at)
                VALUES (:id, :user_id, :persona_name, :user_system_prompt, 'PENDING', NOW(), NOW())
            """), {
                "id": ai_profile_id,
                "user_id": user_id,
                "persona_name": persona_name,
                "user_system_prompt": user_system_prompt
            })
    
    # Remove persona fields from users table
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('persona_name')
        batch_op.drop_column('persona_style_description')
        batch_op.drop_column('persona_interests_json')
        batch_op.drop_column('user_system_prompt')
        batch_op.drop_column('last_context_analysis_at')
        batch_op.drop_column('context_analysis_status')


def downgrade() -> None:
    # Add persona fields back to users table
    op.add_column('users', sa.Column('persona_name', sa.String(), nullable=True, default='Default User'))
    op.add_column('users', sa.Column('persona_style_description', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('persona_interests_json', sa.JSON(), nullable=True))
    op.add_column('users', sa.Column('user_system_prompt', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('last_context_analysis_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('context_analysis_status', sa.String(), nullable=True))
    
    # Migrate data back from ai_profiles to users
    connection = op.get_bind()
    
    ai_profiles_with_persona = connection.execute(sa.text("""
        SELECT user_id, persona_name, user_system_prompt 
        FROM ai_profiles 
        WHERE persona_name IS NOT NULL OR user_system_prompt IS NOT NULL
    """)).fetchall()
    
    for ai_profile in ai_profiles_with_persona:
        user_id, persona_name, user_system_prompt = ai_profile
        connection.execute(sa.text("""
            UPDATE users 
            SET persona_name = :persona_name, user_system_prompt = :user_system_prompt
            WHERE id = :user_id
        """), {
            "persona_name": persona_name,
            "user_system_prompt": user_system_prompt,
            "user_id": user_id
        })
    
    # Remove persona fields from ai_profiles table
    with op.batch_alter_table('ai_profiles') as batch_op:
        batch_op.drop_column('persona_name')
        batch_op.drop_column('user_system_prompt')
