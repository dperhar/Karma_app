"""Handlers for the Telegram bot."""

from .command_handlers import router as command_router
from .main_state_handlers import router as main_state_router

__all__ = [
    "command_router",
    "main_state_router",
]
