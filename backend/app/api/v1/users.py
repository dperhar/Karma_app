"""API routes for user management."""

import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_current_user, get_optional_user, logger
from app.schemas.base import APIResponse, MessageResponse
from app.schemas.user import UserResponse, UserUpdate
from app.core.dependencies import container
from app.tasks.tasks import analyze_vibe_profile

router = APIRouter()


@router.get("/me", response_model=APIResponse[UserResponse])
async def get_user(
    current_user: Optional[UserResponse] = Depends(get_optional_user),
) -> APIResponse[UserResponse]:
    """Get current user."""
    # Development mode fallback for when auth isn't working
    is_develop = os.getenv("IS_DEVELOP", "true").lower() == "true"
    
    if not current_user and is_develop:
        # Return a mock user for development when authentication fails
        mock_user = UserResponse(
            id="dev-user-123",
            telegram_id=109005276,  # From the frontend logs
            username="dev_user",
            first_name="Development",
            last_name="User", 
            phone_number=None,
            is_active=True
        )
        return APIResponse(
            success=True,
            data=mock_user,
            message="Development mode: mock user returned",
        )
    
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    return APIResponse(
        success=True,
        data=current_user,
    )


@router.put("/me", response_model=APIResponse[UserResponse])
async def update_user(
    user_data: UserUpdate,
    current_user: Optional[UserResponse] = Depends(get_current_user),
) -> APIResponse[UserResponse]:
    """Update current user data."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    try:
        from app.services.user_service import UserService
        user_service = container.resolve(UserService)
        updated_user = await user_service.update_user(current_user.id, user_data)
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        return APIResponse(
            success=True,
            data=updated_user,
            message="User updated successfully",
        )
    except Exception as e:
        logger.error(f"Error updating user: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating user",
        ) from e


@router.post("/me/analyze-vibe-profile", response_model=APIResponse[dict])
async def analyze_user_vibe_profile(
    current_user: Optional[UserResponse] = Depends(get_current_user),
) -> APIResponse[dict]:
    """
    Trigger analysis of user's Telegram activity to build their vibe profile.
    This is an asynchronous task.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    analyze_vibe_profile.delay(user_id=current_user.id)

    return APIResponse(
        success=True,
        data={"status": "analysis_queued"},
        message="Vibe profile analysis has been queued. You will be notified when it's complete.",
    ) 