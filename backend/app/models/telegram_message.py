"""Telegram message models."""

from uuid import uuid4

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from app.models.db_base import DBBase
from app.models.timestamp_mixin import TimestampMixin


class TelegramMessengerMessage(DBBase, TimestampMixin):
    """Telegram message model."""

    __tablename__ = "telegram_messenger_messages"

    id = Column(String, primary_key=True, default=lambda: uuid4().hex)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    chat_id = Column(String, ForeignKey("telegram_messenger_chats.id"), nullable=False)
    sender_id = Column(
        String, ForeignKey("telegram_messenger_chat_users.id"), nullable=True
    )
    reply_to_message_telegram_id = Column(BigInteger, nullable=True)
    text = Column(String, nullable=True)
    date = Column(DateTime, nullable=False)
    edit_date = Column(DateTime, nullable=True)
    media_type = Column(String, nullable=True)  # photo, video, document, etc.
    file_id = Column(String, nullable=True)

    # Relationships
    chat = relationship("TelegramMessengerChat", back_populates="messages")
    sender = relationship("TelegramMessengerChatUser")
