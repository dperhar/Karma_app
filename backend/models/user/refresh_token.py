"""Refresh token model for secure token management."""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship

from models.db_base import DBBase


class RefreshToken(DBBase):
    """Refresh token model for JWT token refresh."""

    __tablename__ = "refresh_tokens"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(Text, nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    revoked_at = Column(DateTime, nullable=True)
    device_info = Column(String, nullable=True)  # Optional device fingerprint
    ip_address = Column(String, nullable=True)  # IP address when token was created
    
    # Relationship
    user = relationship("User", back_populates="refresh_tokens")

    def __repr__(self):
        return f"<RefreshToken {self.id} for user {self.user_id}>"

    def is_expired(self) -> bool:
        """Check if the refresh token is expired."""
        return datetime.utcnow() > self.expires_at

    def is_valid(self) -> bool:
        """Check if the refresh token is valid (not expired and not revoked)."""
        return not self.is_revoked and not self.is_expired()

    def revoke(self):
        """Revoke the refresh token."""
        self.is_revoked = True
        self.revoked_at = datetime.utcnow() 