# services/external/telegram_bot_service.py

import asyncio
import logging
from typing import Optional

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message

from app.core.config import settings
# from app.core.dependencies import container  # Avoid circular import
from app.schemas.user import UserCreate
from app.services.base_service import BaseService

logger = logging.getLogger(__name__)


class TelegramBotService(BaseService):
    """Service for interacting with the Telegram bot and handling user commands."""

    def __init__(self):
        super().__init__()
        if (
            not settings.TELEGRAM_BOT_TOKEN
            or settings.TELEGRAM_BOT_TOKEN == "dummy-token-for-development"
        ):
            self.bot = None
            self.dp = None
            logger.warning(
                "TELEGRAM_BOT_TOKEN is not configured. TelegramBotService will be disabled."
            )
        else:
            self.bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
            self.storage = MemoryStorage()
            self.dp = Dispatcher(storage=self.storage)
            self._register_handlers()

        self._task = None

    def _register_handlers(self):
        """Register all command and message handlers for the bot."""
        if not self.dp:
            return

        @self.dp.message(CommandStart())
        async def cmd_start(message: Message, state: FSMContext):
            """Handles the /start command, creating a user if one doesn't exist."""
            try:
                # For now, we'll just send a simple welcome message
                # User creation can be handled by the frontend app
                await message.answer(
                    "Welcome to Karma App! 🎯\n\n"
                    "This bot is for notifications and updates. "
                    "Please use the web application for all features.\n\n"
                    "Web App: http://localhost:3000"
                )
            except Exception as e:
                logger.error(
                    f"Error in /start command for user {message.from_user.id}: {e}",
                    exc_info=True,
                )
                await message.answer("Sorry, something went wrong. Please try again later.")

        @self.dp.message(F.text)
        async def handle_text_message(message: Message):
            """Handles any other text messages sent to the bot."""
            try:
                await message.reply(
                    "This bot is for notifications and initial setup. "
                    "Please use the web application for all features."
                )
            except Exception as e:
                logger.error(
                    f"Error handling text message from {message.from_user.id}: {e}",
                    exc_info=True,
                )

    async def send_message(
        self, chat_id: int, text: str, parse_mode: Optional[str] = None
    ):
        """Sends a message to a specific chat ID."""
        if not self.bot:
            logger.warning(
                f"Attempted to send message to {chat_id}, but bot is disabled."
            )
            return

        try:
            await self.bot.send_message(
                chat_id=chat_id, text=text, parse_mode=parse_mode
            )
        except Exception as e:
            logger.error(f"Failed to send message to {chat_id}: {e}", exc_info=True)

    async def start_polling(self):
        """Starts the bot's polling mechanism in the background."""
        if not self.dp or not self.bot:
            logger.info("Telegram bot is disabled. Skipping polling.")
            return

        if self._task:
            logger.warning("Bot is already running.")
            return

        logger.info("Starting Telegram bot polling...")
        self._task = asyncio.create_task(self.dp.start_polling(self.bot))

    async def stop_polling(self):
        """Stops the bot's polling mechanism gracefully."""
        if self._task and not self._task.done():
            logger.info("Stopping Telegram bot polling...")
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                logger.info("Bot polling stopped.")
        if self.bot:
            await self.bot.session.close()
