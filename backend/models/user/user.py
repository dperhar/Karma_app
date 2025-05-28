"""Database models for user management and authentication."""

import logging
from uuid import uuid4

from sqlalchemy import BigInteger, Column, Integer, String, Text, JSON, DateTime
from sqlalchemy import Enum as SQLEnum

from models.ai.ai_request import AIRequestModel
from models.db_base import DBBase
from models.mixins.timestamp_mixin import TimestampMixin

logger = logging.getLogger(__name__)


class User(TimestampMixin, DBBase):
    """Model representing a user"""

    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: uuid4().hex)
    telegram_id = Column(BigInteger, unique=True, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    username = Column(String, nullable=True)
    telegram_session_string = Column(String, nullable=True)
    email = Column(String, nullable=True)
    telegram_chats_load_limit = Column(Integer, nullable=True, default=100)
    telegram_messages_load_limit = Column(Integer, nullable=True, default=100)
    preferred_ai_model = Column(
        SQLEnum(AIRequestModel), nullable=True, default=AIRequestModel.GPT_4_1_MINI
    )
    preferred_message_context_size = Column(Integer, nullable=True, default=50)
    
    # Digital Twin / User-specific AI persona fields
    persona_name = Column(String, nullable=True, default="Default User")
    persona_style_description = Column(
        Text, 
        nullable=True, 
        comment="Describes the user's own communication style for AI, learned from their messages."
    )
    persona_interests_json = Column(
        JSON, 
        nullable=True, 
        comment="JSON list of interest keywords for the user, learned from their activity."
    )
    user_system_prompt = Column(
        Text, 
        nullable=True, 
        comment="AI system prompt derived from the user's topics/interests, used for comment generation."
    )
    last_context_analysis_at = Column(
        DateTime, 
        nullable=True, 
        comment="Timestamp of the last successful user context analysis."
    )
    context_analysis_status = Column(
        String, 
        nullable=True, 
        comment="Status of the user context analysis (e.g., PENDING, COMPLETED, FAILED)."
    )

    def has_valid_tg_session(self) -> bool:
        """Check if the user has a valid Telegram session."""
        return self.telegram_session_string is not None
