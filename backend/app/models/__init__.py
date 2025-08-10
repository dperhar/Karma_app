"""Ensure SQLAlchemy maps all models by importing them at package import time.

This avoids lazy mapper configuration errors like missing class names in relationships.
"""

# Import core models so SQLAlchemy class registry is populated
from .user import User  # noqa: F401
from .telegram_connection import TelegramConnection  # noqa: F401
from .draft_comment import DraftComment, DraftStatus  # noqa: F401
from .telegram_message import TelegramMessengerMessage  # noqa: F401
from .chat import TelegramMessengerChat, TelegramMessengerChatType  # noqa: F401


