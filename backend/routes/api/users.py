"""API routes for user management."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from models.base.schemas import APIResponse
from models.user.schemas import (
    UserResponse,
    UserUpdate,
)
from routes.dependencies import get_current_user, get_optional_user, logger
from services.dependencies import get_user_service, get_user_context_analysis_service, get_telethon_client, container
from services.domain.user_service import UserService
from services.domain.user_context_analysis_service import UserContextAnalysisService
from services.external.telethon_client import TelethonClient

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=APIResponse[UserResponse])
async def get_user(
    current_user: Optional[UserResponse] = Depends(get_optional_user),
    user_service: UserService = Depends(lambda: container.resolve(UserService))
) -> APIResponse[UserResponse]:
    """Get current user."""
    if not current_user:
        # В development режиме возвращаем mock пользователя
        import os
        is_develop = os.getenv("IS_DEVELOP", "true").lower() == "true"
        if is_develop:
            # Сначала попробуем найти пользователя с активной сессией
            users = await user_service.get_users()
            active_session_user = None
            for user in users:
                if user.has_valid_tg_session:
                    active_session_user = user
                    break
            
            if active_session_user:
                return APIResponse(
                    success=True,
                    data=active_session_user,
                    message="Development mode: real user returned"
                )
            
            # Если пользователя с активной сессией нет, попробуем найти по telegram_id из initData
            real_user = await user_service.get_user_by_telegram_id(118672216)
            if real_user:
                return APIResponse(
                    success=True,
                    data=real_user,
                    message="Development mode: real user returned"
                )
            
            # Если реального пользователя нет - создаем mock с реальным ID
            mock_user = UserResponse(
                id="972e2892ea124bb08e0d638817572b58",  # Реальный ID из базы
                telegram_id=118672216,
                first_name="Development",
                last_name="User",
                username="dev_user",
                email=None,
                telegram_chats_load_limit=100,
                telegram_messages_load_limit=100,
                preferred_ai_model="gpt-4.1-mini",
                preferred_message_context_size=50,
                persona_name="Developer",
                persona_style_description="Helpful development persona",
                persona_interests_json=None,
                user_system_prompt=None,
                last_context_analysis_at=None,
                context_analysis_status="pending",
                created_at="2025-05-28T13:00:00Z",
                updated_at="2025-05-28T13:00:00Z"
            )
            return APIResponse(
                success=True,
                data=mock_user,
                message="Development mode: mock user returned"
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


@router.post("/me/analyze-context", response_model=APIResponse[dict])
async def analyze_user_context(
    current_user: Optional[UserResponse] = Depends(get_current_user),
    user_context_analysis_service: UserContextAnalysisService = Depends(get_user_context_analysis_service),
    telethon_client: TelethonClient = Depends(get_telethon_client),
) -> APIResponse[dict]:
    """Trigger analysis of user's Telegram activity to build their digital twin."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    try:
        # Get user from DB to check telegram session
        user_model = await user_context_analysis_service.user_repository.get_user(current_user.id)
        if not user_model or not user_model.has_valid_tg_session():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="User must have a valid Telegram session to analyze context"
            )

        # Create Telegram client
        client = await telethon_client.create_client(user_model.telegram_session_string)
        if not client:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create Telegram client"
            )

        # Start context analysis
        analysis_result = await user_context_analysis_service.analyze_user_context(
            client, current_user.id
        )
        
        await client.disconnect()

        if analysis_result.get("status") == "completed":
            return APIResponse(
                success=True,
                data=analysis_result,
                message="User context analysis completed successfully"
            )
        else:
            return APIResponse(
                success=False,
                data=analysis_result,
                message=f"User context analysis failed: {analysis_result.get('reason', 'Unknown error')}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing user context: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error analyzing user context",
        ) from e
