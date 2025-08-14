"""Schemas for Digital Twin context capture and approval."""

from typing import List, Optional
from pydantic import BaseModel, Field


class ContextApproveRequest(BaseModel):
    """Request body for approving a captured context run for LLM analysis."""

    run_id: str = Field(..., description="Identifier returned by dry-run capture")
    min_len: Optional[int] = Field(default=8, description="Minimum message length to include")
    languages: Optional[List[str]] = Field(
        default=["ru", "en"], description="Allowed languages: ru, en"
    )
    exclude_regex: Optional[str] = Field(
        default=None, description="Regex to exclude messages (e.g., promo links)"
    )
    per_chat_cap: Optional[int] = Field(
        default=300, description="Limit messages per chat to avoid over-representation"
    )
    dedupe: Optional[bool] = Field(
        default=True, description="Remove duplicate normalized messages"
    )



