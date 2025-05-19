"""
This module is the entry point for the FastAPI application.
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from aiogram.types import Update
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from bot.bot_instance import WEBHOOK_STATUS_KEY, BotInstance
from config import REDIS_URL, TELEGRAM_BOT_TOKEN
from middleware.auth import AuthMiddleware
from routes import admin_router, miniapp_router
from services.dependencies import container
from services.external.telegram_bot_service import TelegramBotService
from services.external.telethon_client import TelethonClient
from services.external.telethon_service import TelethonService

IS_DEVELOP = (
    os.getenv("IS_DEVELOP", "true").lower() == "true"
)  # Default to true for development
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://turboapp-app.ptel.brainex.co")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://your-domain.com/webhook")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

# Настройка CORS
origins: list[str] = [
    FRONTEND_URL,
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "https://testbot.zeenevents.com",
    "https://app.doublekiss.zeenevents.ru",
    "https://admin.doublekiss.zeenevents.ru",
    "https://turboapp-app.ptel.brainex.co",
]

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_STARTUP_RETRIES = 5
STARTUP_RETRY_DELAY = 10


async def initialize_services(app: FastAPI):
    """Initialize all application services with retries."""
    for attempt in range(MAX_STARTUP_RETRIES):
        try:
            # Initialize bot and services
            bot_instance = BotInstance(token=TELEGRAM_BOT_TOKEN, redis_url=REDIS_URL)
            telegram_bot_service = TelegramBotService(bot_instance.bot)

            # Initialize Telethon services
            telethon_client = container.resolve(TelethonClient)
            telethon_service = container.resolve(TelethonService)

            # Store services in application state
            app.state.bot_instance = bot_instance
            app.state.telegram_bot_service = telegram_bot_service
            app.state.telethon_client = telethon_client
            app.state.telethon_service = telethon_service

            # Initialize repositories and services
            for repository_class in container.get_registered_repositories():
                container.resolve(repository_class)

            # Set up webhook only if it's not already active
            current_status = await bot_instance.redis.get(WEBHOOK_STATUS_KEY)
            if not current_status or current_status.decode() != "active":
                await bot_instance.setup_webhook(
                    webhook_url=WEBHOOK_URL, secret_token=WEBHOOK_SECRET
                )

            return bot_instance

        except Exception as e:
            if attempt == MAX_STARTUP_RETRIES - 1:
                logger.error(
                    f"Failed to initialize services after {MAX_STARTUP_RETRIES} attempts: {e}"
                )
                raise
            logger.warning(
                f"Failed to initialize services (attempt {attempt + 1}/{MAX_STARTUP_RETRIES}): {e}"
            )
            await asyncio.sleep(STARTUP_RETRY_DELAY)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for the FastAPI application.
    Handles startup and shutdown events.
    """
    bot_instance = None
    try:
        bot_instance = await initialize_services(app)
        yield

    finally:
        if bot_instance:
            try:
                await bot_instance.shutdown()
                # Disconnect all Telethon clients
                telethon_client = app.state.telethon_client
                if telethon_client:
                    await telethon_client.disconnect_all()
            except Exception as e:
                logger.error(f"Error during services shutdown: {e}")
        logger.info("Application shutdown complete")


# Создание FastAPI приложения
app = FastAPI(
    title="DoubleKiss BOT + API",
    description="Backend API for DoubleKiss BOT",
    version="1.0.0",
    lifespan=lifespan,
)

# Настройка CORS - должна быть первым middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Остальные middleware
if not IS_DEVELOP:
    app.add_middleware(HTTPSRedirectMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")


# Webhook endpoint
@app.post("/webhook")
async def webhook(request: Request):
    """Handle incoming webhook updates from Telegram."""
    bot_instance: BotInstance = request.app.state.bot_instance

    # Verify webhook secret if provided
    if WEBHOOK_SECRET:
        secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if secret_token != WEBHOOK_SECRET:
            raise HTTPException(status_code=403, detail="Invalid secret token")

    try:
        # Get raw update data
        update_data = await request.json()

        # Parse update data into Update object
        update = Update.model_validate(update_data)

        # Process update
        await bot_instance.dp.feed_update(bot_instance.bot, update)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Error processing webhook update: {e}")
        raise HTTPException(status_code=500, detail="Error processing update") from e


# Подключаем роутеры
app.include_router(miniapp_router)
app.include_router(admin_router)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_delay=1,
        proxy_headers=True,
    )
