"""Pydantic schemas for per-user AI generation settings."""

from typing import Optional
from pydantic import BaseModel, Field, field_validator


class AISettings(BaseModel):
    """AI settings returned to the client."""

    model: str = Field(default="gemini-2.5-pro", description="Gemini model name")
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_output_tokens: int = Field(default=512, ge=1, le=8192)


class AISettingsUpdate(BaseModel):
    """Partial update for AI settings from client."""

    model: Optional[str] = Field(default=None, description="Gemini model name")
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    max_output_tokens: Optional[int] = Field(default=None, ge=1, le=8192)

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        # Allow common 2.5 models; keep open for future
        allowed_prefix = "gemini-"
        if not v.startswith(allowed_prefix):
            raise ValueError("model must start with 'gemini-'")
        return v



