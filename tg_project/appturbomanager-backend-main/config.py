"""Application configuration."""

import os

from dotenv import load_dotenv

load_dotenv()

# Database
DATABASE_URL = os.getenv("DATABASE_URL")

# Database connection pool settings
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", 10))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", 20))
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", 30))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", 1800))  # 30 minutes

# Redis
REDIS_HOST = os.getenv("REDIS_HOST", "doublekiss-redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
REDIS_URL = os.getenv("REDIS_URL")
# JWT
JWT_SECRET_KEY = "your-secret-key-here"  # In production, use environment variable
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 600
REFRESH_TOKEN_EXPIRE_DAYS = 30
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

IS_DEVELOP = os.getenv("IS_DEVELOP") == "true"

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
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

# Telethon
TELETHON_API_ID = os.getenv("TELETHON_API_ID")
TELETHON_API_HASH = os.getenv("TELETHON_API_HASH")

# Groq
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Anthropic
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
