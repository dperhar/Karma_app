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

from middleware.auth import AuthMiddleware
from routes import admin_router, miniapp_router
from routes.api.karma import router as karma_router
from routes.api.draft_comments import router as draft_comments_router
from routes.api.telegram.auth import router as telegram_auth_router
from routes.api.auth.tokens import router as tokens_router
from routes.api.telethon_monitoring import router as telethon_monitoring_router
from services.dependencies import container
from services.domain.data_fetching_service import DataFetchingService
from services.domain.scheduler_service import SchedulerService
from services.external.telethon_client import TelethonClient
from services.external.telethon_service import TelethonService

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
    """Initialize Telethon services for Comment Management System."""
    try:
        logger.info("Initializing Comment Management System services...")
        
        # Initialize Telethon services
        telethon_client = container.resolve(TelethonClient)
        telethon_service = container.resolve(TelethonService)
        
        # Store services in application state
        app.state.telethon_client = telethon_client
        app.state.telethon_service = telethon_service
        
        # Initialize repositories and services
        for repository_class in container.get_registered_repositories():
            container.resolve(repository_class)
        
        # Initialize data fetching service and scheduler
        data_fetching_service = container.resolve(DataFetchingService)
        scheduler_service = SchedulerService()
        
        # Store scheduler in application state for cleanup
        app.state.scheduler_service = scheduler_service
        
        # Start periodic data fetching task
        await scheduler_service.start_periodic_task(
            task_func=data_fetching_service.fetch_new_data_for_all_users,
            min_interval_minutes=30,
            max_interval_minutes=240,
            task_name="telegram_data_fetch"
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
                logger.info("Scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
            
        # Disconnect all Telethon clients
        try:
            telethon_client = getattr(app.state, 'telethon_client', None)
            if telethon_client:
                await telethon_client.disconnect_all()
        except Exception as e:
            logger.error(f"Error during telethon shutdown: {e}")
            
        logger.info("Application shutdown complete")


# Создание FastAPI приложения
app = FastAPI(
    title="Comment Management System",
    description="AI-powered Telegram Comment Management through User Accounts",
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

# Health check endpoint
@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "Comment Management System"}

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}

# Подключаем роутеры
app.include_router(miniapp_router)
app.include_router(admin_router)
app.include_router(karma_router)
app.include_router(draft_comments_router)
app.include_router(telegram_auth_router, prefix="/api")
app.include_router(tokens_router)
app.include_router(telethon_monitoring_router)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_delay=1,
        proxy_headers=True,
    )
