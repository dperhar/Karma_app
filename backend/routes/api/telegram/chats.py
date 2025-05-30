"""Routes for Telegram chat operations."""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel
import logging

from models.base.schemas import APIResponse
from models.telegram_messenger.chat import (
    TelegramMessengerChatType,
)
from routes.dependencies import get_optional_user
from services.dependencies import container
from services.domain.telegram_messenger.chat_service import TelegramMessengerChatService
from services.domain.user_service import UserService
from services.external.telethon_client import TelethonClient

router = APIRouter(prefix="/telegram/chats", tags=["telegram-chat"])
logger = logging.getLogger(__name__)


class TelegramMessengerChatResponse(BaseModel):
    """Pydantic model for TelegramMessengerChat response."""

    id: str
    telegram_id: int
    user_id: str
    type: TelegramMessengerChatType
    title: Optional[str]
    member_count: Optional[int]

    class Config:
        """Pydantic config."""

        from_attributes = True


class PaginationInfo(BaseModel):
    """Pagination information."""
    
    offset_date: Optional[str] = None
    offset_id: Optional[int] = None
    has_more: bool = False


class ChatListResponse(BaseModel):
    """Response model for chat list."""

    chats: list[TelegramMessengerChatResponse]
    pagination: Optional[PaginationInfo] = None


@router.get("/list", response_model=APIResponse[ChatListResponse])
async def get_chats(
    limit: int = Query(default=20, ge=1, le=50, description="Number of chats to retrieve (max 50 for safety)"),
    offset_date: Optional[str] = Query(None, description="ISO datetime string for pagination offset"),
    offset_id: Optional[int] = Query(None, description="Message ID for pagination offset"),
    current_user: Optional[UserService] = Depends(get_optional_user),
    chat_service: TelegramMessengerChatService = Depends(
        lambda: container.resolve(TelegramMessengerChatService)
    ),
    telethon_client: TelethonClient = Depends(
        lambda: container.resolve(TelethonClient)
    ),
) -> APIResponse[ChatListResponse]:
    """Get list of user's Telegram chats with safe pagination."""
    try:
        logger.info(f"GET /telegram/chats/list called with limit={limit}, offset_date={offset_date}, offset_id={offset_id}")
        
        # Check if user is authenticated
        if not current_user:
            logger.warning("GET /telegram/chats/list - User not authenticated")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )
        
        logger.info(f"GET /telegram/chats/list - User authenticated: user_id={current_user.id}")
        
        client = await telethon_client.get_or_create_client(current_user.id)
        if not client:
            logger.warning(f"GET /telegram/chats/list - No telegram client for user {current_user.id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Telegram session is not active or invalid. Please log in again via Settings."
            )

        logger.info(f"GET /telegram/chats/list - Telegram client obtained for user {current_user.id}")

        # Parse offset_date if provided
        parsed_offset_date = None
        if offset_date:
            try:
                parsed_offset_date = datetime.fromisoformat(offset_date.replace('Z', '+00:00'))
                logger.info(f"GET /telegram/chats/list - Parsed offset_date: {parsed_offset_date}")
            except ValueError:
                logger.error(f"GET /telegram/chats/list - Invalid offset_date format: {offset_date}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid offset_date format. Use ISO format."
                )

        logger.info(f"GET /telegram/chats/list - Calling chat_service.get_chats_paginated for user {current_user.id}")
        chats, next_pagination = await chat_service.get_chats_paginated(
            client=client,
            user_id=current_user.id,
            limit=limit,
            offset_date=parsed_offset_date,
            offset_id=offset_id,
        )
        
        logger.info(f"GET /telegram/chats/list - Got {len(chats)} chats for user {current_user.id}")
        if chats:
            logger.info(f"GET /telegram/chats/list - First few chats: {[{'id': chat.id, 'title': chat.title, 'telegram_id': chat.telegram_id} for chat in chats[:3]]}")
        else:
            logger.info("GET /telegram/chats/list - No chats returned")
        
        # Prepare pagination info for response
        pagination_info = None
        if next_pagination:
            pagination_info = PaginationInfo(
                offset_date=next_pagination.get('offset_date').isoformat() if next_pagination.get('offset_date') else None,
                offset_id=next_pagination.get('offset_id'),
                has_more=True
            )
            logger.info(f"GET /telegram/chats/list - Pagination info: {pagination_info}")
        
        response_data = ChatListResponse(chats=chats, pagination=pagination_info)
        logger.info(f"GET /telegram/chats/list - Returning response with {len(response_data.chats)} chats")
        
        return APIResponse(
            success=True, 
            data=response_data
        )
    except Exception as e:
        logger.error(f"GET /telegram/chats/list - Error: {str(e)}", exc_info=True)
        return APIResponse(success=False, message=str(e))


@router.get("/{telegram_id}", response_model=APIResponse[TelegramMessengerChatResponse])
async def get_chat(
    telegram_id: int,
    current_user: Optional[UserService] = Depends(get_optional_user),
    chat_service: TelegramMessengerChatService = Depends(
        lambda: container.resolve(TelegramMessengerChatService)
    ),
    telethon_client: TelethonClient = Depends(
        lambda: container.resolve(TelethonClient)
    ),
) -> APIResponse[TelegramMessengerChatResponse]:
    """Get specific chat data."""
    try:
        # Check if user is authenticated
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )
            
        client = await telethon_client.get_or_create_client(current_user.id)
        if not client:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Telegram session is not active or invalid. Please log in again via Settings."
            )

        chat = await chat_service.get_chat(
            client=client,
            telegram_id=telegram_id,
            user_id=current_user.id,
        )
        if not chat:
            return APIResponse(
                success=False,
                message=f"Chat with ID {telegram_id} not found",
                status_code=404,
            )
        return APIResponse(success=True, data=chat)
    except Exception as e:
        return APIResponse(success=False, message=str(e))
