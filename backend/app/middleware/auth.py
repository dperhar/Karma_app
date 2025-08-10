"""Authentication middleware for Karma App."""

import logging
from typing import Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.dependencies import container
from app.services.redis_service import RedisService
from app.services.user_service import UserService
from app.core.config import settings

logger = logging.getLogger(__name__)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware for handling authentication across the application."""

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process the request and add user info to request state."""
        logger.info(f"🔧 AuthMiddleware START - path: {request.url.path}")
        
        # Skip authentication for certain paths
        skip_auth_paths = [
            "/",
            "/health",
            "/docs", 
            "/openapi.json",
            "/redoc",
            "/api/admin/auth/login",
            "/api/v1/auth/telegram",    # Only auth endpoints, not all telegram endpoints
            "/api/telegram/auth"
        ]

        # Skip for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            logger.info(f"🔧 AuthMiddleware - skipping OPTIONS request")
            return await call_next(request)

        # Check if this path should skip auth (exact matches)
        should_skip = False
        for skip_path in skip_auth_paths:
            if request.url.path == skip_path or request.url.path.startswith(skip_path + "/"):
                should_skip = True
                break
        
        if should_skip:
            logger.info(f"🔧 AuthMiddleware - skipping auth for path: {request.url.path}")
            return await call_next(request)

        # Initialize user and admin
        user = None
        admin = None
        
        logger.info(f"🔧 AuthMiddleware - processing auth for path: {request.url.path}")
        
        # Try session cookie via Redis, but don't let failures block dev fallback
        try:
            session_id = request.cookies.get(settings.SESSION_COOKIE_NAME)
            logger.info(f"🔧 AuthMiddleware - session_id: {session_id}")
            if session_id:
                logger.info(f"🔧 AuthMiddleware - Found session_id: {session_id}")
                redis_service = container.resolve(RedisService)
                session_data = redis_service.get_session(f"web_session:{session_id}")
                logger.info(f"🔧 AuthMiddleware - Session data: {session_data}")
                if session_data and "user_id" in session_data:
                    user_service = container.resolve(UserService)
                    user = await user_service.get_user(session_data["user_id"]) 
                    logger.info(f"🔧 AuthMiddleware - User from session: {user.id if user else None}")
        except Exception as e:
            logger.error(f"🔧 AuthMiddleware - Session lookup error (continuing): {e}", exc_info=True)

        # Development mode fallback should always run independently
        if not user and settings.IS_DEVELOP and request.url.path.startswith("/api/v1/"):
            try:
                logger.info(f"🔧 AuthMiddleware - Using development fallback for: {request.url.path}")
                user_service = container.resolve(UserService)
                user = await user_service.get_user_by_telegram_id(109005276)
                logger.info(f"🔧 AuthMiddleware - Development user loaded: {user.id if user else None}")
            except Exception as e:
                logger.error(f"🔧 AuthMiddleware - Dev fallback error: {e}", exc_info=True)

        # Set user/admin in request state
        request.state.user = user
        request.state.admin = admin
        
        logger.info(f"🔧 AuthMiddleware END - user set: {user.id if user else None}")

        # Continue processing
        response = await call_next(request)
        return response
