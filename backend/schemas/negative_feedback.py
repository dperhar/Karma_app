"""Pydantic schemas for negative feedback."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class NegativeFeedbackBase(BaseModel):
    """Base schema for negative feedback."""
    rejected_comment_text: str
    original_post_content: Optional[str] = None
    original_post_url: Optional[str] = None
    rejection_reason: Optional[str] = None
    ai_model_used: Optional[str] = None


class NegativeFeedbackCreate(NegativeFeedbackBase):
    """Schema for creating negative feedback."""
    user_id: str
    draft_comment_id: Optional[str] = None


class NegativeFeedbackUpdate(BaseModel):
    """Schema for updating negative feedback."""
    rejection_reason: Optional[str] = None


class NegativeFeedbackResponse(NegativeFeedbackBase):
    """Schema for negative feedback response."""
    id: str
    user_id: str
    draft_comment_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RegenerateRequest(BaseModel):
    """Schema for regenerating a draft comment after negative feedback."""
    rejection_reason: Optional[str] = None
    custom_instructions: Optional[str] = None 