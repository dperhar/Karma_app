"""Telegram chat models."""

from uuid import uuid4

from sqlalchemy import BigInteger, Column, ForeignKey, String

from models.db_base import DBBase
from models.mixins.timestamp_mixin import TimestampMixin


class ManagementPerson(DBBase, TimestampMixin):
    """Telegram chat model."""

    __tablename__ = "management_persons"

    id = Column(String, primary_key=True, default=lambda: uuid4().hex)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    telegram_id = Column(BigInteger, nullable=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
