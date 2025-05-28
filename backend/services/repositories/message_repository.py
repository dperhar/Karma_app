"""Repository for message management operations."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from models.base.message import Message, MessageStatus
from services.base.base_repository import BaseRepository


class MessageRepository(BaseRepository):
    """Repository class for message management."""

    async def create_message(self, **message_data) -> Optional[Message]:
        """Create a new message."""
        async with self.get_session() as session:
            try:
                self.logger.info("Creating message with data: %s", message_data)
                message = Message(**message_data)
                session.add(message)
                await session.commit()
                await session.refresh(message)
                self.logger.info("Message created successfully with id: %s", message.id)
                return message
            except SQLAlchemyError as e:
                await session.rollback()
                self.logger.error("Error creating message: %s", str(e), exc_info=True)
                raise

    async def get_message(self, message_id: str) -> Optional[Message]:
        """Get message by ID."""
        async with self.get_session() as session:
            try:
                query = select(Message).where(Message.id == message_id)
                result = await session.execute(query)
                message = result.scalar_one_or_none()
                if not message:
                    self.logger.info("Message not found with id: %s", message_id)
                return message
            except SQLAlchemyError as e:
                self.logger.error("Error getting message: %s", str(e), exc_info=True)
                raise

    async def update_message(self, message_id: str, **update_data) -> Optional[Message]:
        """Update message data."""
        async with self.get_session() as session:
            try:
                message = await session.get(Message, message_id)
                if not message:
                    self.logger.info("Message not found with id: %s", message_id)
                    return None

                for key, value in update_data.items():
                    if hasattr(message, key):
                        setattr(message, key, value)

                await session.commit()
                await session.refresh(message)
                self.logger.info("Message updated successfully: %s", message_id)
                return message
            except SQLAlchemyError as e:
                await session.rollback()
                self.logger.error("Error updating message: %s", str(e), exc_info=True)
                raise

    async def delete_message(self, message_id: str) -> None:
        """Delete message by ID."""
        async with self.get_session() as session:
            try:
                message = await session.get(Message, message_id)
                if message:
                    await session.delete(message)
                    await session.commit()
                    self.logger.info("Message deleted successfully: %s", message_id)
                else:
                    self.logger.info("Message not found for deletion: %s", message_id)
            except SQLAlchemyError as e:
                await session.rollback()
                self.logger.error("Error deleting message: %s", str(e), exc_info=True)
                raise

    async def get_messages(self) -> list[Message]:
        """Get all messages."""
        async with self.get_session() as session:
            query = select(Message)
            result = await session.execute(query)
            return result.scalars().all()

    async def update_message_status(
        self, message_id: str, status: MessageStatus
    ) -> Optional[Message]:
        """Update message status."""
        async with self.get_session() as session:
            try:
                message = await session.get(Message, message_id)
                if not message:
                    self.logger.info("Message not found with id: %s", message_id)
                    return None

                message.status = status
                await session.commit()
                await session.refresh(message)
                self.logger.info("Message status updated successfully: %s", message_id)
                return message
            except SQLAlchemyError as e:
                await session.rollback()
                self.logger.error(
                    "Error updating message status: %s", str(e), exc_info=True
                )
                raise
