"""Dependencies for FastAPI routes."""

import logging
from typing import Optional

from aiogram import Bot
from fastapi import Depends, HTTPException, Request, status

from models.user.schemas import AdminResponse, UserResponse, UserTelegramResponse
from services.domain.user_service import UserService
from services.dependencies import container

logger = logging.getLogger(__name__)


async def get_request(request: Request) -> Request:
    """Get the current request object."""
    return request


async def get_current_user(
    request: Request,
    user_service: UserService = Depends(lambda: container.resolve(UserService)),
) -> Optional[UserResponse]:
    """
    Get current user from Telegram auth data in request state.

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

    tg_user = getattr(request.state, "user", None)

    if not tg_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    user = await user_service.get_user_by_telegram_id(tg_user.id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return user


async def get_optional_user(
    request: Request,
    user_service: UserService = Depends(lambda: container.resolve(UserService)),
) -> Optional[UserResponse]:
    """
    Get current user from Telegram auth data in request state, but don't require authentication.
    
    Returns None if no authentication is provided.
    """
    # Always allow OPTIONS requests 
    if request.method == "OPTIONS":
        return None

    tg_user = getattr(request.state, "user", None)

    if not tg_user:
        return None

    user = await user_service.get_user_by_telegram_id(tg_user.id)
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
        bot_instance = request.app.state.bot_instance
        if not bot_instance:
            logger.error("Bot instance not found in application state")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Bot instance not available",
            )
        return bot_instance.bot
    except Exception as e:
        logger.error(f"Error getting bot instance: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bot instance not available",
        ) from e
