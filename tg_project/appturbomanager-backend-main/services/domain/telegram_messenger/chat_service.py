"""Service for Telegram Messenger chat operations."""

from typing import Any, Optional

from models.telegram_messenger.chat import TelegramMessengerChat
from services.base.base_service import BaseService
from services.external.telethon_service import TelethonService
from services.repositories.telegram.chat_repository import ChatRepository


class TelegramMessengerChatService(BaseService):
    """Service class for Telegram Messenger chat operations."""

    def __init__(
        self,
        telethon_service: TelethonService,
        chat_repository: ChatRepository,
    ):
        """Initialize the service with required dependencies."""
        super().__init__()
        self.telethon_service = telethon_service
        self.chat_repository = chat_repository

    async def get_chats(
        self, client: Any, user_id: str, limit: int = 10, offset: int = 0
    ) -> list[TelegramMessengerChat]:
        """Get user's Telegram chats.

        Args:
            client: Authenticated TelegramClient instance
            user_id: User ID
            limit: Maximum number of chats to retrieve
            offset: Number of chats to skip

        Returns:
            list of TelegramMessengerChat objects
        """
        chats = await self.telethon_service.sync_chats(
            client=client,
            user_id=user_id,
            limit=limit,
            offset=offset,
        )
        if chats:
            return await self.chat_repository.create_or_update_chats(chats)
        return chats

    async def get_chat(
        self, client: Any, telegram_id: int, user_id: str
    ) -> Optional[TelegramMessengerChat]:
        """Get specific chat data from Telegram.

        Args:
            client: Authenticated TelegramClient instance
            telegram_id: Telegram chat ID
            user_id: User ID

        Returns:
            TelegramMessengerChat object or None if failed
        """
        # First try to get chat from database
        chat = await self.chat_repository.get_chat_by_telegram_id(telegram_id, user_id)
        if chat:
            return chat

        # If not found in database, sync from Telegram
        chat = await self.telethon_service.sync_chat(
            client=client,
            telegram_id=telegram_id,
            user_id=user_id,
        )
        if not chat:
            self.logger.warning(f"Failed to sync chat {telegram_id} from Telegram")
            return None

        # Store the synced chat in the database
        saved_chats = await self.chat_repository.create_or_update_chats([chat])
        if not saved_chats:
            self.logger.warning(f"Failed to save chat {telegram_id} to database")
            return None

        return saved_chats[0]
