"""Routes for Telegram chat operations."""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel

from models.base.schemas import APIResponse
from models.telegram_messenger.chat import (
    TelegramMessengerChatType,
)
from routes.dependencies import get_current_user
from services.dependencies import container
from services.domain.telegram_messenger.chat_service import TelegramMessengerChatService
from services.domain.user_service import UserService
from services.external.telethon_client import TelethonClient

router = APIRouter(prefix="/telegram/chats", tags=["telegram-chat"])


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
    current_user: UserService = Depends(get_current_user),
    chat_service: TelegramMessengerChatService = Depends(
        lambda: container.resolve(TelegramMessengerChatService)
    ),
    telethon_client: TelethonClient = Depends(
        lambda: container.resolve(TelethonClient)
    ),
) -> APIResponse[ChatListResponse]:
    """Get list of user's Telegram chats with safe pagination."""
    try:
        client = await telethon_client.get_or_create_client(current_user.id)
        if not client:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Telegram session is not active or invalid. Please log in again via Settings."
            )

        # Parse offset_date if provided
        parsed_offset_date = None
        if offset_date:
            try:
                parsed_offset_date = datetime.fromisoformat(offset_date.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid offset_date format. Use ISO format."
                )

        chats, next_pagination = await chat_service.get_chats_paginated(
            client=client,
            user_id=current_user.id,
            limit=limit,
            offset_date=parsed_offset_date,
            offset_id=offset_id,
        )
        
        # Prepare pagination info for response
        pagination_info = None
        if next_pagination:
            pagination_info = PaginationInfo(
                offset_date=next_pagination.get('offset_date').isoformat() if next_pagination.get('offset_date') else None,
                offset_id=next_pagination.get('offset_id'),
                has_more=True
            )
        
        return APIResponse(
            success=True, 
            data=ChatListResponse(chats=chats, pagination=pagination_info)
        )
    except Exception as e:
        return APIResponse(success=False, message=str(e))


@router.get("/{telegram_id}", response_model=APIResponse[TelegramMessengerChatResponse])
async def get_chat(
    telegram_id: int,
    current_user: UserService = Depends(get_current_user),
    chat_service: TelegramMessengerChatService = Depends(
        lambda: container.resolve(TelegramMessengerChatService)
    ),
    telethon_client: TelethonClient = Depends(
        lambda: container.resolve(TelethonClient)
    ),
) -> APIResponse[TelegramMessengerChatResponse]:
    """Get specific chat data."""
    try:
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
