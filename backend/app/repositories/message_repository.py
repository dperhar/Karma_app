"""Repository for Telegram message operations."""

from collections.abc import Sequence
from typing import Optional, List

from sqlalchemy import join, select, desc, func, and_, or_
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

    async def get_message_by_chat_and_telegram_id(
        self, chat_id: str, telegram_msg_id: int
    ) -> Optional[TelegramMessengerMessage]:
        """Get message by chat DB id and Telegram message id."""
        async with self.get_session() as session:
            try:
                query = select(TelegramMessengerMessage).where(
                    TelegramMessengerMessage.chat_id == chat_id,
                    TelegramMessengerMessage.telegram_id == int(telegram_msg_id),
                )
                result = await session.execute(query)
                return result.unique().scalar_one_or_none()
            except Exception as e:
                self.logger.error(
                    f"Error getting message by chat {chat_id} and telegram_id {telegram_msg_id}: {e!s}",
                    exc_info=True,
                )
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
        self, user_id: str, limit: int = 20, offset: int = 0, source: str = "channels"
    ) -> List[dict]:
        """
        Get recent posts from channels for a user's feed, with optional draft comments.
        """
        async with self.get_session() as session:
            try:
                # Alias for DraftComment to handle the LEFT JOIN correctly for a specific user
                user_draft = aliased(DraftComment)

                # Build source filter with comments_enabled constraint for channels
                if source == "channels":
                    # Treat "channels" as any broadcast channel with discussion enabled OR any supergroup
                    source_filter = or_(
                        and_(
                            TelegramMessengerChat.type == TelegramMessengerChatType.CHANNEL,
                            TelegramMessengerChat.comments_enabled.is_(True),
                        ),
                        TelegramMessengerChat.type == TelegramMessengerChatType.SUPERGROUP,
                    )
                elif source == "groups":
                    source_filter = TelegramMessengerChat.type.in_(
                        [TelegramMessengerChatType.GROUP, TelegramMessengerChatType.SUPERGROUP]
                    )
                else:  # both
                    source_filter = or_(
                        and_(
                            TelegramMessengerChat.type == TelegramMessengerChatType.CHANNEL,
                            TelegramMessengerChat.comments_enabled.is_(True),
                        ),
                        TelegramMessengerChat.type.in_(
                            [TelegramMessengerChatType.GROUP, TelegramMessengerChatType.SUPERGROUP]
                        ),
                    )

                # Straight date-ordered feed (no per-chat balancing)
                query = (
                    select(
                        TelegramMessengerMessage,
                        TelegramMessengerChat.title.label("channel_name"),
                        TelegramMessengerChat.telegram_id.label("channel_telegram_id"),
                        TelegramMessengerChat.type.label("channel_type"),
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
                        source_filter,
                    )
                    .order_by(desc(TelegramMessengerMessage.date))
                    .limit(limit)
                    .offset(offset)
                )

                result = await session.execute(query)
                rows = result.all()

                # Try to fetch avatar URL or leave None (placeholder; actual fetching requires extra API/storage)
                feed_items = []
                for message, channel_name, channel_telegram_id, channel_type, draft in rows:
                    feed_items.append({
                        "post": message,
                        "channel_name": channel_name,
                        "channel_telegram_id": channel_telegram_id,
                        "channel_type": channel_type,
                        "channel_avatar_url": None,
                        "draft": draft,
                    })
                return feed_items
            except SQLAlchemyError as e:
                self.logger.error(f"Error getting feed posts for user {user_id}: {e}", exc_info=True)
                raise

    async def get_feed_posts_total(self, user_id: str, source: str = "channels") -> int:
        """Return the total count of posts available for the user's feed (for pagination)."""
        async with self.get_session() as session:
            try:
                if source == "channels":
                    source_filter = or_(
                        and_(
                            TelegramMessengerChat.type == TelegramMessengerChatType.CHANNEL,
                            TelegramMessengerChat.comments_enabled.is_(True),
                        ),
                        TelegramMessengerChat.type == TelegramMessengerChatType.SUPERGROUP,
                    )
                elif source == "groups":
                    source_filter = TelegramMessengerChat.type.in_(
                        [TelegramMessengerChatType.GROUP, TelegramMessengerChatType.SUPERGROUP]
                    )
                else:
                    source_filter = or_(
                        and_(
                            TelegramMessengerChat.type == TelegramMessengerChatType.CHANNEL,
                            TelegramMessengerChat.comments_enabled.is_(True),
                        ),
                        TelegramMessengerChat.type.in_(
                            [TelegramMessengerChatType.GROUP, TelegramMessengerChatType.SUPERGROUP]
                        ),
                    )

                # Total messages that qualify (for pagination of date-ordered feed)
                query = (
                    select(func.count(TelegramMessengerMessage.id))
                    .join(
                        TelegramMessengerChat,
                        TelegramMessengerMessage.chat_id == TelegramMessengerChat.id,
                    )
                    .where(
                        TelegramMessengerChat.user_id == user_id,
                        source_filter,
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

    async def get_recent_user_messages(self, user_id: str, limit: int = 300) -> list[TelegramMessengerMessage]:
        """Return recent cached Telegram messages authored by the given app user across all chats.

        This does not hit Telegram APIs; it only reads our local DB cache. Suitable for
        lightweight reseeding of Digital Twin freeform without a full analysis.
        """
        async with self.get_session() as session:
            try:
                # Join messages with chat_user to filter only messages sent by this user
                query = (
                    select(TelegramMessengerMessage)
                    .join(
                        TelegramMessengerChatUser,
                        TelegramMessengerMessage.sender_id == TelegramMessengerChatUser.id,
                    )
                    .where(
                        TelegramMessengerChatUser.user_id == user_id,
                        TelegramMessengerMessage.text.is_not(None),
                    )
                    .order_by(desc(TelegramMessengerMessage.date))
                    .limit(limit)
                )
                result = await session.execute(query)
                rows = result.scalars().all()
                return list(rows)
            except SQLAlchemyError as e:
                self.logger.error(
                    f"Error getting recent user messages for user {user_id}: {e}", exc_info=True
                )
                raise

    async def delete_all_for_user(self, user_id: str) -> int:
        """Delete all Telegram messages for a user's chats.

        Returns number of rows deleted.
        """
        from sqlalchemy import delete
        async with self.get_session() as session:
            try:
                # Subquery to select chat ids belonging to the user
                chat_ids_query = select(TelegramMessengerChat.id).where(TelegramMessengerChat.user_id == user_id)
                stmt = delete(TelegramMessengerMessage).where(TelegramMessengerMessage.chat_id.in_(chat_ids_query))
                result = await session.execute(stmt)
                await session.commit()
                return int(getattr(result, "rowcount", 0) or 0)
            except SQLAlchemyError as e:
                await session.rollback()
                self.logger.error(f"Error deleting messages for user {user_id}: {e}", exc_info=True)
                raise
