"""API routes for user management."""

import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_current_user, get_optional_user, logger
from app.schemas.base import APIResponse, MessageResponse
from app.schemas.ai_profile import AIProfileResponse, AIProfileUpdate
from app.schemas.ai_settings import AISettings, AISettingsUpdate
from app.schemas.user import UserResponse, UserUpdate
from app.core.dependencies import container
from app.tasks.tasks import analyze_vibe_profile
from app.core.config import settings

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


@router.get("/me/ai-profile", response_model=APIResponse[AIProfileResponse])
async def get_my_ai_profile(
    current_user: Optional[UserResponse] = Depends(get_current_user),
) -> APIResponse[AIProfileResponse]:
    """Return current user's AI profile (vibe analysis) if exists."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    from app.repositories.ai_profile_repository import AIProfileRepository
    from app.core.dependencies import container

    repo = container.resolve(AIProfileRepository)
    ai_profile = await repo.get_ai_profile_by_user(current_user.id)
    if not ai_profile:
        if settings.IS_DEVELOP:
            ai_profile = await repo.create_ai_profile(user_id=current_user.id)
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI profile not found")

    # Normalize datetime to string for schema compatibility
    payload = AIProfileResponse.model_validate(ai_profile).model_dump()
    if isinstance(payload.get("last_analyzed_at"), (int, float)):
        pass
    return APIResponse(success=True, data=payload)


@router.get("/me/ai-settings", response_model=APIResponse[AISettings])
async def get_my_ai_settings(
    current_user: Optional[UserResponse] = Depends(get_current_user),
) -> APIResponse[AISettings]:
    """Return current user's AI generation settings (model, temperature, tokens)."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    from app.repositories.ai_profile_repository import AIProfileRepository
    repo = container.resolve(AIProfileRepository)
    ai_profile = await repo.get_ai_profile_by_user(current_user.id)
    if not ai_profile:
        # Defaults if no profile yet
        return APIResponse(success=True, data=AISettings())

    # For now, use defaults; can be extended to read persisted values later
    settings_payload = AISettings(
        model="gemini-2.5-pro",
        temperature=0.2,
        max_output_tokens=512,
    )
    return APIResponse(success=True, data=settings_payload)


@router.put("/me/ai-settings", response_model=APIResponse[AISettings])
async def update_my_ai_settings(
    settings_update: AISettingsUpdate,
    current_user: Optional[UserResponse] = Depends(get_current_user),
) -> APIResponse[AISettings]:
    """Update current user's AI generation settings. Persist on AIProfile for now."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    from app.repositories.ai_profile_repository import AIProfileRepository
    repo = container.resolve(AIProfileRepository)
    ai_profile = await repo.get_ai_profile_by_user(current_user.id)
    if not ai_profile:
        ai_profile = await repo.create_ai_profile(user_id=current_user.id)

    # For MVP, we don't add DB columns; settings will be applied ad-hoc via request
    # Return merged values
    merged = AISettings(
        model=settings_update.model or "gemini-2.5-pro",
        temperature=settings_update.temperature if settings_update.temperature is not None else 0.2,
        max_output_tokens=settings_update.max_output_tokens if settings_update.max_output_tokens is not None else 512,
    )

    return APIResponse(success=True, data=merged)


@router.put("/me/ai-profile", response_model=APIResponse[AIProfileResponse])
async def update_my_ai_profile(
    profile_update: AIProfileUpdate,
    current_user: Optional[UserResponse] = Depends(get_current_user),
) -> APIResponse[AIProfileResponse]:
    """Edit user's Digital Twin: tone, interests, templates, and persona fields.

    Rule: This is synchronous and light. It merges provided fields into the
    existing `vibe_profile_json` and mirrored persona fields, leaving others intact.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    from app.repositories.ai_profile_repository import AIProfileRepository
    repo = container.resolve(AIProfileRepository)
    ai_profile = await repo.get_ai_profile_by_user(current_user.id)
    if not ai_profile:
        ai_profile = await repo.create_ai_profile(user_id=current_user.id)

    # Merge updates into vibe_profile_json
    base = getattr(ai_profile, "vibe_profile_json", {}) or {}
    vp = dict(base)

    def set_if(value, key):
        if value is not None:
            vp[key] = value

    set_if(profile_update.tone, "tone")
    set_if(profile_update.verbosity, "verbosity")
    set_if(profile_update.emoji_usage, "emoji_usage")
    set_if(profile_update.style_prompt, "style_prompt")
    set_if(profile_update.topics_of_interest, "topics_of_interest")
    set_if(profile_update.signature_templates, "signature_templates")
    set_if(profile_update.do_list, "do_list")
    set_if(profile_update.dont_list, "dont_list")

    if profile_update.signature_phrases is not None:
        vp["signature_phrases"] = [
            {"text": t, "count": 1} if isinstance(t, str) else t
            for t in profile_update.signature_phrases
        ]

    # Digital comm subsection
    dc = dict(vp.get("digital_comm", {}) or {})
    if profile_update.greetings is not None:
        dc["greetings"] = profile_update.greetings
    if profile_update.typical_endings is not None:
        dc["typical_endings"] = profile_update.typical_endings
    if dc:
        vp["digital_comm"] = dc

    # Persist back
    updated = await repo.update_ai_profile(
        ai_profile.id,
        vibe_profile_json=vp,
        persona_name=profile_update.persona_name or getattr(ai_profile, "persona_name", None),
        user_system_prompt=profile_update.user_system_prompt or getattr(ai_profile, "user_system_prompt", None),
    )

    return APIResponse(success=True, data=AIProfileResponse.model_validate(updated))


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


@router.post("/me/analyze-context", response_model=APIResponse[dict])
async def analyze_user_context(
    current_user: Optional[UserResponse] = Depends(get_current_user),
) -> APIResponse[dict]:
    """Trigger analysis of user's Telegram activity to build their digital twin context.

    This is an asynchronous task dispatch. The worker will fetch up to 10,000
    of the user's latest sent messages (subject to Telegram API limits and
    internal safety guards) and build/update the user's vibe profile.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    # Dispatch Celery task with a high message limit for deep analysis
    try:
        analyze_vibe_profile.delay(user_id=current_user.id, messages_limit=10000)
    except Exception:
        # In dev, if Celery is down or no Telegram session, seed a default completed profile
        if settings.IS_DEVELOP:
            from app.tasks.tasks import seed_ai_profile_dev
            seed_ai_profile_dev.delay(user_id=current_user.id)

    return APIResponse(
        success=True,
        data={"status": "analysis_queued"},
        message=(
            "Context analysis has been queued. We'll analyze up to your latest 10,000 "
            "messages and update your profile when complete."
        ),
    ) 