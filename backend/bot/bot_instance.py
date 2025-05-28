# bot/bot_instance.py

import asyncio
import logging
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramNetworkError, TelegramRetryAfter
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import ConnectionPool, Redis

from handlers import command_router, main_state_router
from services.dependencies import container

logger = logging.getLogger(__name__)

WEBHOOK_STATUS_KEY = "bot:webhook:status"
WEBHOOK_URL_KEY = "bot:webhook:url"
MAX_RETRIES = 3
RETRY_DELAY = 5


class BotInstance:
    """Telegram bot instance."""

    def __init__(self, token: str, redis_url: str):
        if not token:
            raise ValueError("BOT_TOKEN environment variable is not set")
        logger.info("-------BOT REGISTRATION-------")
        logger.debug("Initializing Telegram bot with token: %s...", token[:10])

        # Initialize Redis connection pool for better performance in multi-process environment
        self.redis_pool = ConnectionPool.from_url(redis_url)
        self.redis = Redis(connection_pool=self.redis_pool)

        # Initialize Redis storage with connection pool
        self.storage = RedisStorage(redis=self.redis)

        # Initialize bot and dispatcher
        self.bot = Bot(token=token)
        self.dp = Dispatcher(storage=self.storage)
        logger.debug("Bot and dispatcher initialized successfully")

        # Initialize dependency container
        container.initialize()
        logger.debug("Dependency container initialized")

        # Register routers
        self._register_routers()

    def _register_routers(self):
        """Register all routers in the dispatcher."""
        routers = [
            command_router,
            main_state_router,
        ]
        for router in routers:
            self.dp.include_router(router)
            logger.debug(f"Router {router.__class__.__name__} registered successfully")

    async def _retry_with_backoff(self, func, *args, **kwargs):
        """Retry a function with exponential backoff."""
        for attempt in range(MAX_RETRIES):
            try:
                return await func(*args, **kwargs)
            except TelegramRetryAfter as e:
                if attempt == MAX_RETRIES - 1:
                    raise
                retry_after = e.retry_after
                logger.warning(f"Rate limited, retrying in {retry_after} seconds...")
                await asyncio.sleep(retry_after)
            except TelegramNetworkError as e:
                if attempt == MAX_RETRIES - 1:
                    raise
                logger.warning(f"Network error, retrying in {RETRY_DELAY} seconds...")
                await asyncio.sleep(RETRY_DELAY)

    async def setup_webhook(self, webhook_url: str, secret_token: Optional[str] = None):
        """Set up webhook for the bot with distributed locking and retries."""
        try:
            # Check if webhook is already set up with the same URL
            current_url = await self.redis.get(WEBHOOK_URL_KEY)
            if current_url and current_url.decode() == webhook_url:
                logger.info("Webhook is already set up with the same URL")
                return

            # Check if webhook is already set up by another process
            current_status = await self.redis.get(WEBHOOK_STATUS_KEY)
            if current_status and current_status.decode() == "active":
                logger.info("Webhook is already active in another process")
                return

            # Set up webhook with retries
            await self._retry_with_backoff(
                self.bot.set_webhook,
                url=webhook_url,
                secret_token=secret_token,
                drop_pending_updates=True,
            )

            # Mark webhook as active in Redis and store the URL
            await self.redis.set(WEBHOOK_STATUS_KEY, "active")
            await self.redis.set(WEBHOOK_URL_KEY, webhook_url)
            logger.info(f"Webhook set up successfully at {webhook_url}")
        except Exception as e:
            logger.error(f"Failed to set up webhook after {MAX_RETRIES} attempts: {e}")
            raise

    async def shutdown(self):
        """Cleanup resources with retries."""
        try:
            # Remove webhook status from Redis
            await self.redis.delete(WEBHOOK_STATUS_KEY)

            # Get current webhook URL
            current_url = await self.redis.get(WEBHOOK_URL_KEY)

            # Only delete webhook if this is the last instance
            if not await self.redis.exists(WEBHOOK_STATUS_KEY):
                try:
                    await self._retry_with_backoff(self.bot.delete_webhook)
                    await self.redis.delete(WEBHOOK_URL_KEY)
                    logger.info("Webhook deleted successfully")
                except Exception as e:
                    logger.warning(f"Failed to delete webhook during shutdown: {e}")

            # Close connections with timeout
            try:
                # Try to close bot with a short timeout
                await asyncio.wait_for(self.bot.close(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning(
                    "Bot close operation timed out, proceeding with shutdown"
                )
            except Exception as e:
                logger.warning(f"Failed to close bot during shutdown: {e}")

            try:
                await self.storage.close()
            except Exception as e:
                logger.warning(f"Failed to close storage during shutdown: {e}")

            try:
                await self.redis.close()
                await self.redis_pool.disconnect()
            except Exception as e:
                logger.warning(f"Failed to close Redis during shutdown: {e}")

            logger.info("Bot and storage closed successfully")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            raise
