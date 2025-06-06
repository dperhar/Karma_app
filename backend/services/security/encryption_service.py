"""Encryption service for handling sensitive data encryption/decryption."""

import logging
import os
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

logger = logging.getLogger(__name__)


class EncryptionService:
    """Service for encrypting and decrypting sensitive data."""
    
    def __init__(self):
        self._fernet = None
        self._initialize_encryption()
    
    def _initialize_encryption(self):
        """Initialize the encryption system with a key derived from environment."""
        encryption_key = os.getenv("ENCRYPTION_KEY")
        
        if not encryption_key:
            raise ValueError(
                "ENCRYPTION_KEY environment variable is required. "
                "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
        
        try:
            # If encryption_key is already a valid Fernet key, use it directly
            self._fernet = Fernet(encryption_key.encode())
        except Exception:
            # If not, derive a key from the provided string
            self._fernet = self._derive_key_from_string(encryption_key)
    
    def _derive_key_from_string(self, password: str) -> Fernet:
        """Derive a Fernet key from a password string."""
        # Use a fixed salt for reproducibility (in production, consider user-specific salts)
        salt = b'karma_app_salt_v1'  # Fixed salt - consider making this configurable
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return Fernet(key)
    
    def encrypt(self, data: str) -> bytes:
        """
        Encrypt a string and return encrypted bytes.
        
        Args:
            data: The string to encrypt
            
        Returns:
            Encrypted data as bytes
            
        Raises:
            ValueError: If data is None or empty
            Exception: If encryption fails
        """
        if not data:
            raise ValueError("Cannot encrypt empty or None data")
        
        try:
            encrypted_data = self._fernet.encrypt(data.encode('utf-8'))
            logger.debug("Successfully encrypted data")
            return encrypted_data
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise Exception(f"Encryption failed: {e}")
    
    def decrypt(self, encrypted_data: bytes) -> str:
        """
        Decrypt bytes and return the original string.
        
        Args:
            encrypted_data: The encrypted bytes to decrypt
            
        Returns:
            Decrypted string
            
        Raises:
            ValueError: If encrypted_data is None or empty
            Exception: If decryption fails
        """
        if not encrypted_data:
            raise ValueError("Cannot decrypt empty or None data")
        
        try:
            decrypted_data = self._fernet.decrypt(encrypted_data)
            result = decrypted_data.decode('utf-8')
            logger.debug("Successfully decrypted data")
            return result
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise Exception(f"Decryption failed: {e}")
    
    def encrypt_session_string(self, session_string: str) -> bytes:
        """
        Encrypt a Telegram session string.
        
        Args:
            session_string: The Telethon session string to encrypt
            
        Returns:
            Encrypted session string as bytes
        """
        if not session_string:
            raise ValueError("Session string cannot be empty")
        
        return self.encrypt(session_string)
    
    def decrypt_session_string(self, encrypted_session: bytes) -> str:
        """
        Decrypt a Telegram session string.
        
        Args:
            encrypted_session: The encrypted session bytes
            
        Returns:
            Decrypted session string
        """
        if not encrypted_session:
            raise ValueError("Encrypted session cannot be empty")
        
        return self.decrypt(encrypted_session)


# Singleton instance
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """Get the singleton encryption service instance."""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service 