"""Pydantic schemas for draft comments."""

from datetime import datetime
from typing import Optional, Dict, Any

from pydantic import BaseModel

from models.ai.draft_comment import DraftStatus


class DraftCommentBase(BaseModel):
    """Base schema for draft comment."""
    persona_name: Optional[str] = None
    ai_model_used: Optional[str] = None
    original_post_url: Optional[str] = None
    original_post_content: Optional[str] = None
    original_post_text_preview: Optional[str] = None
    draft_text: str
    edited_text: Optional[str] = None
    final_text_to_post: Optional[str] = None
    status: DraftStatus = DraftStatus.DRAFT
    generation_params: Optional[Dict[str, Any]] = None
    failure_reason: Optional[str] = None


class DraftCommentCreate(DraftCommentBase):
    """Schema for creating a draft comment."""
    original_message_id: str
    user_id: str


class DraftCommentUpdate(BaseModel):
    """Schema for updating a draft comment."""
    edited_text: Optional[str] = None
    status: Optional[DraftStatus] = None
    final_text_to_post: Optional[str] = None
    failure_reason: Optional[str] = None


class DraftCommentResponse(DraftCommentBase):
    """Schema for draft comment response."""
    id: str
    original_message_id: str
    user_id: str
    posted_telegram_message_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True 