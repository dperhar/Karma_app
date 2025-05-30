"""JWT service for token management."""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

import jwt
from fastapi import HTTPException, status

from config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_ALGORITHM,
    JWT_SECRET_KEY,
    REFRESH_TOKEN_EXPIRE_DAYS,
    REFRESH_TOKEN_SECRET_KEY,
)
from models.user.refresh_token_schemas import (
    AccessTokenResponse,
    RefreshTokenCreate,
    TokenPair,
)
from services.base.base_service import BaseService
from services.repositories.refresh_token_repository import RefreshTokenRepository

logger = logging.getLogger(__name__)


class JWTService(BaseService):
    """Service for JWT token operations."""

    def __init__(self, refresh_token_repository: RefreshTokenRepository):
        super().__init__()
        self.refresh_token_repository = refresh_token_repository

    def _create_access_token(self, data: Dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            
        to_encode.update({"exp": expire, "type": "access"})
        
        return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    def _create_refresh_token_string(self) -> str:
        """Create a secure random refresh token string."""
        return secrets.token_urlsafe(32)

    def _hash_refresh_token(self, token: str) -> str:
        """Hash refresh token for secure storage."""
        return hashlib.sha256(token.encode()).hexdigest()

    def verify_access_token(self, token: str) -> Dict:
        """Verify and decode access token."""
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            
            if payload.get("type") != "access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type",
                )
                
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Access token expired",
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid access token",
            )

    async def create_token_pair(
        self,
        user_id: str,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> TokenPair:
        """Create access and refresh token pair."""
        # Create access token
        access_token_data = {
            "sub": user_id,
            "user_id": user_id,
        }
        access_token = self._create_access_token(access_token_data)

        # Create refresh token
        refresh_token_string = self._create_refresh_token_string()
        refresh_token_hash = self._hash_refresh_token(refresh_token_string)
        
        # Calculate expiry
        expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        # Store refresh token in database
        await self.refresh_token_repository.create_refresh_token(
            user_id=user_id,
            token_hash=refresh_token_hash,
            expires_at=expires_at,
            device_info=device_info,
            ip_address=ip_address,
        )

        logger.info(f"Created token pair for user {user_id}")
        
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token_string,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def refresh_access_token(self, refresh_token: str) -> AccessTokenResponse:
        """Create new access token using refresh token."""
        # Hash the provided refresh token
        token_hash = self._hash_refresh_token(refresh_token)
        
        # Get refresh token from database
        db_refresh_token = await self.refresh_token_repository.get_refresh_token_by_hash(token_hash)
        
        if not db_refresh_token:
            logger.warning("Refresh token not found in database")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
            
        if not db_refresh_token.is_valid():
            logger.warning(f"Invalid refresh token for user {db_refresh_token.user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired or revoked",
            )

        # Create new access token
        access_token_data = {
            "sub": db_refresh_token.user_id,
            "user_id": db_refresh_token.user_id,
        }
        access_token = self._create_access_token(access_token_data)

        logger.info(f"Refreshed access token for user {db_refresh_token.user_id}")
        
        return AccessTokenResponse(
            access_token=access_token,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def revoke_refresh_token(self, refresh_token: str) -> bool:
        """Revoke a refresh token."""
        token_hash = self._hash_refresh_token(refresh_token)
        return await self.refresh_token_repository.revoke_refresh_token(token_hash)

    async def revoke_all_user_tokens(self, user_id: str) -> int:
        """Revoke all refresh tokens for a user."""
        return await self.refresh_token_repository.revoke_all_user_tokens(user_id)

    async def cleanup_expired_tokens(self) -> int:
        """Clean up expired refresh tokens."""
        return await self.refresh_token_repository.cleanup_expired_tokens()

    async def get_user_token_count(self, user_id: str) -> int:
        """Get count of active refresh tokens for a user."""
        return await self.refresh_token_repository.get_token_count_for_user(user_id) 