"""Routes for Telegram chat messages and participants operations."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
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


class ChatParticipantsResponse(BaseModel):
    """Response model for chat participants."""

    participants: list[TelegramMessengerChatUserResponse]


class ChatMessagesResponse(BaseModel):
    """Response model for chat messages."""

    messages: list[TelegramMessengerMessageResponse]


@router.get(
    "/{telegram_id}/participants", response_model=APIResponse[ChatParticipantsResponse]
)
async def get_chat_participants(
    telegram_id: int,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
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
    """Get list of chat participants."""
    try:
        client = await telethon_client.get_or_create_client(current_user.id)
        if not client:
            return APIResponse(
                success=False,
                message="No valid Telegram session found. Please log in first.",
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

        # Get participants
        participants = await chat_user_service.get_chat_participants(
            client=client,
            chat=chat,
            limit=limit,
            offset=offset,
        )
        return APIResponse(
            success=True, data=ChatParticipantsResponse(participants=participants)
        )
    except Exception as e:
        return APIResponse(success=False, message=str(e))


@router.get("/{telegram_id}/messages", response_model=APIResponse[ChatMessagesResponse])
async def get_chat_messages(
    telegram_id: int,
    limit: int = Query(default=10, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
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
    """Get list of chat messages."""
    try:
        client = await telethon_client.get_or_create_client(current_user.id)
        if not client:
            return APIResponse(
                success=False,
                message="No valid Telegram session found. Please log in first.",
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

        # Get messages
        messages = await messages_service.get_chat_messages(
            client=client,
            chat=chat,
            limit=limit,
            offset=offset,
        )
        return APIResponse(success=True, data=ChatMessagesResponse(messages=messages))
    except Exception as e:
        return APIResponse(success=False, message=str(e))
