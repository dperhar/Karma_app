"""Telegram chat models."""

from uuid import uuid4

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from app.models.db_base import DBBase
from app.models.timestamp_mixin import TimestampMixin


class TelegramMessengerChatUser(DBBase, TimestampMixin):
    """Telegram chat model."""

    __tablename__ = "telegram_messenger_chat_users"

    id = Column(String, primary_key=True, default=lambda: uuid4().hex)
    telegram_id = Column(BigInteger, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    chat_id = Column(String, ForeignKey("telegram_messenger_chats.id"), nullable=False)
    management_person_id = Column(
        String, ForeignKey("management_persons.id"), nullable=True
    )
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    is_bot = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    is_creator = Column(Boolean, default=False)
    join_date = Column(DateTime, nullable=True)

    # Relationships
    chat = relationship("TelegramMessengerChat", back_populates="participants")
    user = relationship("User")
    management_person = relationship("ManagementPerson")
