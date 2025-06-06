"""Database models for Telegram connection management."""

import logging
from uuid import uuid4
from datetime import datetime

from sqlalchemy import Column, String, LargeBinary, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from models.db_base import DBBase
from models.mixins.timestamp_mixin import TimestampMixin

logger = logging.getLogger(__name__)


class TelegramConnection(TimestampMixin, DBBase):
    """Model representing a user's Telegram connection with encrypted session data."""

    __tablename__ = "telegram_connections"

    id = Column(String, primary_key=True, default=lambda: uuid4().hex)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True)
    
    # Encrypted session string - this is the critical security requirement
    session_string_encrypted = Column(LargeBinary, nullable=True, comment="Encrypted Telethon session string")
    
    # Connection metadata
    last_used = Column(DateTime, nullable=True, comment="Last time this connection was used")
    is_active = Column(Boolean, default=True, nullable=False, comment="Whether this connection is currently active")
    
    # Connection validation
    last_validation_at = Column(DateTime, nullable=True, comment="Last time the session was validated")
    validation_status = Column(String, nullable=True, comment="Status of last validation (VALID, INVALID, EXPIRED)")
    
    # Relationships
    user = relationship("User", back_populates="telegram_connection")

    def mark_as_used(self):
        """Mark the connection as recently used."""
        self.last_used = datetime.utcnow()
    
    def is_session_valid(self) -> bool:
        """Check if the session appears to be valid based on last validation."""
        return (
            self.session_string_encrypted is not None 
            and self.validation_status == "VALID"
            and self.is_active
        ) 