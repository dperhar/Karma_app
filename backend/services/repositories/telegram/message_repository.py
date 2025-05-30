"""Repository for Telegram message operations."""

from collections.abc import Sequence
from typing import Optional

from sqlalchemy import join, select

from models.telegram_messenger.chat_user import TelegramMessengerChatUser
from models.telegram_messenger.message import TelegramMessengerMessage
from services.base.base_repository import BaseRepository


class MessageRepository(BaseRepository):
    """Repository class for Telegram message operations."""

    async def create_or_update_messages(
        self, messages: Sequence[TelegramMessengerMessage]
    ) -> list[TelegramMessengerMessage]:
        """Create or update multiple messages.

        Args:
            messages: List of TelegramMessengerMessage objects to create or update

        Returns:
            List of created/updated TelegramMessengerMessage objects
        """
        async with self.get_session() as session:
            try:
                result_messages = []
                for message in messages:
                    # Check if message exists by telegram_id and chat_id
                    query = select(TelegramMessengerMessage).where(
                        TelegramMessengerMessage.telegram_id == message.telegram_id,
                        TelegramMessengerMessage.chat_id == message.chat_id,
                    )
                    result = await session.execute(query)
                    existing_message = result.unique().scalar_one_or_none()

                    if existing_message:
                        # Update existing message
                        for key, value in message.__dict__.items():
                            if key != "id" and not key.startswith("_"):
                                setattr(existing_message, key, value)
                        result_messages.append(existing_message)
                    else:
                        # Create new message
                        session.add(message)
                        result_messages.append(message)

                await session.commit()
                for message in result_messages:
                    await session.refresh(message)

                self.logger.info(
                    f"Successfully processed {len(result_messages)} messages"
                )
                return result_messages

            except Exception as e:
                await session.rollback()
                self.logger.error(
                    f"Error creating/updating messages: {e!s}", exc_info=True
                )
                raise

    async def get_message(self, message_id: str) -> Optional[TelegramMessengerMessage]:
        """Get message by ID.

        Args:
            message_id: Message ID

        Returns:
            TelegramMessengerMessage object or None if not found
        """
        async with self.get_session() as session:
            try:
                query = select(TelegramMessengerMessage).where(
                    TelegramMessengerMessage.id == message_id
                )
                result = await session.execute(query)
                message = result.unique().scalar_one_or_none()
                if not message:
                    self.logger.info(f"Message not found with id: {message_id}")
                return message
            except Exception as e:
                self.logger.error(f"Error getting message: {e!s}", exc_info=True)
                raise

    async def get_chat_messages(
        self, chat_id: str, limit: int = 100, offset: int = 0
    ) -> list[TelegramMessengerMessage]:
        """Get messages for a chat with user information.

        Args:
            chat_id: Chat ID
            limit: Maximum number of messages to retrieve
            offset: Number of messages to skip

        Returns:
            List of TelegramMessengerMessage objects with user information populated
        """
        async with self.get_session() as session:
            try:
                # Create a join between messages and chat users
                query = (
                    select(TelegramMessengerMessage, TelegramMessengerChatUser)
                    .join(
                        TelegramMessengerChatUser,
                        TelegramMessengerMessage.sender_id
                        == TelegramMessengerChatUser.id,
                        isouter=True,  # Left outer join to include messages without sender
                    )
                    .where(TelegramMessengerMessage.chat_id == chat_id)
                    .limit(limit)
                    .offset(offset)
                    .order_by(TelegramMessengerMessage.telegram_id.desc())
                )

                result = await session.execute(query)
                messages_with_users = result.unique().all()

                # Process results to include user information in the message objects
                processed_messages = []
                for message_row, user_row in messages_with_users:
                    # Add user information to the message object
                    if user_row:
                        message_row.sender_first_name = user_row.first_name
                        message_row.sender_last_name = user_row.last_name
                        message_row.sender_username = user_row.username
                    processed_messages.append(message_row)

                return processed_messages
            except Exception as e:
                self.logger.error(f"Error getting chat messages: {e!s}", exc_info=True)
                raise
