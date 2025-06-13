import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4

from telethon import TelegramClient, events
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
    Production-ready Telegram service with proper client lifecycle management.
    
    This service follows the proven pattern from the working project:
    - Proper connection pooling and lifecycle management
    - Event-driven message handling
    - Real-time streaming capabilities
    - Scalable client management
    """

    def __init__(self, connection_repo: TelegramConnectionRepository, container=None):
        super().__init__()
        self.connection_repo = connection_repo
        self.encryption_service = get_encryption_service()
        self.container = container
        
        # Production-ready client management
        self._clients: Dict[str, TelegramClient] = {}
        self._client_locks: Dict[str, asyncio.Lock] = {}
        self._flood_wait_state: Dict[str, Dict] = {}
        self._event_handlers_setup: Dict[str, bool] = {}

    # --- Production Client Management ---

    async def has_client(self, user_id: str) -> Optional[TelegramClient]:
        """Check if client exists and is valid without creating a new one."""
        client = self._clients.get(user_id)
        if client:
            try:
                if not client.is_connected():
                    await client.connect()
                if await client.is_user_authorized():
                    return client
                else:
                    # Remove invalid client
                    await self._remove_client(user_id)
            except Exception as e:
                self.logger.error(f"Error checking client status for user {user_id}: {e}")
                await self._remove_client(user_id)
        return None

    async def get_or_create_client(self, user_id: str) -> Optional[TelegramClient]:
        """
        Get existing client or create new one with proper lifecycle management.
        This is the main method for production client access.
        """
        lock = await self._get_client_lock(user_id)
        async with lock:
            # Check if client exists and is connected
            client = await self.has_client(user_id)
            if client:
                return client

            # Get user connection from database
            connection = await self.connection_repo.get_by_user_id(user_id)
            if not connection or not connection.session_string_encrypted:
                self.logger.warning(f"No valid Telegram connection found for user {user_id}")
                return None

            # Create new client
            client = await self._create_client(user_id, connection.session_string_encrypted)
            if client:
                self._clients[user_id] = client
                # Set up event handlers for real-time processing
                await self._setup_event_handlers(client, user_id)
                return client

            return None

    async def _create_client(self, user_id: str, encrypted_session: str) -> Optional[TelegramClient]:
        """Create and setup a new Telegram client."""
        try:
            # Decrypt session string
            session_string = self.encryption_service.decrypt_session_string(encrypted_session)

            # Create new client with session string
            client = TelegramClient(
                StringSession(session_string),
                int(settings.TELETHON_API_ID),
                settings.TELETHON_API_HASH,
                device_model="Karma App",
                system_version="1.0",
                app_version="1.0",
            )

            # Connect and verify authorization
            await client.connect()
            if not await client.is_user_authorized():
                self.logger.error(f"Session for user {user_id} is invalid or expired")
                await client.disconnect()
                return None

            self.logger.info(f"Successfully created Telethon client for user {user_id}")
            return client

        except Exception as e:
            self.logger.error(f"Error creating client for user {user_id}: {e}", exc_info=True)
            if 'client' in locals() and client.is_connected():
                await client.disconnect()
            return None

    async def _setup_event_handlers(self, client: TelegramClient, user_id: str):
        """
        Setup real-time event handlers for incoming messages.
        This enables real-time streaming of new messages.
        """
        if self._event_handlers_setup.get(user_id):
            return  # Already setup

        @client.on(events.NewMessage)
        async def handle_new_message(event):
            try:
                self.logger.info(f"📨 New message received for user {user_id}")
                # TODO: Process new message and send WebSocket notification
                # This will be implemented when we add WebSocket service
                
                # For now, just log the message
                if event.message.text:
                    self.logger.info(f"Message text: {event.message.text[:100]}...")
                    
            except Exception as e:
                self.logger.error(f"Error handling new message for user {user_id}: {e}")

        self._event_handlers_setup[user_id] = True
        self.logger.info(f"✅ Event handlers setup for user {user_id}")

    async def disconnect_client(self, user_id: str):
        """Disconnect and remove client from pool."""
        await self._remove_client(user_id)

    async def _remove_client(self, user_id: str):
        """Remove client from pool and clean up."""
        if user_id in self._clients:
            try:
                client = self._clients[user_id]
                if client.is_connected():
                    await client.disconnect()
                self.logger.info(f"Disconnected client for user {user_id}")
            except Exception as e:
                self.logger.error(f"Error disconnecting client for user {user_id}: {e}")
            finally:
                self._clients.pop(user_id, None)
                self._event_handlers_setup.pop(user_id, None)

    async def disconnect_all_clients(self):
        """Disconnect all clients - called during application shutdown."""
        for user_id in list(self._clients.keys()):
            await self._remove_client(user_id)
        self.logger.info("🔌 All Telegram clients disconnected")

    async def _get_client_lock(self, user_id: str) -> asyncio.Lock:
        """Get or create a lock for client operations."""
        if user_id not in self._client_locks:
            self._client_locks[user_id] = asyncio.Lock()
        return self._client_locks[user_id]

    # --- Flood Control (Production Ready) ---

    async def _handle_flood_wait(self, client_key: str, error: FloodWaitError):
        """Handle FloodWaitError with exponential backoff."""
        wait_time = error.seconds
        self.logger.warning(f"⚠️ FloodWaitError for client {client_key}: waiting {wait_time} seconds")

        # Mark client as in cooldown
        self._flood_wait_state[client_key] = {
            "cooldown_until": datetime.now().timestamp() + wait_time,
            "wait_seconds": wait_time,
        }

        await asyncio.sleep(wait_time + 1)  # Add 1 second buffer

        # Clear cooldown state
        self._flood_wait_state.pop(client_key, None)

    def _is_client_in_cooldown(self, client_key: str) -> bool:
        """Check if client is currently in cooldown."""
        if client_key not in self._flood_wait_state:
            return False
        cooldown_until = self._flood_wait_state[client_key]["cooldown_until"]
        return datetime.now().timestamp() < cooldown_until

    async def _safe_api_call(self, client_key: str, api_call_func, *args, **kwargs):
        """Execute API call with flood wait handling."""
        if self._is_client_in_cooldown(client_key):
            remaining = (
                self._flood_wait_state[client_key]["cooldown_until"]
                - datetime.now().timestamp()
            )
            self.logger.info(f"Client {client_key} in cooldown for {remaining:.1f}s")
            await asyncio.sleep(remaining + 1)

        try:
            return await api_call_func(*args, **kwargs)
        except FloodWaitError as e:
            await self._handle_flood_wait(client_key, e)
            # Retry once after waiting
            return await api_call_func(*args, **kwargs)

    # --- High-level API methods (Production Ready) ---

    async def get_user_chats(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get user's Telegram chats with production-ready error handling.
        
        Returns a list of chat dictionaries suitable for API responses.
        """
        client = await self.get_or_create_client(user_id)
        if not client:
            self.logger.warning(f"Could not get Telegram client for user {user_id}")
            return []

        try:
            # Use get_dialogs for efficient chat fetching (not iter_dialogs)
            dialogs = await self._safe_api_call(
                user_id, 
                client.get_dialogs,
                limit=limit
            )
            
            self.logger.info(f"📋 Found {len(dialogs)} dialogs for user {user_id}")
            
            chats = []
            for dialog in dialogs:
                try:
                    chat_data = await self._create_chat_dict_from_entity(dialog.entity, user_id)
                    if chat_data:
                        chats.append(chat_data)
                except Exception as e:
                    self.logger.error(f"Error processing dialog entity: {e}")
                    continue
                    
            self.logger.info(f"✅ Processed {len(chats)} valid chats for user {user_id}")
            return chats
            
        except Exception as e:
            self.logger.error(f"❌ Error fetching chats for user {user_id}: {e}", exc_info=True)
            return []

    async def _create_chat_dict_from_entity(
        self,
        chat_entity: Union[TelethonUser, TelethonChat, TelethonChannel],
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Create chat dictionary from Telethon entity.
        Returns structure compatible with frontend expectations.
        """
        try:
            chat_data = {
                "telegram_id": int(chat_entity.id),
                "user_id": user_id,
                "title": "",
                "type": "",
                "member_count": None,
                "username": getattr(chat_entity, "username", None),
            }
            
            if isinstance(chat_entity, TelethonUser):
                full_name = f"{chat_entity.first_name or ''} {chat_entity.last_name or ''}".strip()
                chat_data.update({
                    "type": "private",
                    "title": full_name or "Unknown User",
                })
                
            elif isinstance(chat_entity, TelethonChat):
                chat_data.update({
                    "type": "group", 
                    "title": chat_entity.title or "Unnamed Group",
                    "member_count": getattr(chat_entity, "participants_count", None),
                })
                
            elif isinstance(chat_entity, TelethonChannel):
                is_broadcast = getattr(chat_entity, "broadcast", False)
                chat_data.update({
                    "type": "channel" if is_broadcast else "supergroup",
                    "title": chat_entity.title or "Unnamed Channel",
                    "member_count": getattr(chat_entity, "participants_count", None),
                })
            else:
                self.logger.warning(f"Unknown entity type: {type(chat_entity)}")
                return None
                
            return chat_data
            
        except Exception as e:
            self.logger.error(f"Error creating chat dict from entity: {e}")
            return None

    # --- Legacy methods (keeping for backward compatibility) ---

    async def get_client(self, user_id: str) -> Optional[TelegramClient]:
        """Legacy method - use get_or_create_client instead."""
        return await self.get_or_create_client(user_id)

    async def get_user_sent_messages(
        self, user_id: str, limit: int = 200
    ) -> list[dict]:
        """
        Fetch user's own sent messages from DMs and group chats for style analysis.
        """
        client = await self.get_or_create_client(user_id)
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

    def _convert_to_naive_utc(self, dt: Optional[datetime]) -> Optional[datetime]:
        """Convert timezone-aware datetime to naive UTC datetime."""
        if dt and dt.tzinfo is not None:
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt 