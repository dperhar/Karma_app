"""
Migration environment setup for Alembic.
"""

import os
import sys
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import Base model for Alembic migrations
# ruff: noqa: E402
from models.db_base import DBBase

# Load environment variables from .env file in project root
env_path = os.path.join(os.path.dirname(project_root), '.env')
load_dotenv(env_path)

# Load Alembic configuration
config = context.config  # pylint: disable=no-member

# Configure logging from configuration file
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use database URL from environment variables, replacing the driver with synchronous
database_url = os.getenv("DATABASE_URL")

# Fallback to SQLite if no DATABASE_URL is set
if not database_url:
    database_url = "sqlite+aiosqlite:///./karma_app.db"

# Replace async drivers with sync ones for Alembic compatibility
if "asyncpg" in database_url:
    database_url = database_url.replace("asyncpg", "psycopg2")
elif "aiosqlite" in database_url:
    database_url = database_url.replace("aiosqlite", "pysqlite")

config.set_main_option("sqlalchemy.url", database_url)

# Set metadata for automatic migration generation
target_metadata = DBBase.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(  # pylint: disable=no-member
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():  # pylint: disable=no-member
        context.run_migrations()  # pylint: disable=no-member


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(  # pylint: disable=no-member
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # Useful for modifying existing tables
        )

        with context.begin_transaction():  # pylint: disable=no-member
            context.run_migrations()  # pylint: disable=no-member


# Determine the mode of migration execution: 'offline' or 'online'
if context.is_offline_mode():  # pylint: disable=no-member
    run_migrations_offline()
else:
    run_migrations_online()
