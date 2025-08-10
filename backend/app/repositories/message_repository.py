"""Repository for Telegram message operations."""

from collections.abc import Sequence
from typing import Optional, List

from sqlalchemy import join, select, desc, func
from sqlalchemy.orm import aliased
from sqlalchemy.exc import SQLAlchemyError

from app.models.chat_user import TelegramMessengerChatUser
from app.models.telegram_message import TelegramMessengerMessage
from app.models.draft_comment import DraftComment
from app.models.chat import TelegramMessengerChat, TelegramMessengerChatType
from app.services.base_repository import BaseRepository


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

                self.logger.info(f"Successfully retrieved {len(processed_messages)} messages for chat {chat_id}")
                return processed_messages
            except Exception as e:
                self.logger.error(f"Error getting chat messages: {e!s}", exc_info=True)
                raise

    async def get_feed_posts(
        self, user_id: str, limit: int = 20, offset: int = 0, source: str = "channel"
    ) -> List[dict]:
        """
        Get recent posts from channels for a user's feed, with optional draft comments.
        """
        async with self.get_session() as session:
            try:
                # Alias for DraftComment to handle the LEFT JOIN correctly for a specific user
                user_draft = aliased(DraftComment)

                query = (
                    select(
                        TelegramMessengerMessage,
                        TelegramMessengerChat.title.label("channel_name"),
                        TelegramMessengerChat.telegram_id.label("channel_telegram_id"),
                        user_draft,
                    )
                    .join(
                        TelegramMessengerChat,
                        TelegramMessengerMessage.chat_id == TelegramMessengerChat.id,
                    )
                    .outerjoin(
                        user_draft,
                        (user_draft.original_message_id == TelegramMessengerMessage.id)
                        & (user_draft.user_id == user_id),
                    )
                    .where(
                        TelegramMessengerChat.user_id == user_id,
                        (
                            (TelegramMessengerChat.type == TelegramMessengerChatType.CHANNEL)
                            if source == "channel"
                            else (
                                (TelegramMessengerChat.type == TelegramMessengerChatType.SUPERGROUP)
                                if source == "supergroup"
                                else (TelegramMessengerChat.type.in_([TelegramMessengerChatType.CHANNEL, TelegramMessengerChatType.SUPERGROUP]))
                            )
                        ),
                        TelegramMessengerChat.comments_enabled.is_(True),
                    )
                    .order_by(desc(TelegramMessengerMessage.date))
                    .limit(limit)
                    .offset(offset)
                )

                result = await session.execute(query)
                rows = result.all()

                # Try to fetch avatar URL or leave None (placeholder; actual fetching requires extra API/storage)
                feed_items = []
                for message, channel_name, channel_telegram_id, draft in rows:
                    feed_items.append({
                        "post": message,
                        "channel_name": channel_name,
                        "channel_telegram_id": channel_telegram_id,
                        "channel_avatar_url": None,
                        "draft": draft,
                    })
                return feed_items
            except SQLAlchemyError as e:
                self.logger.error(f"Error getting feed posts for user {user_id}: {e}", exc_info=True)
                raise

    async def get_feed_posts_total(self, user_id: str, source: str = "channel") -> int:
        """Return the total count of posts available for the user's feed (for pagination)."""
        async with self.get_session() as session:
            try:
                query = (
                    select(func.count(TelegramMessengerMessage.id))
                    .join(
                        TelegramMessengerChat,
                        TelegramMessengerMessage.chat_id == TelegramMessengerChat.id,
                    )
                    .where(
                        TelegramMessengerChat.user_id == user_id,
                        (
                            (TelegramMessengerChat.type == TelegramMessengerChatType.CHANNEL)
                            if source == "channel"
                            else (
                                (TelegramMessengerChat.type == TelegramMessengerChatType.SUPERGROUP)
                                if source == "supergroup"
                                else (TelegramMessengerChat.type.in_([TelegramMessengerChatType.CHANNEL, TelegramMessengerChatType.SUPERGROUP]))
                            )
                        ),
                        TelegramMessengerChat.comments_enabled.is_(True),
                    )
                )
                result = await session.execute(query)
                total: int = int(result.scalar() or 0)
                return total
            except SQLAlchemyError as e:
                self.logger.error(
                    f"Error counting feed posts for user {user_id}: {e}", exc_info=True
                )
                raise
