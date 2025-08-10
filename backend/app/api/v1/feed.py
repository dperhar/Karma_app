"""API routes for the user feed."""

from typing import Optional
from fastapi import APIRouter, Depends, Query

from app.dependencies import get_current_user
from app.schemas.base import APIResponse
from app.schemas.feed import FeedResponse
from app.services.feed_service import FeedService
from app.core.dependencies import container

router = APIRouter()


def get_feed_service() -> FeedService:
    return container.resolve(FeedService)


@router.get("", response_model=APIResponse[FeedResponse])
async def get_feed(
    current_user=Depends(get_current_user),
    feed_service: FeedService = Depends(get_feed_service),
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    limit: int = Query(20, ge=1, le=100, description="Number of posts per page"),
) -> APIResponse[FeedResponse]:
    """Get the user's personalized feed of posts and drafts."""
    # Convert page to offset for the service
    offset = (page - 1) * limit
    
    feed = await feed_service.get_user_feed(
        user_id=current_user.id,
        limit=limit,
        offset=offset
    )
    return APIResponse(success=True, data=feed, message="Feed retrieved successfully") 