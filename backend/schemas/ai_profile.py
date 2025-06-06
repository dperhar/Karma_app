"""Pydantic schemas for AI profiles."""

from datetime import datetime
from typing import Optional, Dict, Any, List

from pydantic import BaseModel

from models.ai.ai_profile import AnalysisStatus


class VibeProfileData(BaseModel):
    """Schema for structured vibe profile data."""
    tone: Optional[str] = None
    verbosity: Optional[str] = None
    emoji_usage: Optional[str] = None
    common_phrases: Optional[List[str]] = None
    topics_of_interest: Optional[List[str]] = None
    communication_patterns: Optional[Dict[str, Any]] = None


class AIProfileBase(BaseModel):
    """Base schema for AI profile."""
    analysis_status: AnalysisStatus = AnalysisStatus.PENDING
    ai_model_used: Optional[str] = None
    analysis_version: Optional[str] = "1.0"


class AIProfileCreate(AIProfileBase):
    """Schema for creating an AI profile."""
    user_id: str


class AIProfileUpdate(BaseModel):
    """Schema for updating an AI profile."""
    vibe_profile_json: Optional[Dict[str, Any]] = None
    analysis_status: Optional[AnalysisStatus] = None
    ai_model_used: Optional[str] = None
    last_error_message: Optional[str] = None


class AIProfileResponse(AIProfileBase):
    """Schema for AI profile response."""
    id: str
    user_id: str
    vibe_profile_json: Optional[Dict[str, Any]] = None
    last_analyzed_at: Optional[datetime] = None
    messages_analyzed_count: Optional[str] = None
    last_error_message: Optional[str] = None
    retry_count: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VibeProfileResponse(BaseModel):
    """Schema for vibe profile response with parsed data."""
    status: AnalysisStatus
    profile: Optional[VibeProfileData] = None
    last_analyzed_at: Optional[datetime] = None
    messages_analyzed_count: Optional[int] = None
    ai_model_used: Optional[str] = None


class AnalysisRequest(BaseModel):
    """Schema for requesting vibe profile analysis."""
    force_reanalysis: bool = False
    ai_model: Optional[str] = None 