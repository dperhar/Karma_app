"""
This module is the entry point for the FastAPI application.
Comment Management System - работает через пользовательские аккаунты Telegram.
"""

import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from middleware.auth import AuthenticationMiddleware
from app.api.admin import router as admin_router
from app.api.v1.router import api_router
from app.core.dependencies import container
from app.services.data_fetching_service import DataFetchingService
from app.services.draft_generation_service import DraftGenerationService
from app.services.scheduler_service import SchedulerService
from app.services.telegram_bot_service import TelegramBotService

# Assuming settings are loaded via app.core.config
from app.core.config import settings
from app.db.session import engine # For Alembic, if tables are created here
# from app.db.base import Base # If creating tables directly without Alembic

IS_DEVELOP = (
    os.getenv("IS_DEVELOP", "true").lower() == "true"
)  # Default to true for development
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# Настройка CORS
origins: list[str] = [
    FRONTEND_URL,
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "null",  # For file:// protocol
]

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def initialize_services(app: FastAPI):
    """Initialize services for Comment Management System."""
    try:
        # Initialize repositories and services - punq handles dependency resolution automatically
        
        # Initialize data fetching service and scheduler
        data_fetching_service = container.resolve(DataFetchingService)
        draft_generation_service = container.resolve(DraftGenerationService)
        scheduler_service = SchedulerService()
        
        # Store scheduler in application state for cleanup
        app.state.scheduler_service = scheduler_service
        
        # Initialize and start the Telegram bot
        telegram_bot_service = container.resolve(TelegramBotService)
        app.state.telegram_bot_service = telegram_bot_service
        await telegram_bot_service.start_polling()
        logger.info("Telegram bot service initialized and started.")
        
        # Start periodic data fetching task
        await scheduler_service.start_periodic_task(
            task_func=data_fetching_service.fetch_new_data_for_all_users,
            min_interval_minutes=30,
            max_interval_minutes=240,
            task_name="telegram_data_fetch"
        )
        
        # Start periodic draft generation task
        draft_scheduler = SchedulerService()
        app.state.draft_scheduler = draft_scheduler
        await draft_scheduler.start_periodic_task(
            task_func=draft_generation_service.check_for_new_posts,
            min_interval_minutes=15,  # Check more frequently for drafts
            max_interval_minutes=60,
            task_name="draft_generation"
        )
        
        logger.info("Comment Management System services initialized successfully")
        logger.info("Automated data fetching scheduler started")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for the FastAPI application.
    Handles startup and shutdown events.
    """
    try:
        await initialize_services(app)
        yield
    finally:
        # Stop scheduler
        try:
            scheduler_service = getattr(app.state, 'scheduler_service', None)
            if scheduler_service:
                await scheduler_service.stop()
                logger.info("Data fetching scheduler stopped")
                
            draft_scheduler = getattr(app.state, 'draft_scheduler', None)
            if draft_scheduler:
                await draft_scheduler.stop()
                logger.info("Draft generation scheduler stopped")

            # Stop Telegram bot
            telegram_bot_service = getattr(app.state, "telegram_bot_service", None)
            if telegram_bot_service:
                await telegram_bot_service.stop_polling()
                logger.info("Telegram bot service stopped.")
        except Exception as e:
            logger.error(f"Error stopping services: {e}")
            
        logger.info("Application shutdown complete")


# Создание FastAPI приложения
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI-powered Telegram Comment Management through User Accounts",
    version="1.0.0",
    lifespan=lifespan
)

# Настройка CORS - должна быть первым middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Остальные middleware
if not IS_DEVELOP:
    app.add_middleware(HTTPSRedirectMiddleware)
app.add_middleware(AuthenticationMiddleware)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

# Health check endpoint
@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Karma App API is running"}

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}

# Подключаем роутеры
app.include_router(admin_router, prefix="/api/admin")
app.include_router(api_router, prefix="/api/v1")

# Base.metadata.create_all(bind=engine) # Uncomment if you want to create tables on startup without Alembic

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_delay=1,
        proxy_headers=True,
    ) 