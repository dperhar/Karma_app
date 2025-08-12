"""Pydantic schemas for AI Profile responses."""

from __future__ import annotations

from typing import Optional, Dict, Any, Union, List
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.ai_profile import AnalysisStatus


class AIProfileResponse(BaseModel):
    """Schema returned for a user's AI-generated vibe profile."""

    id: str
    user_id: str
    analysis_status: AnalysisStatus | str
    vibe_profile_json: Optional[Dict[str, Any]] = None
    last_analyzed_at: Optional[Union[str, datetime]] = None
    messages_analyzed_count: Optional[str] = None
    ai_model_used: Optional[str] = None
    analysis_version: Optional[str] = None
    last_error_message: Optional[str] = None

    # Convenience persona fields mirrored from model (may be null)
    persona_name: Optional[str] = None
    user_system_prompt: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AIProfileUpdate(BaseModel):
    """Payload to update parts of a user's AI profile.

    All fields are optional; provided values will be merged into the stored
    vibe_profile_json and/or mirrored persona fields.
    """

    # Mirrored persona fields
    persona_name: Optional[str] = None
    user_system_prompt: Optional[str] = None

    # High-level vibe profile adjustments
    tone: Optional[str] = None
    verbosity: Optional[str] = None
    emoji_usage: Optional[str] = None
    style_prompt: Optional[str] = None

    # Lists
    topics_of_interest: Optional[List[str]] = None
    signature_templates: Optional[List[str]] = None
    do_list: Optional[List[str]] = None
    dont_list: Optional[List[str]] = None
    signature_phrases: Optional[List[str]] = None

    # Digital communication sub-section
    greetings: Optional[List[str]] = None
    typical_endings: Optional[List[str]] = None

    # Digital Twin config partial update (frontend edits everything except HD and Astro)
    dt_config: Optional[Dict[str, Any]] = None

