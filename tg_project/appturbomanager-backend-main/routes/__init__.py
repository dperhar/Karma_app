"""API routes package.

This package contains all API route handlers for the application.
"""

from fastapi import APIRouter

from .api.admin.auth import router as admin_auth_router
from .api.admin.menu import router as admin_menu_router
from .api.admin.messages import router as admin_messages_router
from .api.admin.users import router as admin_users_router
from .api.ai_dialogs import router as ai_dialogs_router
from .api.menu import router as menu_router
from .api.telegram.auth import router as telegram_auth_router
from .api.telegram.chat_messages import router as telegram_chat_messages_router
from .api.telegram.chats import router as telegram_chats_router
from .api.tg_chat import router as tg_chat_router
from .api.transcribe import router as transcribe_router
from .api.users import router as users_router
from .api.websocket import router as websocket_router

miniapp_router = APIRouter(prefix="/api")

miniapp_router.include_router(users_router)
miniapp_router.include_router(menu_router)
miniapp_router.include_router(websocket_router)
miniapp_router.include_router(tg_chat_router)
miniapp_router.include_router(telegram_auth_router)
miniapp_router.include_router(telegram_chats_router)
miniapp_router.include_router(telegram_chat_messages_router)
miniapp_router.include_router(transcribe_router)
miniapp_router.include_router(ai_dialogs_router)

admin_router = APIRouter(prefix="/api/admin")

admin_router.include_router(admin_auth_router)
admin_router.include_router(admin_users_router)
admin_router.include_router(admin_menu_router)
admin_router.include_router(admin_messages_router)

__all__ = ["admin_router", "miniapp_router"]
