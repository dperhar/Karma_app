"""Database session configuration."""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Get database URL from environment variables
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./karma_app.db")

# Replace async drivers with sync ones for regular SQLAlchemy
if "asyncpg" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("asyncpg", "psycopg2")
elif "aiosqlite" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("aiosqlite", "pysqlite")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) 