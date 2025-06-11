"""Database models for user management and authentication."""

import logging
from uuid import uuid4
from enum import Enum

from sqlalchemy import BigInteger, Column, Integer, String, Text, JSON, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.models.ai_request import AIRequestModel
from app.models.db_base import DBBase
from app.models.timestamp_mixin import TimestampMixin

logger = logging.getLogger(__name__)


class UserInitialSyncStatus(str, Enum):
    """User initial sync status for safe onboarding."""
    
    PENDING = "pending"
    MINIMAL_COMPLETED = "minimal_completed"
    FULL_COMPLETED = "full_completed"
    FAILED = "failed"


class User(TimestampMixin, DBBase):
    """Model representing a user"""

    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: uuid4().hex)
    telegram_id = Column(BigInteger, unique=True, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    username = Column(String, nullable=True)
    
    # Removed telegram_session_string - now handled by TelegramConnection model
    last_telegram_auth_at = Column(DateTime, nullable=True, comment="Timestamp of the last successful Telegram authentication")
    email = Column(String, nullable=True)
    telegram_chats_load_limit = Column(Integer, nullable=True, default=20)  # Reduced default for safety
    telegram_messages_load_limit = Column(Integer, nullable=True, default=50)  # Reduced default for safety
    telegram_participants_load_limit = Column(Integer, nullable=True, default=50, comment="Batch size for fetching participants")
    preferred_ai_model = Column(
        SQLEnum(AIRequestModel), nullable=True, default=AIRequestModel.GPT_4_1_MINI
    )
    preferred_message_context_size = Column(Integer, nullable=True, default=50)
    
    # New fields for safe initial synchronization
    initial_sync_status = Column(
        SQLEnum(UserInitialSyncStatus), 
        nullable=True, 
        default=UserInitialSyncStatus.PENDING,
        comment="Status of the user's initial safe sync process"
    )
    last_dialog_sync_at = Column(
        DateTime, 
        nullable=True, 
        comment="Timestamp of the last successful dialog list sync"
    )

    # Relationships
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    telegram_connection = relationship("TelegramConnection", back_populates="user", uselist=False, cascade="all, delete-orphan")
    ai_profile = relationship("AIProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    draft_comments = relationship("DraftComment", back_populates="user", cascade="all, delete-orphan")
    negative_feedback = relationship("NegativeFeedback", back_populates="user", cascade="all, delete-orphan")

    def has_valid_tg_session(self) -> bool:
        """Check if the user has a valid Telegram session."""
        return (
            self.telegram_connection is not None 
            and self.telegram_connection.is_session_valid()
        )

    def needs_initial_sync(self) -> bool:
        """Check if user needs initial synchronization."""
        return self.initial_sync_status == UserInitialSyncStatus.PENDING

    def needs_vibe_analysis(self) -> bool:
        """Check if user needs vibe profile analysis."""
        return (
            self.ai_profile is None 
            or self.ai_profile.needs_analysis()
        )
