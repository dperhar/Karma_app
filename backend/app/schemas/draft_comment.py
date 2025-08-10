"""Pydantic schemas for draft comments."""

from datetime import datetime
from typing import Optional, Dict, Any, List

from pydantic import BaseModel

from app.models.draft_comment import DraftStatus


class DraftCommentBase(BaseModel):
    """Base schema for draft comment."""
    persona_name: Optional[str] = None
    ai_model_used: Optional[str] = None
    original_post_url: Optional[str] = None
    original_post_content: Optional[str] = None
    ai_context_summary: Optional[str] = None
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
    generation_params: Optional[Dict[str, Any]] = None


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


class PostData(BaseModel):
    """Schema for post data needed for regeneration."""
    original_message_id: str
    original_post_url: Optional[str] = None
    original_post_content: Optional[str] = None


class RegenerateRequest(BaseModel):
    """Schema for draft regeneration request."""
    post_data: PostData
    rejection_reason: Optional[str] = None


class PostGenerateItem(BaseModel):
    """Minimal data to queue AI draft generation for a post."""
    original_message_id: str
    original_post_content: Optional[str] = None
    original_post_url: Optional[str] = None
    channel_telegram_id: Optional[int] = None


class BatchGenerateRequest(BaseModel):
    """Batch of posts to generate drafts for."""
    posts: List[PostGenerateItem]