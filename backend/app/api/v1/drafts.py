"""API routes for draft comment management."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.models.draft_comment import DraftStatus
from app.schemas.base import APIResponse
from app.dependencies import get_current_user, logger
from app.schemas.draft_comment import (
    DraftCommentResponse,
    DraftCommentUpdate,
    RegenerateRequest,
)
from app.core.dependencies import container
from app.services.karma_service import KarmaService
from app.tasks.tasks import generate_draft_for_post

router = APIRouter(prefix="/draft-comments", tags=["draft-comments"])


def get_karma_service() -> KarmaService:
    """Get KarmaService instance."""
    return container.resolve(KarmaService)


@router.get("", response_model=APIResponse[List[DraftCommentResponse]])
async def get_user_drafts(
    status: Optional[DraftStatus] = None,
    current_user=Depends(get_current_user),
    karma_service: KarmaService = Depends(get_karma_service),
) -> APIResponse[List[DraftCommentResponse]]:
    """Get draft comments for current user."""
    try:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )

        drafts = await karma_service.get_drafts_by_user(current_user.id, status)
        
        return APIResponse(
            success=True,
            data=drafts,
            message=f"Retrieved {len(drafts)} draft comments"
        )

    except Exception as e:
        logger.error(f"Error retrieving draft comments: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving draft comments"
        ) from e


@router.get("/{draft_id}", response_model=APIResponse[DraftCommentResponse])
async def get_draft_comment(
    draft_id: str,
    current_user=Depends(get_current_user),
    karma_service: KarmaService = Depends(get_karma_service),
) -> APIResponse[DraftCommentResponse]:
    """Get a specific draft comment."""
    try:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )

        # Get draft and verify ownership
        drafts = await karma_service.get_drafts_by_user(current_user.id)
        draft = next((d for d in drafts if d.id == draft_id), None)
        
        if not draft:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Draft comment not found"
            )

        return APIResponse(
            success=True,
            data=draft,
            message="Draft comment retrieved successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving draft comment: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving draft comment"
        ) from e


@router.put("/{draft_id}", response_model=APIResponse[DraftCommentResponse])
async def update_draft_comment(
    draft_id: str,
    update_data: DraftCommentUpdate,
    current_user=Depends(get_current_user),
    karma_service: KarmaService = Depends(get_karma_service),
) -> APIResponse[DraftCommentResponse]:
    """Update a draft comment."""
    try:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )

        # Verify ownership
        drafts = await karma_service.get_drafts_by_user(current_user.id)
        if not any(d.id == draft_id for d in drafts):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Draft comment not found"
            )

        updated_draft = await karma_service.update_draft_comment(draft_id, update_data)
        
        if not updated_draft:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Draft comment not found"
            )

        return APIResponse(
            success=True,
            data=updated_draft,
            message="Draft comment updated successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating draft comment: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating draft comment"
        ) from e


@router.post("/{draft_id}/approve", response_model=APIResponse[DraftCommentResponse])
async def approve_draft_comment(
    draft_id: str,
    current_user=Depends(get_current_user),
    karma_service: KarmaService = Depends(get_karma_service),
) -> APIResponse[DraftCommentResponse]:
    """Approve a draft comment for posting."""
    try:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )

        # Verify ownership
        drafts = await karma_service.get_drafts_by_user(current_user.id)
        if not any(d.id == draft_id for d in drafts):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Draft comment not found"
            )

        approved_draft = await karma_service.approve_draft_comment(draft_id)
        
        if not approved_draft:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Draft comment not found"
            )

        return APIResponse(
            success=True,
            data=approved_draft,
            message="Draft comment approved successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving draft comment: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error approving draft comment"
        ) from e


class GenerateDraftRequest(BaseModel):
    """Request body for generating a draft for a specific Telegram post."""
    post_telegram_id: int
    channel_telegram_id: int


@router.post("/generate", response_model=APIResponse[dict])
async def generate_draft_comment_for_post(
    body: GenerateDraftRequest,
    current_user=Depends(get_current_user),
):
    """Queue draft generation for a post via Celery.

    This endpoint only validates input and dispatches a background task, keeping the API thin.
    """
    try:
        if not current_user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

        # Minimal, serializable payload. Task will fetch any additional context it needs.
        post_data = {
            "original_message_id": "unknown",  # DB message ID may not exist; task can still proceed
            "original_message_telegram_id": int(body.post_telegram_id),
            "channel_telegram_id": int(body.channel_telegram_id),
            # Encourage generation even if relevance filter would otherwise skip
            "force_generate": True,
        }
        generate_draft_for_post.delay(user_id=current_user.id, post_data=post_data)
        return APIResponse(success=True, data={"status": "queued"}, message="Draft generation queued")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to queue draft generation: {e!s}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to queue draft generation")


@router.post("/{draft_id}/post", response_model=APIResponse[DraftCommentResponse])
async def post_draft_comment(
    draft_id: str,
    current_user=Depends(get_current_user),
    karma_service: KarmaService = Depends(get_karma_service),
) -> APIResponse[DraftCommentResponse]:
    """Post a draft comment to Telegram and return updated draft."""
    try:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )

        # Verify ownership
        drafts = await karma_service.get_drafts_by_user(current_user.id)
        if not any(d.id == draft_id for d in drafts):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Draft comment not found"
            )

        # Delegate to service to actually post to Telegram and persist status
        result = await karma_service.post_draft_comment(draft_id=draft_id, user_id=current_user.id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to post draft to Telegram"
            )

        return APIResponse(success=True, data=result, message="Draft posted to Telegram")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error posting draft comment: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error posting draft comment"
        ) from e


@router.post("/{draft_id}/regenerate", response_model=APIResponse[dict])
async def regenerate_draft_comment(
    draft_id: str,
    regenerate_request: RegenerateRequest,
    current_user=Depends(get_current_user),
) -> APIResponse[dict]:
    """Regenerate a draft comment after negative feedback (Not My Vibe)."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )

    # Force generation on regeneration so we always produce a new draft
    payload = regenerate_request.post_data.model_dump()
    payload.setdefault("force_generate", True)
    generate_draft_for_post.delay(
        user_id=current_user.id,
        post_data=payload,
        rejected_draft_id=draft_id,
        rejection_reason=regenerate_request.rejection_reason,
    )

    return APIResponse(
        success=True,
        data={"status": "regeneration_queued"},
        message="Draft comment regeneration has been queued.",
    ) 