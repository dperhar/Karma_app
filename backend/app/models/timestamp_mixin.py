"""Timestamp mixin for SQLAlchemy models."""

# Standard library imports
from datetime import datetime

# Third-party imports
from sqlalchemy import Column, DateTime


class TimestampMixin:
    """Mixin for adding created_at and updated_at columns to a model."""

    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        nullable=False,
    )
