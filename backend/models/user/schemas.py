"""Pydantic schemas for user data validation and serialization."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field

from models.ai.ai_request import AIRequestModel


class UserBase(BaseModel):
    """Base schema for user data."""

    telegram_id: Optional[int] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    telegram_session_string: Optional[str] = None
    last_telegram_auth_at: Optional[datetime] = None
    email: Optional[str] = None
    telegram_chats_load_limit: Optional[int] = 100
    telegram_messages_load_limit: Optional[int] = 100
    preferred_ai_model: Optional[AIRequestModel] = AIRequestModel.GPT_4_1_MINI
    preferred_message_context_size: Optional[int] = 50

    model_config = ConfigDict(from_attributes=True)


class UserCreate(UserBase):
    """Schema for user data in requests."""


class UserUpdate(BaseModel):
    """Schema for updating user data."""

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    telegram_id: Optional[int] = None
    telegram_session_string: Optional[str] = None
    email: Optional[str] = None
    telegram_chats_load_limit: Optional[int] = None
    telegram_messages_load_limit: Optional[int] = None
    preferred_ai_model: Optional[AIRequestModel] = None
    preferred_message_context_size: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class UserResponse(UserBase):
    """Schema for user data in responses."""

    id: str
    telegram_session_string: Optional[str] = Field(default=None, exclude=True)

    @computed_field # type: ignore[misc]
    def has_valid_tg_session(self) -> bool:
        """Check if the user has a valid Telegram session."""
        return self.telegram_session_string is not None

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"exclude": {"telegram_session_string"}},
        exclude={"telegram_session_string"},
    )


class UserTelegramResponse(BaseModel):
    """Schema for user data in Telegram."""

    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None
    language_code: Optional[str] = None
    is_premium: Optional[bool] = None
    allows_write_to_pm: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)


class AdminCreate(BaseModel):
    """Schema for creating a new admin."""

    login: str
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AdminLogin(BaseModel):
    """Schema for admin login."""

    login: str
    password: str

    model_config = ConfigDict(from_attributes=True)


class AdminResponse(BaseModel):
    """Schema for admin response."""

    id: str
    login: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
