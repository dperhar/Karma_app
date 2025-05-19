"""Telegram chat models."""

from uuid import uuid4

from sqlalchemy import Column, ForeignKey, String

from models.db_base import DBBase
from models.mixins.timestamp_mixin import TimestampMixin


class AIDialog(DBBase, TimestampMixin):
    """Telegram chat model."""

    __tablename__ = "ai_dialogs"

    id = Column(String, primary_key=True, default=lambda: uuid4().hex)
    chat_id = Column(String, ForeignKey("telegram_messenger_chats.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
