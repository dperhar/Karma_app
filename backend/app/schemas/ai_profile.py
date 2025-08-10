"""Pydantic schemas for AI Profile responses."""

from __future__ import annotations

from typing import Optional, Dict, Any

from pydantic import BaseModel, ConfigDict

from app.models.ai_profile import AnalysisStatus


class AIProfileResponse(BaseModel):
    """Schema returned for a user's AI-generated vibe profile."""

    id: str
    user_id: str
    analysis_status: AnalysisStatus | str
    vibe_profile_json: Optional[Dict[str, Any]] = None
    last_analyzed_at: Optional[str] = None
    messages_analyzed_count: Optional[str] = None
    ai_model_used: Optional[str] = None
    analysis_version: Optional[str] = None
    last_error_message: Optional[str] = None

    # Convenience persona fields mirrored from model (may be null)
    persona_name: Optional[str] = None
    user_system_prompt: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


