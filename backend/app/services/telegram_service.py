import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4

from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.sessions import StringSession
from telethon.tl.types import Channel as TelethonChannel
from telethon.tl.types import Chat as TelethonChat
from telethon.tl.types import Message as TelethonMessage
from telethon.tl.types import (
    MessageMediaDocument,
    MessageMediaPhoto,
    PeerChannel,
    PeerChat,
    PeerUser,
)
from telethon.tl.types import User as TelethonUser

from app.core.config import settings
from app.core.security import get_encryption_service
from app.models.chat import TelegramMessengerChat, TelegramMessengerChatType
from app.repositories.telegram_connection_repository import (
    TelegramConnectionRepository,
)
from app.services.base_service import BaseService


class TelegramService(BaseService):
    """
    A consolidated service for all Telethon interactions.
    Manages client lifecycle and provides high-level methods for API calls.
    """

    def __init__(self, connection_repo: TelegramConnectionRepository):
        super().__init__()
        self.connection_repo = connection_repo
        # The encryption service is now retrieved from a function, not injected.
        # This is based on the existing code in telegram_service.py
        self.encryption_service = get_encryption_service()
        self._clients: Dict[str, TelegramClient] = {}
        self._client_locks: Dict[str, asyncio.Lock] = {}
        self._flood_wait_state: Dict[str, Dict] = {}

    # --- Client Management ---

    async def get_client(self, user_id: str) -> Optional[TelegramClient]:
        """
        Get an authenticated Telethon client for a user.
        Uses an in-memory cache for active clients. This method is thread-safe.
        """
        lock = await self._get_client_lock(user_id)
        async with lock:
            if user_id in self._clients:
                client = self._clients[user_id]
                if client.is_connected():
                    try:
                        if await client.is_user_authorized():
                            return client
                    except Exception:
                        self.logger.warning(f"Client for user {user_id} is no longer authorized. Reconnecting.")

                await self.disconnect_client(user_id, acquire_lock=False)

            connection = await self.connection_repo.get_by_user_id(user_id)
            if not connection or not connection.session_string_encrypted:
                self.logger.warning(f"No valid Telegram connection found for user {user_id}")
                return None

            try:
                session_string = self.encryption_service.decrypt_session_string(
                    connection.session_string_encrypted
                )

                client = TelegramClient(
                    StringSession(session_string),
                    int(settings.TELETHON_API_ID),
                    settings.TELETHON_API_HASH,
                    device_model="Karma App",
                    system_version="1.0",
                    app_version="1.0",
                )
                await client.connect()

                if not await client.is_user_authorized():
                    self.logger.error(f"Session for user {user_id} is invalid or expired.")
                    await client.disconnect()
                    return None

                self._clients[user_id] = client
                return client
            except Exception as e:
                self.logger.error(f"Failed to create Telethon client for user {user_id}: {e}", exc_info=True)
                return None

    async def _get_client_lock(self, user_id: str) -> asyncio.Lock:
        if user_id not in self._client_locks:
            self._client_locks[user_id] = asyncio.Lock()
        return self._client_locks[user_id]

    async def disconnect_client(self, user_id: str, acquire_lock: bool = True):
        """Disconnect and remove a client from the cache."""
        if user_id in self._clients:
            client = self._clients.pop(user_id)
            if client.is_connected():
                await client.disconnect()
            self.logger.info(f"Disconnected client for user {user_id}")

    # --- Flood Control ---

    async def _handle_flood_wait(self, client_key: str, error: FloodWaitError):
        """Handle FloodWaitError globally for a client."""
        wait_time = error.seconds
        self.logger.warning(
            f"FloodWaitError for client {client_key}: waiting {wait_time} seconds"
        )

        # Mark client as in cooldown
        self._flood_wait_state[client_key] = {
            "cooldown_until": datetime.now().timestamp() + wait_time,
            "wait_seconds": wait_time,
        }

        await asyncio.sleep(wait_time + 1)  # Add 1 second buffer

        # Clear cooldown state
        if client_key in self._flood_wait_state:
            del self._flood_wait_state[client_key]

    def _is_client_in_cooldown(self, client_key: str) -> bool:
        """Check if client is currently in cooldown."""
        if client_key not in self._flood_wait_state:
            return False

        cooldown_until = self._flood_wait_state[client_key]["cooldown_until"]
        return datetime.now().timestamp() < cooldown_until

    async def _safe_api_call(self, client_key: str, api_call_func, *args, **kwargs):
        """Safely execute an API call with flood wait handling."""
        if self._is_client_in_cooldown(client_key):
            remaining = (
                self._flood_wait_state[client_key]["cooldown_until"]
                - datetime.now().timestamp()
            )
            self.logger.info(
                f"Client {client_key} still in cooldown for {remaining:.1f} seconds"
            )
            await asyncio.sleep(remaining + 1)

        try:
            return await api_call_func(*args, **kwargs)
        except FloodWaitError as e:
            await self._handle_flood_wait(client_key, e)
            # Retry once after waiting
            return await api_call_func(*args, **kwargs)

    # --- High-level API methods ---

    async def get_user_sent_messages(
        self, user_id: str, limit: int = 200
    ) -> list[dict]:
        """
        Fetch user's own sent messages from DMs and group chats for style analysis.
        """
        client = await self.get_client(user_id)
        if not client:
            return []

        messages = []
        try:
            # iter_dialogs can be slow, so we limit it.
            # We also fetch more messages from recent chats.
            async for dialog in client.iter_dialogs(limit=50):
                if dialog.is_user or dialog.is_group:
                    # from_user='me' is an efficient way to get sent messages
                    async for message in client.iter_messages(
                        dialog, from_user="me", limit=100
                    ):
                        if message and message.text:
                            messages.append(
                                {
                                    "text": message.text,
                                    "date": self._convert_to_naive_utc(message.date),
                                }
                            )
                        if len(messages) >= limit:
                            break
                if len(messages) >= limit:
                    break
        except Exception as e:
            self.logger.error(
                f"Error fetching user sent messages for user {user_id}: {e}",
                exc_info=True,
            )

        # Sort by date descending to get the most recent messages
        messages.sort(key=lambda x: x.get("date", datetime.min), reverse=True)

        return messages[:limit]

    # --- Internal Helper Methods ---

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
            # Дополнительные проверки для безопасности
            if chat_entity is None:
                self.logger.warning(f"User {user_id}: chat_entity is None")
                return None

            if not hasattr(chat_entity, "id") or chat_entity.id is None:
                self.logger.warning(
                    f"User {user_id}: chat_entity has no valid ID: {type(chat_entity)}"
                )
                return None

            self.logger.debug(
                f"User {user_id}: Processing entity: {chat_entity}, type: {type(chat_entity)}, id: {getattr(chat_entity, 'id', 'N/A')}"
            )

            if isinstance(chat_entity, TelethonUser):
                first_name = getattr(chat_entity, "first_name", "") or ""
                last_name = getattr(chat_entity, "last_name", "") or ""
                title = f"{first_name} {last_name}".strip()
                if not title:
                    # Если нет имени, используем username или "Unknown User"
                    title = getattr(chat_entity, "username", "") or "Unknown User"

                return TelegramMessengerChat(
                    id=uuid4().hex,
                    telegram_id=int(chat_entity.id),
                    user_id=user_id,
                    type=TelegramMessengerChatType.PRIVATE,
                    title=title,
                    member_count=None,
                )

            elif isinstance(chat_entity, TelethonChat):
                title = getattr(chat_entity, "title", "") or "Unknown Group"
                return TelegramMessengerChat(
                    id=uuid4().hex,
                    telegram_id=int(chat_entity.id),
                    user_id=user_id,
                    type=TelegramMessengerChatType.GROUP,
                    title=title,
                    member_count=getattr(chat_entity, "participants_count", None),
                )

            elif isinstance(chat_entity, TelethonChannel):
                is_broadcast = getattr(chat_entity, "broadcast", False)
                title = getattr(chat_entity, "title", "") or "Unknown Channel"
                return TelegramMessengerChat(
                    id=uuid4().hex,
                    telegram_id=int(chat_entity.id),
                    user_id=user_id,
                    type=(
                        TelegramMessengerChatType.CHANNEL
                        if is_broadcast
                        else TelegramMessengerChatType.SUPERGROUP
                    ),
                    title=title,
                    member_count=getattr(chat_entity, "participants_count", None),
                )
            else:
                self.logger.warning(
                    f"User {user_id}: Unsupported entity type: {type(chat_entity)}"
                )

            return None
        except Exception as e:
            self.logger.error(
                f"User {user_id}: Error creating chat from entity {type(chat_entity)}: {e!s}",
                exc_info=True,
            )
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

    def _convert_to_naive_utc(self, dt: Optional[datetime]) -> Optional[datetime]:
        """Convert timezone-aware datetime to naive UTC datetime."""
        if dt and dt.tzinfo is not None:
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt 