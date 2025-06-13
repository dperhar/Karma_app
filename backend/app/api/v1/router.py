"""Main API router for v1."""

from fastapi import APIRouter

from . import auth, drafts, users, telegram
from app.api.telegram.auth import router as telegram_auth_router

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["v1-authentication"])
api_router.include_router(users.router, prefix="/users", tags=["v1-users"])
api_router.include_router(drafts.router, prefix="/drafts", tags=["v1-drafts"])
api_router.include_router(telegram.router, prefix="/telegram", tags=["v1-telegram"])
api_router.include_router(telegram_auth_router, tags=["telegram-auth"]) 