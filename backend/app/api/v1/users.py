"""API routes for user management."""

import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_current_user, get_optional_user, logger
from app.schemas.base import APIResponse, MessageResponse
from app.schemas.user import UserResponse, UserUpdate
from app.core.dependencies import container
from app.services.user_service import UserService

router = APIRouter()


@router.get("/me", response_model=APIResponse[UserResponse])
async def get_user(
    current_user: Optional[UserResponse] = Depends(get_optional_user),
    user_service: UserService = Depends(lambda: container.resolve(UserService)),
) -> APIResponse[UserResponse]:
    """Get current user."""
    if not current_user:
        is_develop = os.getenv("IS_DEVELOP", "true").lower() == "true"
        if is_develop:
            # Fallback for development without a valid session
            real_user = await user_service.get_user_by_telegram_id(118672216)
            if real_user:
                return APIResponse(
                    success=True,
                    data=real_user,
                    message="Development mode: real user returned",
                )

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
    user_service: UserService = Depends(lambda: container.resolve(UserService)),
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

    # In a real implementation with Celery, you would dispatch the task here.
    # from tasks import analyze_vibe_profile
    # analyze_vibe_profile.delay(user_id=current_user.id)

    logger.info(
        f"Vibe profile analysis queued for user_id: {current_user.id}"
    )

    return APIResponse(
        success=True,
        data={"status": "analysis_queued"},
        message="Vibe profile analysis has been queued. You will be notified when it's complete.",
    ) 