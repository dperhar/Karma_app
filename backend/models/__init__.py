"""Models package initialization."""

# Import all models first
from models.ai.ai_dialog import AIDialog
from models.ai.ai_profile import AIProfile
from models.ai.ai_request import AIRequest
from models.ai.draft_comment import DraftComment
from models.ai.negative_feedback import NegativeFeedback
from models.base.menu import MenuItem
from models.base.message import Message
from models.management.person import ManagementPerson
from models.mixins.timestamp_mixin import TimestampMixin
from models.relationships import setup_relationships
from models.telegram_messenger.chat import TelegramMessengerChat
from models.telegram_messenger.chat_user import TelegramMessengerChatUser
from models.telegram_messenger.message import TelegramMessengerMessage
from models.user.admin import Admin
from models.user.telegram_connection import TelegramConnection
from models.user.user import User

# Setup all model relationships
setup_relationships()

__all__ = [
    "AIDialog",
    "AIProfile",
    "AIRequest",
    "Admin",
    "DraftComment",
    "ManagementPerson",
    "MenuItem",
    "Message",
    "NegativeFeedback",
    "TelegramConnection",
    "TelegramMessengerChat",
    "TelegramMessengerChatUser",
    "TelegramMessengerMessage",
    "TimestampMixin",
    "User",
]
