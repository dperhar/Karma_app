"""Pydantic schemas for refresh token operations."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class RefreshTokenCreate(BaseModel):
    """Schema for creating a refresh token."""
    
    user_id: str
    device_info: Optional[str] = None
    ip_address: Optional[str] = None


class RefreshTokenResponse(BaseModel):
    """Schema for refresh token response."""
    
    id: str
    user_id: str
    expires_at: datetime
    is_revoked: bool
    created_at: datetime
    revoked_at: Optional[datetime] = None
    device_info: Optional[str] = None
    ip_address: Optional[str] = None

    class Config:
        from_attributes = True


class TokenPair(BaseModel):
    """Schema for access and refresh token pair."""
    
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token expiry in seconds")


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request."""
    
    refresh_token: str


class AccessTokenResponse(BaseModel):
    """Schema for new access token response."""
    
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token expiry in seconds") 