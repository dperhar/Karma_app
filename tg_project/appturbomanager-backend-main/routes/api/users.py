"""API routes for user management."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from models.base.schemas import APIResponse
from models.user.schemas import (
    UserResponse,
    UserTelegramResponse,
    UserUpdate,
)
from routes.dependencies import get_current_user, logger
from services.dependencies import get_user_service
from services.domain.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=APIResponse[UserResponse])
async def get_user(
    current_user: Optional[UserTelegramResponse] = Depends(get_current_user),
) -> APIResponse[UserResponse]:
    """Get current user."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    response_user_data = UserResponse.model_validate(current_user)
    return APIResponse(
        success=True,
        data=response_user_data,
    )


@router.put("/me", response_model=APIResponse[UserResponse])
async def update_user(
    user_data: UserUpdate,
    current_user: Optional[UserTelegramResponse] = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> APIResponse[UserResponse]:
    """Update current user data."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    try:
        updated_user = await user_service.update_user(current_user.id, user_data)
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        response_user_data = UserResponse.model_validate(updated_user)
        return APIResponse(
            success=True,
            data=response_user_data,
            message="User updated successfully",
        )
    except Exception as e:
        logger.error(f"Error updating user: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating user",
        ) from e
