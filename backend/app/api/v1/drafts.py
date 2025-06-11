"""API routes for draft comment management."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.models.draft_comment import DraftStatus
from app.schemas.base import APIResponse
from app.dependencies import get_current_user, logger
from schemas.draft_comment import (
    DraftCommentResponse,
    DraftCommentUpdate,
)
from app.schemas.negative_feedback import RegenerateRequest
from app.core.dependencies import container
from app.services.karma_service import KarmaService

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


@router.post("/{draft_id}/post", response_model=APIResponse[DraftCommentResponse])
async def post_draft_comment(
    draft_id: str,
    current_user=Depends(get_current_user),
    karma_service: KarmaService = Depends(get_karma_service),
) -> APIResponse[DraftCommentResponse]:
    """Post an approved draft comment to Telegram."""
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

        # For now, this is a placeholder - real implementation would need
        # a proper way to get the user's Telegram client
        # posted_draft = await karma_service.post_draft_comment(draft_id, client)
        
        # Instead, we'll just mark it as approved for now
        posted_draft = await karma_service.approve_draft_comment(draft_id)
        
        if not posted_draft:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Draft comment not found"
            )

        return APIResponse(
            success=True,
            data=posted_draft,
            message="Draft comment posting initiated (placeholder implementation)"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error posting draft comment: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error posting draft comment"
        ) from e


@router.post("/{draft_id}/regenerate", response_model=APIResponse[DraftCommentResponse])
async def regenerate_draft_comment(
    draft_id: str,
    regenerate_request: RegenerateRequest,
    current_user=Depends(get_current_user),
    karma_service: KarmaService = Depends(get_karma_service),
) -> APIResponse[DraftCommentResponse]:
    """Regenerate a draft comment after negative feedback (Not My Vibe)."""
    try:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )

        # Verify ownership
        drafts = await karma_service.get_drafts_by_user(current_user.id)
        draft = next((d for d in drafts if d.id == draft_id), None)
        
        if not draft:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Draft comment not found"
            )

        # Regenerate the draft with negative feedback
        regenerated_draft = await karma_service.regenerate_draft_with_feedback(
            draft_id, 
            regenerate_request
        )
        
        if not regenerated_draft:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to regenerate draft comment"
            )

        return APIResponse(
            success=True,
            data=regenerated_draft,
            message="Draft comment regenerated successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error regenerating draft comment: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error regenerating draft comment"
        ) from e 