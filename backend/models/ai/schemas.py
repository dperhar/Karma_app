"""Pydantic schemas for AI data validation and serialization."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from models.ai.ai_request import AIRequestModel


class AIRequestBase(BaseModel):
    """Base schema for AI request data."""

    request_text: str
    model: AIRequestModel

    model_config = ConfigDict(from_attributes=True)


class AIRequestCreate(AIRequestBase):
    """Schema for creating a new AI request."""

    dialog_id: str
    user_id: str
    response_text: str


class AIRequestResponse(AIRequestBase):
    """Schema for AI request response."""

    id: str
    dialog_id: str
    user_id: str
    response_text: str
    created_at: str
    updated_at: str


class AIDialogBase(BaseModel):
    """Base schema for AI dialog data."""

    title: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AIDialogCreate(BaseModel):
    """Schema for creating a new AI dialog."""

    chat_id: str


class AIDialogResponse(BaseModel):
    """Schema for AI dialog response."""

    id: str
    chat_id: str
    user_id: str
    created_at: str
    updated_at: str


class AIDialogMessageCreate(BaseModel):
    """Schema for creating a new AI dialog message."""

    dialog_id: str
    content: str
    role: str = Field(..., pattern="^(user|assistant)$")
    model: Optional[str] = None


class AIDialogMessageResponse(BaseModel):
    """Schema for AI dialog message response."""

    id: str
    dialog_id: str
    content: str
    role: str
    model: Optional[str] = None
    created_at: str
    updated_at: str


class AIDialogWithMessages(BaseModel):
    """Schema for AI dialog with messages."""

    dialog: AIDialogResponse
    messages: list[AIRequestResponse]


class LangChainMessageRequest(BaseModel):
    """Schema for LangChain message request."""

    dialog_id: str
    content: str
    dialog_context_length: int
    model_name: str
    temperature: float = 0.5
    prompt_template: str
    max_tokens: Optional[int] = 2000
