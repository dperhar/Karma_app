"""API routes for Telegram chat management."""

from typing import Optional

from aiogram.types import Chat
from fastapi import APIRouter, Depends, HTTPException, status

from models.base.schemas import APIResponse
from routes.dependencies import get_current_user, logger
from services.dependencies import get_telegram_bot_service
from services.external.telegram_bot_service import TelegramBotService

router = APIRouter(prefix="/tg-chat", tags=["telegram-chat"])


@router.get("/{chat_id}", response_model=APIResponse[dict])
async def get_chat_info(
    chat_id: int,
    current_user: Optional[Chat] = Depends(get_current_user),
    telegram_bot_service: TelegramBotService = Depends(get_telegram_bot_service),
) -> APIResponse[dict]:
    """Get Telegram chat information by ID."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    try:
        # Validate chat ID format
        if chat_id == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid chat ID format"
            )

        chat, permanent_id = await telegram_bot_service.get_chat(chat_id)
        logger.info(f"Chat: {chat}")
        logger.info(f"Permanent ID: {permanent_id}")

        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat not found. Please ensure the bot is a member of the chat and has the necessary permissions.",
            )

        return APIResponse(
            success=True,
            data={
                "chat": chat.model_dump(),
                "permanent_id": permanent_id,
                "chat_type": chat.type,
                "chat_title": chat.title,
                "chat_username": chat.username,
                "invite_link": (
                    f"https://t.me/c/{str(chat_id)[4:]}"
                    if chat_id > 1000000000000
                    else None
                ),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chat info: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error getting chat information",
        ) from e
