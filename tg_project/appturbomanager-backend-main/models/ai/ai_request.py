"""Telegram chat models."""

from enum import Enum
from uuid import uuid4

from sqlalchemy import Column, ForeignKey, String
from sqlalchemy import Enum as SQLEnum

from models.db_base import DBBase
from models.mixins.timestamp_mixin import TimestampMixin


class AIRequestModel(str, Enum):
    """AI request model."""

    GPT_4_1 = "gpt-4.1"
    GPT_4_1_MINI = "gpt-4.1-mini"
    GPT_4_1_NANO = "gpt-4.1-nano"
    CLAUDE_3_7_SONNET = "claude-3-7-sonnet-20250219"
    CLAUDE_3_5_HAIKU = "claude-3-5-haiku-20241022"


class AIRequest(DBBase, TimestampMixin):
    """Telegram chat model."""

    __tablename__ = "ai_requests"

    id = Column(String, primary_key=True, default=lambda: uuid4().hex)
    dialog_id = Column(String, ForeignKey("ai_dialogs.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    request_text = Column(String, nullable=False)
    response_text = Column(String, nullable=False)
    model = Column(SQLEnum(AIRequestModel), nullable=False)
