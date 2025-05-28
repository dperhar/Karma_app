"""API routes for AI dialog management."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from models.ai.schemas import (
    AIDialogCreate,
    AIDialogResponse,
    AIDialogWithMessages,
    AIRequestResponse,
    LangChainMessageRequest,
)
from models.base.schemas import APIResponse
from models.user.schemas import UserTelegramResponse
from routes.dependencies import get_current_user, logger
from services.dependencies import get_ai_dialog_service
from services.domain.ai_dialog_service import AIDialogService

router = APIRouter(prefix="/ai-dialogs", tags=["ai-dialogs"])


@router.post("", response_model=APIResponse[AIDialogResponse])
async def create_dialog(
    dialog_data: AIDialogCreate,
    current_user: Optional[UserTelegramResponse] = Depends(get_current_user),
    ai_dialog_service: AIDialogService = Depends(get_ai_dialog_service),
) -> APIResponse[AIDialogResponse]:
    """Create a new AI dialog."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    try:
        # Create a new dialog data object with user_id from current_user
        dialog_data_dict = dialog_data.model_dump()
        dialog_data_dict["user_id"] = current_user.id

        created_dialog = await ai_dialog_service.create_dialog_with_user_id(
            dialog_data_dict["chat_id"], dialog_data_dict["user_id"]
        )

        if not created_dialog:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create dialog",
            )

        return APIResponse(
            success=True,
            data=created_dialog,
            message="AI dialog created successfully",
        )
    except Exception as e:
        logger.error(f"Error creating AI dialog: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating AI dialog",
        ) from e


@router.get("/chat/{chat_id}", response_model=APIResponse[list[AIDialogResponse]])
async def get_dialogs_by_chat(
    chat_id: str,
    current_user: Optional[UserTelegramResponse] = Depends(get_current_user),
    ai_dialog_service: AIDialogService = Depends(get_ai_dialog_service),
) -> APIResponse[list[AIDialogResponse]]:
    """Get all AI dialogs for a chat."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    try:
        dialogs = await ai_dialog_service.get_dialogs_by_chat_id(chat_id)
        return APIResponse(
            success=True,
            data=dialogs,
        )
    except Exception as e:
        logger.error(f"Error getting AI dialogs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error getting AI dialogs",
        ) from e


@router.get("/{dialog_id}", response_model=APIResponse[AIDialogWithMessages])
async def get_dialog_with_requests(
    dialog_id: str,
    current_user: Optional[UserTelegramResponse] = Depends(get_current_user),
    ai_dialog_service: AIDialogService = Depends(get_ai_dialog_service),
) -> APIResponse[AIDialogWithMessages]:
    """Get AI dialog with all requests and responses."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    try:
        dialog_with_requests = await ai_dialog_service.get_dialog_with_requests(
            dialog_id
        )
        if not dialog_with_requests:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Dialog not found"
            )

        # Verify that the dialog belongs to the current user
        if dialog_with_requests.dialog.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this dialog",
            )

        return APIResponse(
            success=True,
            data=dialog_with_requests,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting AI dialog with requests: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error getting AI dialog with requests",
        ) from e


@router.post("/message", response_model=APIResponse[AIRequestResponse])
async def process_message(
    message_request: LangChainMessageRequest,
    current_user: Optional[UserTelegramResponse] = Depends(get_current_user),
    ai_dialog_service: AIDialogService = Depends(get_ai_dialog_service),
) -> APIResponse[AIRequestResponse]:
    """Process a message using LangChain and create a response."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    try:
        # Verify that the dialog belongs to the current user
        dialog = await ai_dialog_service.get_dialog(message_request.dialog_id)
        if not dialog:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Dialog not found"
            )

        if dialog.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this dialog",
            )
        user_name = f"{current_user.first_name} {current_user.last_name}"
        response = await ai_dialog_service.process_message(message_request, user_name)
        if not response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Failed to process message",
            )

        return APIResponse(
            success=True,
            data=response,
            message="Message processed successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing message",
        ) from e
