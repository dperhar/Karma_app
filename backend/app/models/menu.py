"""Database models for conference halls."""

import enum
from uuid import uuid4

from sqlalchemy import Column, Enum, Integer, String

from app.models.db_base import DBBase
from app.models.timestamp_mixin import TimestampMixin


class MenuItemStatus(enum.Enum):
    """Enum representing the status of a menu item"""

    ACTIVE = "active"
    INACTIVE = "inactive"


class MenuItem(TimestampMixin, DBBase):
    """Model representing a conference hall"""

    __tablename__ = "menu_items"

    id = Column(String, primary_key=True, default=lambda: uuid4().hex)
    title = Column(String, nullable=False)
    status = Column(Enum(MenuItemStatus), nullable=False)
    url = Column(String, nullable=False)
    order = Column(Integer, nullable=False)
