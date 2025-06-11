import asyncio
import logging
from typing import Any, Dict, Optional

from telethon import TelegramClient
from telethon.sessions import StringSession

from app.core.config import settings
from app.repositories.telegram_connection_repository import (
    TelegramConnectionRepository,
)
from app.services.base_service import BaseService
from app.services.encryption_service import get_encryption_service

logger = logging.getLogger(__name__)


class TelegramService(BaseService):
    """
    A simplified and consolidated service for all Telethon interactions.
    Manages client lifecycle and provides methods for API calls.
    """

    def __init__(self, connection_repo: TelegramConnectionRepository):
        super().__init__()
        self.connection_repo = connection_repo
        self.encryption_service = get_encryption_service()
        self._clients: Dict[str, TelegramClient] = {}
        self._client_locks: Dict[str, asyncio.Lock] = {}

    async def _get_client_lock(self, user_id: str) -> asyncio.Lock:
        if user_id not in self._client_locks:
            self._client_locks[user_id] = asyncio.Lock()
        return self._client_locks[user_id]

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
                session_string = self.encryption_service.decrypt_session_string(connection.session_string_encrypted)

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

    async def disconnect_client(self, user_id: str, acquire_lock: bool = True):
        """Disconnect and remove a client from the cache."""
        if user_id in self._clients:
            client = self._clients.pop(user_id)
            if client.is_connected():
                await client.disconnect()
            self.logger.info(f"Disconnected client for user {user_id}") 