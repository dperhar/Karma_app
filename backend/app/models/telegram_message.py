"""Telegram message models."""

from uuid import uuid4

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship

from app.models.db_base import DBBase
from app.models.timestamp_mixin import TimestampMixin


class TelegramMessengerMessage(DBBase, TimestampMixin):
    """Telegram message model."""

    __tablename__ = "telegram_messenger_messages"
    __table_args__ = (
        # Ensure uniqueness per chat, not globally across all chats
        UniqueConstraint("chat_id", "telegram_id", name="uix_msg_chat_telegram_id"),
    )

    id = Column(String, primary_key=True, default=lambda: uuid4().hex)
    # Telegram message ids are only unique within a chat; enforce uniqueness per chat
    telegram_id = Column(BigInteger, nullable=False)
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

    # Enriched features (optional)
    language = Column(String(8), nullable=True, comment="Detected dominant language: ru/en/mixed")
    link_urls = Column(JSON, nullable=True, comment="List of links found in message")
    named_entities = Column(JSON, nullable=True, comment="Naive NER entities from text")
    tokens = Column(JSON, nullable=True, comment="Lightweight token list sample for retrieval")
    rhetorical_type = Column(String(32), nullable=True, comment="question/exclamation/statement")
    env_quadrant = Column(String(32), nullable=True, comment="HIGH_SAFE_HIGH_DEPTH, ... snapshot")
    style_snapshot = Column(JSON, nullable=True, comment="Per-message style metrics snapshot")

    # Relationships
    chat = relationship("TelegramMessengerChat", back_populates="messages")
    sender = relationship("TelegramMessengerChatUser")
