"""Repository for refresh token management."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import and_, select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken
from app.services.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class RefreshTokenRepository(BaseRepository):
    """Repository class for refresh token operations."""

    def __init__(self):
        super().__init__()

    async def create_refresh_token(
        self,
        user_id: str,
        token_hash: str,
        expires_at: datetime,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> RefreshToken:
        """Create a new refresh token."""
        async with self.get_session() as session:
            refresh_token = RefreshToken(
                id=uuid4().hex,
                user_id=user_id,
                token_hash=token_hash,
                expires_at=expires_at,
                device_info=device_info,
                ip_address=ip_address,
            )
            
            session.add(refresh_token)
            await session.commit()
            await session.refresh(refresh_token)
            
            logger.info(f"Created refresh token {refresh_token.id} for user {user_id}")
            return refresh_token

    async def get_refresh_token_by_hash(self, token_hash: str) -> Optional[RefreshToken]:
        """Get refresh token by hash."""
        async with self.get_session() as session:
            result = await session.execute(
                select(RefreshToken).where(RefreshToken.token_hash == token_hash)
            )
            return result.scalar_one_or_none()

    async def get_user_refresh_tokens(
        self, user_id: str, include_revoked: bool = False
    ) -> List[RefreshToken]:
        """Get all refresh tokens for a user."""
        async with self.get_session() as session:
            query = select(RefreshToken).where(RefreshToken.user_id == user_id)
            
            if not include_revoked:
                query = query.where(RefreshToken.is_revoked == False)
                
            result = await session.execute(query)
            return list(result.scalars().all())

    async def revoke_refresh_token(self, token_hash: str) -> bool:
        """Revoke a refresh token."""
        async with self.get_session() as session:
            result = await session.execute(
                select(RefreshToken).where(RefreshToken.token_hash == token_hash)
            )
            refresh_token = result.scalar_one_or_none()
            
            if refresh_token:
                refresh_token.revoke()
                await session.commit()
                logger.info(f"Revoked refresh token {refresh_token.id}")
                return True
            return False

    async def revoke_all_user_tokens(self, user_id: str) -> int:
        """Revoke all refresh tokens for a user."""
        async with self.get_session() as session:
            result = await session.execute(
                select(RefreshToken).where(
                    and_(RefreshToken.user_id == user_id, RefreshToken.is_revoked == False)
                )
            )
            tokens = list(result.scalars().all())
            revoked_count = 0
            
            for token in tokens:
                token.revoke()
                revoked_count += 1
                
            if revoked_count > 0:
                await session.commit()
                logger.info(f"Revoked {revoked_count} refresh tokens for user {user_id}")
                
            return revoked_count

    async def cleanup_expired_tokens(self) -> int:
        """Clean up expired refresh tokens."""
        async with self.get_session() as session:
            result = await session.execute(
                select(RefreshToken).where(RefreshToken.expires_at < datetime.utcnow())
            )
            expired_tokens = list(result.scalars().all())
            
            count = len(expired_tokens)
            for token in expired_tokens:
                await session.delete(token)
                
            if count > 0:
                await session.commit()
                logger.info(f"Cleaned up {count} expired refresh tokens")
                
            return count

    async def cleanup_revoked_tokens(self, older_than_days: int = 7) -> int:
        """Clean up old revoked refresh tokens."""
        async with self.get_session() as session:
            cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
            
            result = await session.execute(
                select(RefreshToken).where(
                    and_(
                        RefreshToken.is_revoked == True,
                        RefreshToken.revoked_at < cutoff_date
                    )
                )
            )
            old_revoked_tokens = list(result.scalars().all())
            
            count = len(old_revoked_tokens)
            for token in old_revoked_tokens:
                await session.delete(token)
                
            if count > 0:
                await session.commit()
                logger.info(f"Cleaned up {count} old revoked refresh tokens")
                
            return count

    async def get_token_count_for_user(self, user_id: str) -> int:
        """Get count of active refresh tokens for a user."""
        async with self.get_session() as session:
            result = await session.execute(
                select(RefreshToken).where(
                    and_(
                        RefreshToken.user_id == user_id,
                        RefreshToken.is_revoked == False,
                        RefreshToken.expires_at > datetime.utcnow()
                    )
                )
            )
            return len(list(result.scalars().all())) 