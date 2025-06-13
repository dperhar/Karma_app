"""Application configuration settings."""

import logging
import os
from typing import List

from dotenv import load_dotenv

# Load .env from parent directory (project root)
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), '.env')
load_dotenv(env_path)


class Settings:
    """Application settings."""
    
    # Project settings
    PROJECT_NAME: str = "Karma App API"
    API_V1_STR: str = "/api/v1"
    
    # Environment
    IS_DEVELOP: bool = os.getenv("IS_DEVELOP", "true").lower() == "true"
    
    # CORS settings
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    @property
    def BACKEND_CORS_ORIGINS(self) -> List[str]:
        """Get CORS origins."""
        return [
            self.FRONTEND_URL,
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
            "null",  # For file:// protocol
        ]

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./karma_app.db")
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "10"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "1800"))  # 30 minutes

    # Security & Encryption
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "a_very_secret_key_for_dev_use_only_change_me")

    # JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-here")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    REFRESH_TOKEN_SECRET_KEY: str = os.getenv("REFRESH_TOKEN_SECRET_KEY", "refresh-token-secret-key-here")

    # Telegram
    TELETHON_API_ID: str = os.getenv("TELETHON_API_ID")
    TELETHON_API_HASH: str = os.getenv("TELETHON_API_HASH")
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "dummy-token-for-development")

    # LLM
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY")

    # Centrifugo WebSocket
    CENTRIFUGO_API_KEY: str = os.getenv("CENTRIFUGO_API_KEY", "dummy-centrifugo-key")
    CENTRIFUGO_API_URL: str = os.getenv("CENTRIFUGO_API_URL", "http://localhost:8000/api")

    # Session configuration
    SESSION_COOKIE_NAME: str = os.getenv("SESSION_COOKIE_NAME", "karma_session")
    SESSION_EXPIRY_SECONDS: int = int(os.getenv("SESSION_EXPIRY_SECONDS", "15552000"))  # 6 months (180 days)
    SESSION_SECRET_KEY: str = os.getenv("SESSION_SECRET_KEY", "another-super-secret-key-for-sessions")

    # AWS S3
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "dummy-access-key")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "dummy-secret-key")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "dummy-bucket")
    S3_ENDPOINT_URL: str = os.getenv("S3_ENDPOINT_URL")

settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings 