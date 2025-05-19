"""API routes for message management."""

from aiogram import Bot
from fastapi import APIRouter, Depends, HTTPException, status

from models.base.schemas import (
    APIResponse,
    MessageCreate,
    MessageResponse,
    MessageStatusUpdate,
)
from routes.dependencies import get_bot, logger
from services.dependencies import get_message_service
from services.domain.message_service import MessageService

router = APIRouter(prefix="/messages", tags=["messages"])


@router.post("", response_model=APIResponse[MessageResponse])
async def create_message(
    message_data: MessageCreate,
    message_service: MessageService = Depends(get_message_service),
) -> APIResponse[MessageResponse]:
    """Create a new message."""
    try:
        message = await message_service.create_message(message_data)
        return APIResponse(
            success=True,
            data=message,
            message="Message created successfully",
        )
    except Exception as e:
        logger.error(f"Error creating message: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating message",
        ) from e


@router.get("", response_model=APIResponse[list[MessageResponse]])
async def get_messages(
    message_service: MessageService = Depends(get_message_service),
) -> APIResponse[list[MessageResponse]]:
    """Get all messages."""
    try:
        messages = await message_service.get_messages()
        if not messages:
            return APIResponse(success=True, data=[], message="No messages found")

        return APIResponse(
            success=True,
            data=messages,
            message="Messages retrieved successfully",
        )
    except Exception as e:
        logger.error(f"Error retrieving messages: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving messages",
        ) from e


@router.get("/{message_id}", response_model=APIResponse[MessageResponse])
async def get_message(
    message_id: str,
    message_service: MessageService = Depends(get_message_service),
) -> APIResponse[MessageResponse]:
    """Get message by ID."""
    try:
        message = await message_service.get_message(message_id)
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found",
            )

        return APIResponse(
            success=True,
            data=message,
            message="Message retrieved successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving message: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving message",
        ) from e


@router.put("/{message_id}", response_model=APIResponse[MessageResponse])
async def update_message(
    message_id: str,
    message_data: MessageCreate,
    message_service: MessageService = Depends(get_message_service),
) -> APIResponse[MessageResponse]:
    """Update message by ID."""
    try:
        message = await message_service.update_message(message_id, message_data)
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found",
            )

        return APIResponse(
            success=True,
            data=message,
            message="Message updated successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating message: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating message",
        ) from e


@router.delete("/{message_id}", response_model=APIResponse)
async def delete_message(
    message_id: str,
    message_service: MessageService = Depends(get_message_service),
) -> APIResponse:
    """Delete message by ID."""
    try:
        await message_service.delete_message(message_id)
        return APIResponse(
            success=True,
            message="Message deleted successfully",
        )
    except Exception as e:
        logger.error(f"Error deleting message: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting message",
        ) from e


@router.patch("/{message_id}/status", response_model=APIResponse[MessageResponse])
async def update_message_status(
    message_id: str,
    status_data: MessageStatusUpdate,
    message_service: MessageService = Depends(get_message_service),
) -> APIResponse[MessageResponse]:
    """Update message status."""
    try:
        message = await message_service.update_message_status(message_id, status_data)
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found",
            )

        return APIResponse(
            success=True,
            data=message,
            message="Message status updated successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating message status: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating message status",
        ) from e


@router.post("/{message_id}/publish", response_model=APIResponse[MessageResponse])
async def publish_message(
    message_id: str,
    bot: Bot = Depends(get_bot),
    message_service: MessageService = Depends(get_message_service),
) -> APIResponse[MessageResponse]:
    """Publish message and send it to all users."""
    try:
        # Get bot from request app state
        message = await message_service.publish_message(message_id, bot)
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found",
            )

        return APIResponse(
            success=True,
            data=message,
            message="Message published and sent to users successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error publishing message: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error publishing message",
        ) from e
