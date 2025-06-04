"""Telethon Session Manager for centralized session handling."""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
import hashlib
import base64

from cryptography.fernet import Fernet
from telethon.sessions import StringSession

from services.repositories.user_repository import UserRepository


class SessionInfo:
    """Information about a session."""
    
    def __init__(self, session_string: str, user_id: str):
        self.session_string = session_string
        self.user_id = user_id
        self.created_at = datetime.utcnow()
        self.last_validated = datetime.utcnow()
        self.validation_attempts = 0
        self.is_valid = True
        self.last_error: Optional[str] = None
        
    def mark_validated(self):
        """Mark session as recently validated."""
        self.last_validated = datetime.utcnow()
        self.is_valid = True
        self.last_error = None
        
    def mark_invalid(self, error: str):
        """Mark session as invalid."""
        self.is_valid = False
        self.last_error = error
        self.validation_attempts += 1
        
    def needs_validation(self) -> bool:
        """Check if session needs validation."""
        if not self.is_valid:
            return True
        # Validate every hour
        return datetime.utcnow() - self.last_validated > timedelta(hours=1)


class TelethonSessionManager:
    """
    Centralized session management with validation and encryption.
    """
    
    def __init__(self, user_repository: UserRepository, encryption_key: Optional[bytes] = None):
        self.user_repository = user_repository
        self.logger = logging.getLogger(__name__)
        
        # Session storage
        self._sessions: Dict[str, SessionInfo] = {}
        self._session_lock = asyncio.Lock()
        
        # Encryption for session storage
        self._encryption_key = encryption_key or Fernet.generate_key()
        self._cipher = Fernet(self._encryption_key)
        
        # Validation settings
        self._validation_timeout = 30  # seconds
        self._max_validation_attempts = 3
        
    async def get_session(self, user_id: str) -> Optional[str]:
        """
        Get valid session string for user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Session string or None if no valid session
        """
        async with self._session_lock:
            # Check cached session
            if user_id in self._sessions:
                session_info = self._sessions[user_id]
                
                if session_info.is_valid and not session_info.needs_validation():
                    return session_info.session_string
                    
                # Remove invalid session
                if not session_info.is_valid and session_info.validation_attempts >= self._max_validation_attempts:
                    del self._sessions[user_id]
                    
            # Get session from database
            return await self._load_session_from_db(user_id)
            
    async def store_session(self, user_id: str, session_string: str) -> bool:
        """
        Store session for user.
        
        Args:
            user_id: User identifier
            session_string: Telegram session string
            
        Returns:
            True if stored successfully
        """
        try:
            async with self._session_lock:
                # Validate session format
                if not self._is_valid_session_format(session_string):
                    self.logger.error(f"Invalid session format for user {user_id}")
                    return False
                    
                # Store in cache
                session_info = SessionInfo(session_string, user_id)
                self._sessions[user_id] = session_info
                
                # Store in database
                await self._store_session_to_db(user_id, session_string)
                
                self.logger.info(f"Stored session for user {user_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error storing session for user {user_id}: {e}")
            return False
            
    async def remove_session(self, user_id: str) -> bool:
        """
        Remove session for user.
        
        Args:
            user_id: User identifier
            
        Returns:
            True if removed successfully
        """
        try:
            async with self._session_lock:
                # Remove from cache
                if user_id in self._sessions:
                    del self._sessions[user_id]
                    
                # Remove from database
                await self._remove_session_from_db(user_id)
                
                self.logger.info(f"Removed session for user {user_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error removing session for user {user_id}: {e}")
            return False
            
    async def validate_session(self, user_id: str, session_string: str) -> bool:
        """
        Validate session by creating a temporary client.
        
        Args:
            user_id: User identifier
            session_string: Session string to validate
            
        Returns:
            True if session is valid
        """
        try:
            from telethon import TelegramClient
            from config import TELETHON_API_ID, TELETHON_API_HASH
            
            # Create temporary client for validation
            client = TelegramClient(
                StringSession(session_string),
                int(TELETHON_API_ID),
                TELETHON_API_HASH,
                timeout=self._validation_timeout
            )
            
            try:
                # Connect and check authorization
                await asyncio.wait_for(client.connect(), timeout=self._validation_timeout)
                is_authorized = await client.is_user_authorized()
                
                async with self._session_lock:
                    if user_id in self._sessions:
                        if is_authorized:
                            self._sessions[user_id].mark_validated()
                        else:
                            self._sessions[user_id].mark_invalid("Not authorized")
                            
                return is_authorized
                
            finally:
                if client.is_connected():
                    await client.disconnect()
                    
        except Exception as e:
            self.logger.error(f"Error validating session for user {user_id}: {e}")
            async with self._session_lock:
                if user_id in self._sessions:
                    self._sessions[user_id].mark_invalid(str(e))
            return False
            
    async def cleanup_invalid_sessions(self):
        """Remove invalid sessions from cache and database."""
        async with self._session_lock:
            invalid_users = []
            
            for user_id, session_info in self._sessions.items():
                if not session_info.is_valid and session_info.validation_attempts >= self._max_validation_attempts:
                    invalid_users.append(user_id)
                    
            for user_id in invalid_users:
                del self._sessions[user_id]
                await self._remove_session_from_db(user_id)
                
            if invalid_users:
                self.logger.info(f"Cleaned up {len(invalid_users)} invalid sessions")
                
    async def get_session_stats(self) -> Dict:
        """Get session statistics."""
        async with self._session_lock:
            valid_sessions = sum(1 for s in self._sessions.values() if s.is_valid)
            invalid_sessions = len(self._sessions) - valid_sessions
            
            return {
                'total_sessions': len(self._sessions),
                'valid_sessions': valid_sessions,
                'invalid_sessions': invalid_sessions,
                'sessions_by_user': {user_id: s.is_valid for user_id, s in self._sessions.items()}
            }
            
    def _is_valid_session_format(self, session_string: str) -> bool:
        """Validate session string format."""
        try:
            # Basic validation - should be base64 encoded
            if not session_string or len(session_string) < 10:
                return False
                
            # Try to decode as base64
            import base64
            base64.b64decode(session_string)
            return True
            
        except Exception:
            return False
            
    async def _load_session_from_db(self, user_id: str) -> Optional[str]:
        """Load session from database."""
        try:
            user = await self.user_repository.get_user(user_id)
            if not user or not user.telegram_session_string:
                return None
                
            # Decrypt if needed
            session_string = user.telegram_session_string
            if self._is_encrypted_session(session_string):
                session_string = self._decrypt_session(session_string)
                
            # Cache the session
            session_info = SessionInfo(session_string, user_id)
            self._sessions[user_id] = session_info
            
            return session_string
            
        except Exception as e:
            self.logger.error(f"Error loading session from DB for user {user_id}: {e}")
            return None
            
    async def _store_session_to_db(self, user_id: str, session_string: str):
        """Store session to database."""
        try:
            user = await self.user_repository.get_user(user_id)
            if not user:
                self.logger.error(f"User {user_id} not found when storing session")
                return
                
            # Encrypt session for storage
            encrypted_session = self._encrypt_session(session_string)
            
            # Update user with encrypted session
            await self.user_repository.update_user_telegram_session(user_id, encrypted_session)
            
        except Exception as e:
            self.logger.error(f"Error storing session to DB for user {user_id}: {e}")
            
    async def _remove_session_from_db(self, user_id: str):
        """Remove session from database."""
        try:
            await self.user_repository.update_user_telegram_session(user_id, None)
        except Exception as e:
            self.logger.error(f"Error removing session from DB for user {user_id}: {e}")
            
    def _encrypt_session(self, session_string: str) -> str:
        """Encrypt session string."""
        try:
            encrypted = self._cipher.encrypt(session_string.encode())
            return base64.b64encode(encrypted).decode()
        except Exception as e:
            self.logger.error(f"Error encrypting session: {e}")
            return session_string  # Fallback to unencrypted
            
    def _decrypt_session(self, encrypted_session: str) -> str:
        """Decrypt session string."""
        try:
            encrypted_data = base64.b64decode(encrypted_session)
            decrypted = self._cipher.decrypt(encrypted_data)
            return decrypted.decode()
        except Exception as e:
            self.logger.error(f"Error decrypting session: {e}")
            return encrypted_session  # Fallback to assuming it's unencrypted
            
    def _is_encrypted_session(self, session_string: str) -> bool:
        """Check if session string is encrypted."""
        try:
            # Try to decrypt - if it works, it was encrypted
            self._decrypt_session(session_string)
            return True
        except Exception:
            return False 