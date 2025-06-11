"""Negative feedback models for AI improvement."""

import logging
from uuid import uuid4
from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.models.db_base import DBBase
from app.models.timestamp_mixin import TimestampMixin

logger = logging.getLogger(__name__)


class NegativeFeedback(TimestampMixin, DBBase):
    """Model representing negative feedback for AI-generated content."""

    __tablename__ = "negative_feedback"

    id = Column(String, primary_key=True, default=lambda: uuid4().hex)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # The rejected comment text that the user didn't like
    rejected_comment_text = Column(Text, nullable=False, comment="AI-generated comment that was rejected")
    
    # Context from the original post that the comment was responding to
    original_post_content = Column(Text, nullable=True, comment="Original post content for context")
    original_post_url = Column(String, nullable=True, comment="URL of the original post if available")
    
    # Metadata about the rejection
    rejection_reason = Column(String, nullable=True, comment="Optional reason for rejection (e.g., 'too_formal', 'wrong_tone')")
    ai_model_used = Column(String, nullable=True, comment="AI model that generated the rejected comment")
    
    # Link to the draft comment if it exists
    draft_comment_id = Column(String, ForeignKey("draft_comments.id"), nullable=True)
    
    # Relationships
    user = relationship("User")
    draft_comment = relationship("DraftComment")

    def __repr__(self):
        return f"<NegativeFeedback(id={self.id}, user_id={self.user_id}, rejected_text='{self.rejected_comment_text[:50]}...')>" 