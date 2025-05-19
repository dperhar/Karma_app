"""Database models for conference messages."""

import enum
from uuid import uuid4

from sqlalchemy import Column, Enum, String

from models.db_base import DBBase
from models.mixins.timestamp_mixin import TimestampMixin


class MessageStatus(enum.Enum):
    """Enum representing the status of a message"""

    DRAFT = "draft"
    PUBLISHED = "published"
    ERROR = "error"


class Message(TimestampMixin, DBBase):
    """Model representing a conference message"""

    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=lambda: uuid4().hex)
    text = Column(String, nullable=False)
    status = Column(Enum(MessageStatus), nullable=False)
