"""Base repository module providing database session management functionality."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import ClassVar, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T")


class SingletonMeta(type):
    """Metaclass to implement the Singleton pattern."""

    _instances: ClassVar[dict[type, object]] = {}

    def __call__(cls, *args, **kwargs):
        """Create a new instance or return an existing one."""
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class BaseRepository(metaclass=SingletonMeta):
    """Base repository class with singleton pattern."""

    def __init__(self):
        """Initialize the repository."""
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Check if using SQLite
        is_sqlite = settings.DATABASE_URL.startswith("sqlite")
        
        if is_sqlite:
            self.logger.debug("Using SQLite database, skipping pool configuration")
            self.async_engine = create_async_engine(
                settings.DATABASE_URL,
                echo=False,
                poolclass=NullPool,
            )
        else:
            self.logger.debug("Initializing database connection pool with settings:")
            self.logger.debug(f"Pool size: {settings.DB_POOL_SIZE}")
            self.logger.debug(f"Max overflow: {settings.DB_MAX_OVERFLOW}")
            self.logger.debug(f"Pool timeout: {settings.DB_POOL_TIMEOUT}")
            self.logger.debug(f"Pool recycle: {settings.DB_POOL_RECYCLE}")
            
            # Use NullPool to avoid reusing connections across different event loops
            # in Celery tasks (prevents 'Event loop is closed' transport errors).
            self.async_engine = create_async_engine(
                settings.DATABASE_URL,
                pool_pre_ping=True,
                echo=False,
                poolclass=NullPool,
            )
            
        self.async_session_factory = async_sessionmaker(
            self.async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        self.logger.debug("Database connection initialized successfully")

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get async session with context manager."""
        self.logger.debug("Acquiring new database session")
        async with self.async_session_factory() as session:
            try:
                self.logger.debug("Database session acquired")
                yield session
            except Exception as e:
                self.logger.error(f"Error in database session: {e!s}", exc_info=True)
                await session.rollback()
                raise
            finally:
                self.logger.debug("Closing database session")
                await session.close()
