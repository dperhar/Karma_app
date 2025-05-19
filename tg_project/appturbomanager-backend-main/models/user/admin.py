"""Database models for user management and authentication."""

from uuid import uuid4

from sqlalchemy import Column, String
from werkzeug.security import check_password_hash, generate_password_hash

from models.db_base import DBBase
from models.mixins.timestamp_mixin import TimestampMixin


class Admin(TimestampMixin, DBBase):
    """Model representing an admin"""

    __tablename__ = "admins"

    id = Column(String, primary_key=True, default=lambda: uuid4().hex)
    login = Column(String, nullable=False, unique=True)
    password_hash = Column(String, nullable=False)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)

    def set_password(self, password: str) -> None:
        """Set password hash from plain password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Check if provided password matches the hash."""
        return check_password_hash(self.password_hash, password)
