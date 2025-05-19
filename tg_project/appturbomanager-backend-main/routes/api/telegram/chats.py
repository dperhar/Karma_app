"""Routes for Telegram chat operations."""

from fastapi import APIRouter, Depends, Query
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
    title: str | None
    member_count: int | None

    class Config:
        """Pydantic config."""

        from_attributes = True


class ChatListResponse(BaseModel):
    """Response model for chat list."""

    chats: list[TelegramMessengerChatResponse]


@router.get("/list", response_model=APIResponse[ChatListResponse])
async def get_chats(
    limit: int = Query(default=10, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    current_user: UserService = Depends(get_current_user),
    chat_service: TelegramMessengerChatService = Depends(
        lambda: container.resolve(TelegramMessengerChatService)
    ),
    telethon_client: TelethonClient = Depends(
        lambda: container.resolve(TelethonClient)
    ),
) -> APIResponse[ChatListResponse]:
    """Get list of user's Telegram chats."""
    try:
        client = await telethon_client.get_or_create_client(current_user.id)
        if not client:
            return APIResponse(success=True, data=ChatListResponse(chats=[]))

        chats = await chat_service.get_chats(
            client=client,
            user_id=current_user.id,
            limit=limit,
            offset=offset,
        )
        return APIResponse(success=True, data=ChatListResponse(chats=chats))
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
            return APIResponse(
                success=False,
                message="No valid Telegram session found. Please log in first.",
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
