"""Pydantic schemas for Telegram connections."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TelegramConnectionBase(BaseModel):
    """Base schema for telegram connection."""
    is_active: bool = True
    validation_status: Optional[str] = None


class TelegramConnectionCreate(TelegramConnectionBase):
    """Schema for creating a telegram connection."""
    user_id: str
    session_string: str  # Unencrypted string for input, will be encrypted before storage


class TelegramConnectionUpdate(BaseModel):
    """Schema for updating a telegram connection."""
    is_active: Optional[bool] = None
    validation_status: Optional[str] = None


class TelegramConnectionResponse(BaseModel):
    """Schema for telegram connection response (no sensitive data)."""
    id: str
    user_id: str
    last_used: Optional[datetime] = None
    is_active: bool
    last_validation_at: Optional[datetime] = None
    validation_status: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TelegramConnectionStatus(BaseModel):
    """Schema for telegram connection status check."""
    is_connected: bool
    is_valid: bool
    last_used: Optional[datetime] = None
    validation_status: Optional[str] = None 