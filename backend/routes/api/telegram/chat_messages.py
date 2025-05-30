"""Routes for Telegram chat messages and participants operations."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel

from models.base.schemas import APIResponse
from models.telegram_messenger.chat_user import TelegramMessengerChatUser
from models.telegram_messenger.message import TelegramMessengerMessage
from routes.dependencies import get_current_user
from services.dependencies import container
from services.domain.telegram_messenger.chat_service import TelegramMessengerChatService
from services.domain.telegram_messenger.chat_user_service import (
    TelegramMessengerChatUserService,
)
from services.domain.telegram_messenger.messages_service import (
    TelegramMessengerMessagesService,
)
from services.domain.user_service import UserService
from services.external.telethon_client import TelethonClient

router = APIRouter(prefix="/telegram/chat", tags=["telegram-chat"])


class TelegramMessengerChatUserResponse(BaseModel):
    """Pydantic model for TelegramMessengerChatUser response."""

    id: str
    telegram_id: int
    user_id: str
    chat_id: str
    management_person_id: Optional[str]
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    phone: Optional[str]
    is_bot: bool
    is_admin: bool
    is_creator: bool
    join_date: Optional[datetime]

    class Config:
        """Pydantic config."""

        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class TelegramMessengerMessageResponse(BaseModel):
    """Pydantic model for TelegramMessengerMessage response."""

    id: str
    telegram_id: int
    chat_id: str
    sender_id: Optional[str]
    text: Optional[str]
    date: datetime
    edit_date: Optional[datetime]
    media_type: Optional[str]
    file_id: Optional[str]
    reply_to_message_telegram_id: Optional[int]

    class Config:
        """Pydantic config."""

        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class PaginationInfo(BaseModel):
    """Pagination information."""
    
    offset: Optional[int] = None
    offset_id: Optional[int] = None
    has_more: bool = False


class ChatParticipantsResponse(BaseModel):
    """Response model for chat participants."""

    participants: list[TelegramMessengerChatUserResponse]
    pagination: Optional[PaginationInfo] = None


class ChatMessagesResponse(BaseModel):
    """Response model for chat messages."""

    messages: list[TelegramMessengerMessageResponse]
    pagination: Optional[PaginationInfo] = None


@router.get(
    "/{telegram_id}/participants", response_model=APIResponse[ChatParticipantsResponse]
)
async def get_chat_participants(
    telegram_id: int,
    limit: int = Query(default=50, ge=1, le=100, description="Number of participants to retrieve (max 100 for safety)"),
    offset: int = Query(default=0, ge=0, description="Number of participants to skip"),
    current_user: UserService = Depends(get_current_user),
    chat_service: TelegramMessengerChatService = Depends(
        lambda: container.resolve(TelegramMessengerChatService)
    ),
    chat_user_service: TelegramMessengerChatUserService = Depends(
        lambda: container.resolve(TelegramMessengerChatUserService)
    ),
    telethon_client: TelethonClient = Depends(
        lambda: container.resolve(TelethonClient)
    ),
) -> APIResponse[ChatParticipantsResponse]:
    """Get list of chat participants with safe pagination."""
    try:
        client = await telethon_client.get_or_create_client(current_user.id)
        if not client:
            return APIResponse(
                success=False, # This path might not be hit if get_current_user raises first
                message="Telegram session is not active or invalid. Please log in again via Settings."
            )

        # Get chat from database or sync from Telegram
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

        # Get participants with pagination
        participants, next_pagination = await chat_user_service.get_chat_participants_paginated(
            client=client,
            chat=chat,
            limit=limit,
            offset=offset,
        )
        
        # Prepare pagination info for response
        pagination_info = None
        if next_pagination:
            pagination_info = PaginationInfo(
                offset=next_pagination.get('offset'),
                has_more=True
            )
        
        return APIResponse(
            success=True, 
            data=ChatParticipantsResponse(participants=participants, pagination=pagination_info)
        )
    except Exception as e:
        return APIResponse(success=False, message=str(e))


@router.get("/{telegram_id}/messages", response_model=APIResponse[ChatMessagesResponse])
async def get_chat_messages(
    telegram_id: int,
    limit: int = Query(default=50, ge=1, le=100, description="Number of messages to retrieve (max 100 for safety)"),
    cursor_message_id: Optional[int] = Query(None, description="Message ID to start fetching from"),
    direction: str = Query("older", regex="^(older|newer)$", description="Direction to fetch messages"),
    current_user: UserService = Depends(get_current_user),
    chat_service: TelegramMessengerChatService = Depends(
        lambda: container.resolve(TelegramMessengerChatService)
    ),
    messages_service: TelegramMessengerMessagesService = Depends(
        lambda: container.resolve(TelegramMessengerMessagesService)
    ),
    telethon_client: TelethonClient = Depends(
        lambda: container.resolve(TelethonClient)
    ),
) -> APIResponse[ChatMessagesResponse]:
    """Get list of chat messages with safe pagination."""
    try:
        client = await telethon_client.get_or_create_client(current_user.id)
        if not client:
            return APIResponse(
                success=False, # This path might not be hit if get_current_user raises first
                message="Telegram session is not active or invalid. Please log in again via Settings."
            )

        # Get chat first
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

        # Get messages with pagination
        messages, next_pagination = await messages_service.get_chat_messages_paginated(
            client=client,
            chat=chat,
            limit=limit,
            cursor_message_id=cursor_message_id,
            direction=direction,
        )
        
        # Prepare pagination info for response
        pagination_info = None
        if next_pagination:
            pagination_info = PaginationInfo(
                offset_id=next_pagination.get('offset_id'),
                has_more=True
            )
        
        return APIResponse(
            success=True, 
            data=ChatMessagesResponse(messages=messages, pagination=pagination_info)
        )
    except Exception as e:
        return APIResponse(success=False, message=str(e))
