"""Service module for handling Telegram client operations."""

from datetime import datetime, timezone
from typing import Any, Optional, Union
from uuid import uuid4

from telethon import TelegramClient
from telethon.tl.types import (
    Channel as TelethonChannel,
)
from telethon.tl.types import (
    Chat as TelethonChat,
)
from telethon.tl.types import (
    Message as TelethonMessage,
)
from telethon.tl.types import (
    MessageMediaDocument,
    MessageMediaPhoto,
    PeerChannel,
    PeerChat,
    PeerUser,
)
from telethon.tl.types import (
    User as TelethonUser,
)

from models.telegram_messenger.chat import (
    TelegramMessengerChat,
    TelegramMessengerChatType,
)
from models.telegram_messenger.chat_user import TelegramMessengerChatUser
from services.base.base_service import BaseService


class TelethonService(BaseService):
    """Service for managing Telegram client operations."""

    def __init__(self):
        """Initialize TelethonService with dependencies."""
        super().__init__()

    def set_container(self, container: Any):
        """Set container after initialization."""
        self.container = container

    # ===== Public Methods =====

    async def sync_chats(
        self, client: TelegramClient, user_id: str, limit: int = 100, offset: int = 0
    ) -> list[TelegramMessengerChat]:
        """Get user's Telegram chats data without storing.

        Args:
            client: Authenticated TelegramClient instance
            user_id: User ID
            limit: Maximum number of chats to retrieve
            offset: Number of chats to skip

        Returns:
            list of TelegramMessengerChat objects
        """
        chats = []
        dialogs = await client.get_dialogs(limit=limit)
        self.logger.info(f"Found {len(dialogs)} dialogs")
        self.logger.info(f"Dialogs: {dialogs}")
        for dialog in dialogs:
            self.logger.info(f"Dialog: {dialog}")
            chat = await self._create_chat_from_entity(dialog.entity, user_id)
            if chat:
                chats.append(chat)

        return chats

    async def sync_chat(
        self, client: TelegramClient, telegram_id: int, user_id: str
    ) -> Optional[TelegramMessengerChat]:
        """Get chat data from Telegram.

        Args:
            client: Authenticated TelegramClient instance
            telegram_id: Telegram chat ID
            user_id: User ID

        Returns:
            TelegramMessengerChat object or None if failed
        """
        try:
            chat_entity = await client.get_entity(telegram_id)
            return await self._create_chat_from_entity(chat_entity, user_id)

        except Exception as e:
            self.logger.error(f"Error syncing chat {telegram_id}: {e!s}")
            return None

    async def sync_chat_participants(
        self,
        client: TelegramClient,
        chat_id: str,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TelegramMessengerChatUser]:
        """Get participants from a chat.

        Args:
            client: Authenticated TelegramClient instance
            chat_id: Chat ID
            user_id: User ID
            limit: Maximum number of participants to retrieve
            offset: Number of participants to skip

        Returns:
            list of TelegramMessengerChatUser objects
        """
        try:
            participants = []
            chat_entity = await client.get_entity(int(chat_id))

            if isinstance(chat_entity, (TelethonChat, TelethonChannel)):
                # Skip participants up to the offset
                skipped = 0
                async for participant in client.iter_participants(chat_entity):
                    if skipped < offset:
                        skipped += 1
                        continue

                    if not isinstance(participant, TelethonUser):
                        continue

                    # Get join date and remove timezone info if present
                    join_date = getattr(participant.participant, "date", None)
                    if join_date and join_date.tzinfo:
                        join_date = join_date.replace(tzinfo=None)

                    # Create TelegramMessengerChatUser object
                    chat_user = TelegramMessengerChatUser(
                        id=uuid4().hex,
                        telegram_id=participant.id,
                        user_id=user_id,
                        chat_id=str(chat_id),
                        username=participant.username,
                        first_name=participant.first_name,
                        last_name=participant.last_name,
                        phone=participant.phone,
                        is_bot=participant.bot,
                        is_admin=hasattr(participant, "participant")
                        and (
                            getattr(participant.participant, "admin_rights", None)
                            is not None
                            or getattr(participant.participant, "role", "") == "admin"
                        ),
                        is_creator=hasattr(participant, "participant")
                        and getattr(participant.participant, "is_creator", False),
                        join_date=join_date,
                    )
                    participants.append(chat_user)

                    # Stop if we've reached the limit
                    if len(participants) >= limit:
                        break

                return participants
            else:
                self.logger.warning(
                    f"Entity with ID {chat_id} is not a group or channel"
                )
                return []

        except Exception as e:
            self.logger.error(f"Error getting participants for chat {chat_id}: {e!s}")
            raise

    async def sync_chat_messages(
        self,
        client: TelegramClient,
        chat_telegram_id: int,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """Get messages from a specific chat without storing.

        Args:
            client: Authenticated TelegramClient instance
            chat_telegram_id: Chat ID
            limit: Maximum number of messages to retrieve
            offset: Number of messages to skip

        Returns:
            list of message data dictionaries
        """
        try:
            messages_data = []
            chat_entity = await client.get_entity(chat_telegram_id)

            # Get the min_id for pagination
            min_id = 0
            if offset > 0:
                # Get the message at the offset position to use as min_id
                async for message in client.iter_messages(
                    chat_entity, limit=1, offset=offset
                ):
                    if message:
                        min_id = message.id

            async for message in client.iter_messages(
                chat_entity, limit=limit, min_id=min_id
            ):
                if not isinstance(message, TelethonMessage):
                    continue

                message_data = await self.process_message(
                    message, chat_entity, chat_telegram_id
                )
                self.logger.info(f"Message data: {message_data}")
                messages_data.append(message_data)

            return messages_data

        except Exception as e:
            self.logger.error(
                f"Error syncing messages for chat {chat_telegram_id}: {e!s}"
            )
            raise

    async def get_telegram_user(self, client: TelegramClient, telegram_id: int) -> dict:
        """Get Telegram user information by telegram_id.

        Args:
            client: Authenticated TelegramClient instance
            telegram_id: Telegram user ID

        Returns:
            dictionary with user information
        """
        try:
            user = await client.get_entity(telegram_id)
            if not isinstance(user, TelethonUser):
                raise ValueError("Entity is not a user")

            user_data = {
                "telegram_id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone": user.phone,
                "is_bot": user.bot,
                "language_code": getattr(user, "lang_code", None),
            }
            return user_data

        except Exception as e:
            self.logger.error(f"Error getting user {telegram_id}: {e!s}")
            raise

    # ===== Internal Methods =====

    async def _create_chat_from_entity(
        self,
        chat_entity: Union[TelethonUser, TelethonChat, TelethonChannel],
        user_id: str,
    ) -> Optional[TelegramMessengerChat]:
        """Create TelegramMessengerChat from Telethon entity.

        Args:
            chat_entity: Telethon chat entity
            user_id: User ID

        Returns:
            TelegramMessengerChat object or None if entity type is not supported
        """
        try:
            if isinstance(chat_entity, TelethonUser):
                return TelegramMessengerChat(
                    id=uuid4().hex,
                    telegram_id=int(chat_entity.id),
                    user_id=user_id,
                    type=TelegramMessengerChatType.PRIVATE,
                    title=f"{chat_entity.first_name or ''} {chat_entity.last_name or ''}".strip(),
                    member_count=None,
                )

            elif isinstance(chat_entity, TelethonChat):
                return TelegramMessengerChat(
                    id=uuid4().hex,
                    telegram_id=int(chat_entity.id),
                    user_id=user_id,
                    type=TelegramMessengerChatType.GROUP,
                    title=chat_entity.title,
                    member_count=getattr(chat_entity, "participants_count", None),
                )

            elif isinstance(chat_entity, TelethonChannel):
                is_broadcast = getattr(chat_entity, "broadcast", False)
                return TelegramMessengerChat(
                    id=uuid4().hex,
                    telegram_id=int(chat_entity.id),
                    user_id=user_id,
                    type=(
                        TelegramMessengerChatType.CHANNEL
                        if is_broadcast
                        else TelegramMessengerChatType.SUPERGROUP
                    ),
                    title=chat_entity.title,
                    member_count=getattr(chat_entity, "participants_count", None),
                )

            return None
        except Exception as e:
            self.logger.error(f"Error creating chat from entity: {e!s}")
            return None

    async def _get_sender_telegram_id(
        self,
        message: TelethonMessage,
        chat_entity: Union[TelethonUser, TelethonChat, TelethonChannel],
    ) -> Optional[int]:
        """Extract sender telegram ID from message based on chat type."""
        sender_telegram_id = None

        if isinstance(chat_entity, TelethonUser):
            # Private chat
            sender_telegram_id = message.sender_id
            if isinstance(sender_telegram_id, PeerUser):
                sender_telegram_id = sender_telegram_id.user_id

        elif isinstance(chat_entity, TelethonChat):
            # Group chat
            if message.from_id:
                if isinstance(message.from_id, PeerUser):
                    sender_telegram_id = message.from_id.user_id
                elif isinstance(message.from_id, PeerChat):
                    sender_telegram_id = message.from_id.chat_id

        elif isinstance(chat_entity, TelethonChannel):
            # Channel or Supergroup
            if message.from_id:
                if isinstance(message.from_id, PeerUser):
                    sender_telegram_id = message.from_id.user_id
                elif isinstance(message.from_id, PeerChannel):
                    sender_telegram_id = message.from_id.channel_id
            # For anonymous admins or channel posts
            elif message.post:
                sender_telegram_id = chat_entity.id

        return sender_telegram_id

    async def _get_media_info(
        self, message: TelethonMessage
    ) -> tuple[Optional[str], Optional[str]]:
        """Extract media type and file ID from message."""
        media_type = None
        file_id = None

        if message.media:
            if isinstance(message.media, MessageMediaPhoto):
                media_type = "photo"
                file_id = str(message.media.photo.id)
            elif isinstance(message.media, MessageMediaDocument):
                media_type = "document"
                file_id = str(message.media.document.id)

        return media_type, file_id

    async def _get_reply_info(
        self,
        message: TelethonMessage,
        chat_entity: Union[TelethonUser, TelethonChat, TelethonChannel],
    ) -> Optional[int]:
        """Extract reply message ID based on chat type."""
        reply_to_msg_id = None
        if message.reply_to:
            if hasattr(message.reply_to, "reply_to_msg_id"):
                if isinstance(chat_entity, TelethonChannel):
                    # Channels use reply_to_msg_id
                    reply_to_msg_id = message.reply_to.reply_to_msg_id
                else:
                    # Groups and private chats use reply_to_msg_id
                    reply_to_msg_id = message.reply_to.reply_to_msg_id
        return reply_to_msg_id

    def _convert_to_naive_utc(self, dt: Optional[datetime]) -> Optional[datetime]:
        """Convert timezone-aware datetime to naive UTC datetime."""
        if dt and dt.tzinfo is not None:
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt

    async def process_message(
        self,
        message: TelethonMessage,
        chat_entity: Union[TelethonUser, TelethonChat, TelethonChannel],
        chat_telegram_id: int,
    ) -> dict:
        """Process a single message and return its data."""
        sender_telegram_id = await self._get_sender_telegram_id(message, chat_entity)
        media_type, file_id = await self._get_media_info(message)
        reply_to_msg_id = await self._get_reply_info(message, chat_entity)

        # Convert dates to naive UTC
        message_date = self._convert_to_naive_utc(message.date)
        edit_date = self._convert_to_naive_utc(message.edit_date)
        return {
            "message_telegram_id": message.id,
            "chat_telegram_id": chat_telegram_id,
            "sender_telegram_id": sender_telegram_id,
            "message_text": message.message or "",
            "message_date": message_date,
            "edit_date": edit_date,
            "media_type": media_type,
            "file_id": file_id,
            "reply_to_message_telegram_id": reply_to_msg_id,
        }
