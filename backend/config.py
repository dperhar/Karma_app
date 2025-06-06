"""Application configuration."""

import logging
import os

from dotenv import load_dotenv

# Load .env from parent directory (project root)
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(env_path)

# Database
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Use absolute path for SQLite database to avoid path issues
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, "karma_app.db")
    DATABASE_URL = f"sqlite+aiosqlite:///{db_path}"

# Database connection pool settings
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", 10))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", 20))
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", 30))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", 1800))  # 30 minutes

# Redis
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")

# Security & Encryption
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    logging.warning(
        "ENCRYPTION_KEY not set. Generate one with: "
        "python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
    )

# JWT
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-here")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 30
REFRESH_TOKEN_SECRET_KEY = os.getenv("REFRESH_TOKEN_SECRET_KEY", "refresh-token-secret-key-here")

# Session configuration
SESSION_COOKIE_NAME = "karma_session_id"
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "another-super-secret-key-for-sessions") # For potential future use if signing session data
SESSION_EXPIRY_SECONDS = 90 * 24 * 60 * 60 # 3 months

# Telegram


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# LangChain
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2")
LANGCHAIN_ENDPOINT = os.getenv("LANGCHAIN_ENDPOINT")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT")

# Platform
PLATFORM_URL = os.getenv("PLATFORM_URL")
MINIAPP_URL = os.getenv("MINIAPP_URL")
MINIAPP_URL_CHAT = "https://t.me/+a2VbD-onWgQ4Y2Zi"
BOT_URL = os.getenv("BOT_URL")

# Development mode
IS_DEVELOP = os.getenv("IS_DEVELOP", "true").lower() == "true"

# S3
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL")

# Centrifugo
CENTRIFUGO_SECRET = os.getenv("CENTRIFUGO_SECRET")
CENTRIFUGO_API_URL = os.getenv("CENTRIFUGO_API_URL")
CENTRIFUGO_API_KEY = os.getenv("CENTRIFUGO_API_KEY")

# Webhook
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://your-domain.com/webhook")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

# Telethon
TELETHON_API_ID = os.getenv("TELETHON_API_ID") or os.getenv("API_ID")
TELETHON_API_HASH = os.getenv("TELETHON_API_HASH") or os.getenv("API_HASH")

# Groq
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Anthropic
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Frontend URL
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# External API Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Admin Authentication
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

# Телеграм бот больше не нужен для Comment Management System
# Работаем через пользовательские аккаунты (Telethon)
