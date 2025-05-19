"""Telegram chat models."""

from enum import Enum
from uuid import uuid4

from sqlalchemy import BigInteger, Column, ForeignKey, Integer, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship

from models.db_base import DBBase
from models.mixins.timestamp_mixin import TimestampMixin


class TelegramMessengerChatType(str, Enum):
    """Telegram chat type."""

    PRIVATE = "private"
    GROUP = "group"
    SUPERGROUP = "supergroup"
    CHANNEL = "channel"


class TelegramMessengerChat(DBBase, TimestampMixin):
    """Telegram chat model."""

    __tablename__ = "telegram_messenger_chats"

    id = Column(String, primary_key=True, default=lambda: uuid4().hex)
    telegram_id = Column(BigInteger, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    type = Column(SQLEnum(TelegramMessengerChatType), nullable=False)
    title = Column(String, nullable=True)
    member_count = Column(Integer, nullable=True)

    # Relationships
    messages = relationship("TelegramMessage", back_populates="chat")
    user = relationship("User", back_populates="telegram_chats")
    participants = relationship("TelegramParticipant", back_populates="chat")
