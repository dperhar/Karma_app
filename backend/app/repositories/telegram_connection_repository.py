"""Repository for Telegram connection management."""

from typing import Optional

from sqlalchemy import select, update, desc
from sqlalchemy.exc import SQLAlchemyError

from app.models.telegram_connection import TelegramConnection
from app.services.base_repository import BaseRepository


class TelegramConnectionRepository(BaseRepository):
    """Repository for Telegram connection operations."""

    async def get_by_user_id(self, user_id: str) -> Optional[TelegramConnection]:
        """Get Telegram connection by user ID."""
        async with self.get_session() as session:
            try:
                query = select(TelegramConnection).where(TelegramConnection.user_id == user_id)
                result = await session.execute(query)
                connection = result.unique().scalar_one_or_none()
                return connection
            except SQLAlchemyError as e:
                self.logger.error("Error getting Telegram connection by user_id %s: %s", user_id, str(e), exc_info=True)
                raise

    async def create_or_update(self, user_id: str, **kwargs) -> TelegramConnection:
        """Create or update a Telegram connection."""
        async with self.get_session() as session:
            try:
                # Check if connection exists using the current session
                query = select(TelegramConnection).where(TelegramConnection.user_id == user_id)
                result = await session.execute(query)
                connection = result.unique().scalar_one_or_none()
                
                if connection:
                    # Update existing connection
                    for key, value in kwargs.items():
                        setattr(connection, key, value)
                    self.logger.info(f"Updated existing Telegram connection for user {user_id}")
                else:
                    # Create new connection
                    connection = TelegramConnection(user_id=user_id, **kwargs)
                    session.add(connection)
                    self.logger.info(f"Created new Telegram connection for user {user_id}")
                
                await session.commit()
                await session.refresh(connection)
                return connection
            except SQLAlchemyError as e:
                await session.rollback()
                self.logger.error("Error creating/updating Telegram connection for user %s: %s", user_id, str(e), exc_info=True)
                raise

    async def update_validation_status(self, user_id: str, status: str, last_validation_at) -> None:
        """Update the validation status of a connection."""
        async with self.get_session() as session:
            stmt = (
                update(TelegramConnection)
                .where(TelegramConnection.user_id == user_id)
                .values(validation_status=status, last_validation_at=last_validation_at)
            )
            await session.execute(stmt)
            await session.commit() 

    async def get_latest_valid_connection(self) -> Optional[TelegramConnection]:
        """Return the most recently validated active Telegram connection across all users.

        Used by dev auth fallback to select the active account when no session cookie is present.
        """
        async with self.get_session() as session:
            try:
                query = (
                    select(TelegramConnection)
                    .where(
                        TelegramConnection.is_active.is_(True),
                        TelegramConnection.validation_status == "VALID",
                        TelegramConnection.session_string_encrypted.is_not(None),
                    )
                    .order_by(desc(TelegramConnection.last_validation_at))
                )
                result = await session.execute(query)
                return result.unique().scalars().first()
            except SQLAlchemyError as e:
                self.logger.error("Error selecting latest valid connection: %s", str(e), exc_info=True)
                raise