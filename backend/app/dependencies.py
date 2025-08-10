"""Dependencies for FastAPI routes."""

import logging
from typing import Optional

from aiogram import Bot
from fastapi import Depends, HTTPException, Request, status

from app.schemas.user import AdminResponse, UserResponse, UserTelegramResponse
from app.core.config import settings
from app.services.user_service import UserService
from app.core.dependencies import container

logger = logging.getLogger(__name__)


async def get_request(request: Request) -> Request:
    """Get the current request object."""
    return request


async def get_current_user(
    request: Request,
    user_service: UserService = Depends(lambda: container.resolve(UserService)),
) -> Optional[UserResponse]:
    """
    Get current user from request state (set by middleware).

    Args:
        request: FastAPI request object
        user_service: Injected UserService instance

    Returns:
        UserResponse: User data from database or None for OPTIONS requests

    Raises:
        HTTPException: If user is not authenticated (except for OPTIONS)
    """
    # Always allow OPTIONS requests with proper CORS headers
    if request.method == "OPTIONS":
        return None

    # The middleware sets the user in request.state.user
    user = getattr(request.state, "user", None)
    logger.info(f"🔍 get_current_user - user from state: {user}")

    if not user:
        # Dev fallback: return a mock user so FE can work without full auth/session
        if settings.IS_DEVELOP:
            logger.info("🔍 get_current_user - dev fallback user injected")
            return UserResponse(
                id="dev-user-109005276",
                telegram_id=109005276,
                username="dev_user",
                first_name="Development",
                last_name="User",
                phone_number=None,
                is_active=True,
            )
        logger.info(f"🔍 get_current_user - no user in state, raising 401")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    logger.info(f"🔍 get_current_user - returning user: {user.id if hasattr(user, 'id') else 'no id'}")
    return user


async def get_optional_user(
    request: Request,
    user_service: UserService = Depends(lambda: container.resolve(UserService)),
) -> Optional[UserResponse]:
    """
    Get current user from request state, but don't require authentication.
    
    Returns None if no authentication is provided.
    """
    # Always allow OPTIONS requests 
    if request.method == "OPTIONS":
        return None

    # The middleware sets the user in request.state.user
    user = getattr(request.state, "user", None)
    return user


async def get_current_admin(request: Request) -> Optional[AdminResponse]:
    """Get current admin from request state."""
    # Always allow OPTIONS requests with proper CORS headers
    if request.method == "OPTIONS":
        return None
    admin = getattr(request.state, "admin", None)

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return admin


async def get_optional_admin(request: Request) -> Optional[AdminResponse]:
    """Get admin from request state if available, but don't require authentication.

    This is used for endpoints that should be accessible without authentication,
    like GET requests to tagcloud endpoints.
    """
    # Just return the admin if it exists, but don't raise an error if it doesn't
    return getattr(request.state, "admin", None)


async def get_bot(request: Request) -> Bot:
    """Get bot instance from application state."""
    try:
        bot_service = request.app.state.telegram_bot_service
        if not bot_service or not bot_service.bot:
            logger.error("Bot instance not found in application state")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Bot instance not available",
            )
        return bot_service.bot
    except Exception as e:
        logger.error(f"Error getting bot instance: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bot instance not available",
        ) from e 