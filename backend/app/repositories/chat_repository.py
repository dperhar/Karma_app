"""Repository for Telegram chat operations."""

from collections.abc import Sequence
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.models.chat import TelegramMessengerChat
from app.services.base_repository import BaseRepository


class ChatRepository(BaseRepository):
    """Repository class for Telegram chat operations."""

    async def create_or_update_chats(
        self, chats: Sequence[TelegramMessengerChat]
    ) -> list[TelegramMessengerChat]:
        """Create or update multiple chats.

        Args:
            chats: List of TelegramMessengerChat objects to create or update

        Returns:
            List of created/updated TelegramMessengerChat objects
        """
        async with self.get_session() as session:
            try:
                result_chats = []
                for chat in chats:
                    # Check if chat exists by telegram_id and user_id
                    query = select(TelegramMessengerChat).where(
                        TelegramMessengerChat.telegram_id == chat.telegram_id,
                        TelegramMessengerChat.user_id == chat.user_id,
                    )
                    result = await session.execute(query)
                    existing_chat = result.unique().scalar_one_or_none()

                    if existing_chat:
                        # Update existing chat
                        for key, value in chat.__dict__.items():
                            if key != "id" and not key.startswith("_"):
                                setattr(existing_chat, key, value)
                        result_chats.append(existing_chat)
                    else:
                        # Create new chat
                        session.add(chat)
                        result_chats.append(chat)

                await session.commit()
                for chat in result_chats:
                    await session.refresh(chat)

                self.logger.info(f"Successfully processed {len(result_chats)} chats")
                return result_chats

            except SQLAlchemyError as e:
                await session.rollback()
                self.logger.error(
                    f"Error creating/updating chats: {e!s}", exc_info=True
                )
                raise

    async def get_chat(self, chat_id: str) -> Optional[TelegramMessengerChat]:
        """Get chat by ID.

        Args:
            chat_id: Chat ID

        Returns:
            TelegramMessengerChat object or None if not found
        """
        async with self.get_session() as session:
            try:
                query = select(TelegramMessengerChat).where(
                    TelegramMessengerChat.id == chat_id
                )
                result = await session.execute(query)
                chat = result.unique().scalar_one_or_none()
                if not chat:
                    self.logger.info(f"Chat not found with id: {chat_id}")
                return chat
            except SQLAlchemyError as e:
                self.logger.error(f"Error getting chat: {e!s}", exc_info=True)
                raise

    async def get_chat_by_telegram_id(
        self, telegram_id: int, user_id: str
    ) -> Optional[TelegramMessengerChat]:
        """Get chat by Telegram ID and user ID.

        Args:
            telegram_id: Telegram chat ID
            user_id: User ID

        Returns:
            TelegramMessengerChat object or None if not found
        """
        async with self.get_session() as session:
            try:
                query = select(TelegramMessengerChat).where(
                    TelegramMessengerChat.telegram_id == telegram_id,
                    TelegramMessengerChat.user_id == user_id,
                )
                result = await session.execute(query)
                chat = result.unique().scalar_one_or_none()
                if not chat:
                    self.logger.info(
                        f"Chat not found with telegram_id: {telegram_id}, user_id: {user_id}"
                    )
                return chat
            except SQLAlchemyError as e:
                self.logger.error(f"Error getting chat: {e!s}", exc_info=True)
                raise

    async def get_user_chats(
        self, user_id: str, limit: int = 100, offset: int = 0
    ) -> list[TelegramMessengerChat]:
        """Get all chats for a user.

        Args:
            user_id: User ID
            limit: Maximum number of chats to retrieve
            offset: Number of chats to skip

        Returns:
            List of TelegramMessengerChat objects
        """
        async with self.get_session() as session:
            try:
                query = (
                    select(TelegramMessengerChat)
                    .where(TelegramMessengerChat.user_id == user_id)
                    .limit(limit)
                    .offset(offset)
                )
                result = await session.execute(query)
                chats = result.unique().scalars().all()
                return list(chats)
            except SQLAlchemyError as e:
                self.logger.error(f"Error getting user chats: {e!s}", exc_info=True)
                raise

    async def update_chat_last_fetched_message(
        self, 
        chat_telegram_id: int, 
        last_message_id: int, 
        fetch_time: datetime
    ) -> Optional[TelegramMessengerChat]:
        """Update the last fetched message ID and timestamp for a chat.

        Args:
            chat_telegram_id: Telegram chat ID
            last_message_id: ID of the last fetched message
            fetch_time: Timestamp of the fetch operation

        Returns:
            Updated TelegramMessengerChat object or None if not found
        """
        async with self.get_session() as session:
            try:
                query = select(TelegramMessengerChat).where(
                    TelegramMessengerChat.telegram_id == chat_telegram_id
                )
                result = await session.execute(query)
                chat = result.unique().scalar_one_or_none()

                if chat:
                    chat.last_fetched_message_telegram_id = last_message_id
                    chat.last_successful_fetch_at = fetch_time
                    await session.commit()
                    await session.refresh(chat)
                    self.logger.info(
                        f"Updated last fetched message for chat {chat_telegram_id}: {last_message_id}"
                    )
                else:
                    self.logger.warning(
                        f"Chat not found with telegram_id: {chat_telegram_id}"
                    )

                return chat
            except SQLAlchemyError as e:
                await session.rollback()
                self.logger.error(f"Error updating chat last fetched message: {e!s}", exc_info=True)
                raise
