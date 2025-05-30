"""Telegram chat models."""

from enum import Enum
from uuid import uuid4

from sqlalchemy import BigInteger, Column, ForeignKey, Integer, String, DateTime, Text
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


class TelegramMessengerChatSyncStatus(str, Enum):
    """Telegram chat sync status for tracking pagination state."""
    
    NEVER_SYNCED = "never_synced"
    INITIAL_MINIMAL_SYNCED = "initial_minimal_synced"
    BACKGROUND_SYNCING = "background_syncing"
    PARTIALLY_SYNCED = "partially_synced"
    FULLY_SYNCED = "fully_synced"


class TelegramMessengerChat(DBBase, TimestampMixin):
    """Telegram chat model."""

    __tablename__ = "telegram_messenger_chats"

    id = Column(String, primary_key=True, default=lambda: uuid4().hex)
    telegram_id = Column(BigInteger, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    type = Column(SQLEnum(TelegramMessengerChatType), nullable=False)
    title = Column(String, nullable=True)
    member_count = Column(Integer, nullable=True)
    
    # Fields for tracking last fetched messages
    last_fetched_message_telegram_id = Column(BigInteger, nullable=True)
    last_successful_fetch_at = Column(DateTime, nullable=True)

    # New fields for pagination and sync state tracking
    dialog_list_offset_date = Column(DateTime, nullable=True, comment="Offset date for dialogs pagination")
    dialog_list_offset_id = Column(BigInteger, nullable=True, comment="Offset ID for dialogs pagination")
    participant_list_offset = Column(Integer, nullable=True, default=0, comment="Offset for participants pagination")
    sync_status = Column(
        SQLEnum(TelegramMessengerChatSyncStatus), 
        nullable=True, 
        default=TelegramMessengerChatSyncStatus.NEVER_SYNCED,
        comment="Current sync status for safe pagination"
    )

    # Additional pagination cursors for messages
    messages_pagination_cursor = Column(Text, nullable=True, comment="JSON cursor for message pagination state")

    # Relationships
    messages = relationship("TelegramMessage", back_populates="chat")
    user = relationship("User", back_populates="telegram_chats")
    participants = relationship("TelegramParticipant", back_populates="chat")
