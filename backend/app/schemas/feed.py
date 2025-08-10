"""Pydantic schemas for the user feed."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .draft_comment import DraftCommentResponse


class DraftMeta(BaseModel):
    """Minimal draft info for a post in the feed."""
    id: Optional[str] = None
    status: Optional[str] = None
    updated_at: Optional[str] = None


class PostForFeed(BaseModel):
    """Represents a post within a feed item."""
    id: str = Field(..., description="Internal UUID of the message")
    telegram_id: int = Field(..., description="Telegram's ID for the message")
    channel_telegram_id: int = Field(..., description="Telegram's channel ID")
    url: Optional[str] = None
    text: Optional[str] = Field(None, description="Post content")
    reactions: Optional[Dict[str, Any]] = None
    channel: Dict[str, Any] = Field(..., description="Channel information")
    date: str = Field(..., description="Post date as ISO string")
    views: Optional[int] = None
    forwards: Optional[int] = None
    replies: Optional[int] = None
    created_at: str = Field(..., description="Created timestamp")
    updated_at: str = Field(..., description="Updated timestamp")
    draft_meta: Optional[DraftMeta] = None

    class Config:
        from_attributes = True
        populate_by_name = True

class FeedItem(BaseModel):
    """Represents a single item in the user's feed."""
    post: PostForFeed
    draft: Optional[DraftCommentResponse] = None

class FeedResponse(BaseModel):
    """Response model for the feed endpoint matching frontend expectations."""
    posts: List[PostForFeed]
    total: int
    page: int
    limit: int 