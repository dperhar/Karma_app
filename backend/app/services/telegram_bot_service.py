# services/external/telegram_bot_service.py

import logging
from typing import Optional, Union

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.types import Chat, InlineKeyboardMarkup, Message, ReplyKeyboardMarkup

from app.services.base_service import BaseService

logger = logging.getLogger(__name__)


class TelegramBotService(BaseService):
    """Service for interacting with Telegram bot."""

    def __init__(self, bot_instance: Bot):
        """Initialize TelegramBotService with bot instance."""
        super().__init__()
        self.bot = bot_instance

    async def edit_message(
        self, chat_id: int, message_id: int, text: str, parse_mode: Optional[str] = None
    ) -> Optional[Message]:
        """Edit a message in Telegram."""
        try:
            return await self.bot.edit_message_text(
                chat_id=chat_id, message_id=message_id, text=text, parse_mode=parse_mode
            )
        except (TelegramAPIError, TelegramBadRequest) as e:
            self.logger.error("Telegram error while editing message: %s", e)
            return None

    async def send_message(
        self, chat_id: int, text: str, parse_mode: Optional[str] = None
    ) -> Optional[Message]:
        """Send a new message in Telegram.

        Args:
            chat_id: Telegram chat ID.
            text: Text message to send.
            parse_mode: Text parsing mode (None, 'HTML', or 'MarkdownV2').
        """
        try:
            return await self.bot.send_message(
                chat_id=chat_id, text=text, parse_mode=parse_mode
            )
        except (TelegramAPIError, TelegramBadRequest) as e:
            self.logger.error("Telegram error while sending message: %s", e)
            return None

    async def send_message_with_markup(
        self,
        chat_id: int,
        text: str,
        reply_markup: Optional[Union[InlineKeyboardMarkup, ReplyKeyboardMarkup]] = None,
        parse_mode: Optional[str] = None,
    ) -> Optional[Message]:
        """Send a new message with reply markup in Telegram."""
        try:
            return await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
        except (TelegramAPIError, TelegramBadRequest) as e:
            self.logger.error("Telegram error while sending message with markup: %s", e)
            return None

    async def delete_message(self, chat_id: int, message_id: int) -> bool:
        """Delete a message from Telegram."""
        try:
            await self.bot.delete_message(chat_id=chat_id, message_id=message_id)
            return True
        except (TelegramAPIError, TelegramBadRequest) as e:
            self.logger.error("Telegram error while deleting message: %s", e)
            return False

    async def reply_to_message(
        self,
        message: Message,
        text: str,
        reply_markup: Optional[Union[InlineKeyboardMarkup, ReplyKeyboardMarkup]] = None,
        parse_mode: Optional[str] = None,
    ) -> Optional[Message]:
        """Reply to a message in Telegram."""
        try:
            return await message.reply(
                text=text, reply_markup=reply_markup, parse_mode=parse_mode
            )
        except (TelegramAPIError, TelegramBadRequest) as e:
            self.logger.error("Telegram error while replying to message: %s", e)
            return None

    async def edit_message_reply_markup(
        self,
        chat_id: int,
        message_id: int,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
    ) -> bool:
        """Edit message's reply markup."""
        try:
            await self.bot.edit_message_reply_markup(
                chat_id=chat_id, message_id=message_id, reply_markup=reply_markup
            )
            return True
        except (TelegramAPIError, TelegramBadRequest) as e:
            self.logger.error("Telegram error while editing message markup: %s", e)
            return False

    async def get_chat(self, chat_id: int) -> tuple[Optional[Chat], Optional[int]]:
        """Get chat information by its ID.

        Args:
            chat_id: Telegram chat ID.

        Returns:
            Tuple containing:
            - Chat object if successful, None otherwise
            - Permanent chat ID if successful, None otherwise
        """
        try:
            # First try to get the chat directly
            self.logger.info(f"Chat ID----: {chat_id}")
            chat = await self.bot.get_chat(chat_id)
            if chat:
                self.logger.info(f"Chat: {chat}")
                self.logger.info(f"Chat ID: {chat.id}")
                return chat, chat.id
            self.logger.info("NO CHAT")
            return None, None

        except (TelegramAPIError, TelegramBadRequest) as e:
            self.logger.error("Telegram error while getting chat info: %s", e)
            return None, None
