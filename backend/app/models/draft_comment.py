"""AI-generated draft comment models."""

import enum
from uuid import uuid4

from sqlalchemy import BigInteger, Column, DateTime, Enum as SQLEnum, ForeignKey, JSON, String, Text
from sqlalchemy.orm import relationship

from app.models.db_base import DBBase
from app.models.timestamp_mixin import TimestampMixin


class DraftStatus(str, enum.Enum):
    """Status of a draft comment."""
    DRAFT = "DRAFT"
    EDITED = "EDITED"
    APPROVED = "APPROVED"
    POSTED = "POSTED"
    FAILED_TO_POST = "FAILED_TO_POST"
    REJECTED = "REJECTED"


class DraftComment(DBBase, TimestampMixin):
    """AI-generated draft comment model."""

    __tablename__ = "draft_comments"

    id = Column(String, primary_key=True, default=lambda: uuid4().hex)
    original_message_id = Column(String, ForeignKey("telegram_messenger_messages.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    persona_name = Column(String, nullable=True)  # e.g., "Mark Zuckerberg"
    ai_model_used = Column(String, nullable=True)  # e.g., "gemini-pro", "gpt-4.1-mini"
    
    # Original post information - aligned with vision
    original_post_url = Column(String, nullable=True, comment="URL of the original post")
    original_post_content = Column(Text, nullable=True, comment="Full content of the original post")
    original_post_text_preview = Column(Text, nullable=True)  # Snippet of the original post
    
    # Comment content
    draft_text = Column(Text, nullable=False)  # AI generated text
    edited_text = Column(Text, nullable=True)  # User-edited text
    final_text_to_post = Column(Text, nullable=True)  # Text that was/is to be posted

    status = Column(SQLEnum(DraftStatus), default=DraftStatus.DRAFT, nullable=False)
    posted_telegram_message_id = Column(BigInteger, nullable=True)  # ID once posted to Telegram
    
    generation_params = Column(JSON, nullable=True)  # Store params used for generation
    failure_reason = Column(Text, nullable=True)  # If status is FAILED_TO_POST

    # Relationships
    original_message = relationship("TelegramMessengerMessage")
    user = relationship("User")
    negative_feedback = relationship("NegativeFeedback", back_populates="draft_comment") 