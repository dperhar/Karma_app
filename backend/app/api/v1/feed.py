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
    queue_missing: bool = Query(False, description="If true, queue AI draft generation for posts on this page that lack drafts"),
) -> APIResponse[FeedResponse]:
    """Get the user's personalized feed of posts and drafts."""
    # Convert page to offset for the service
    offset = (page - 1) * limit
    
    feed = await feed_service.get_user_feed(
        user_id=current_user.id,
        limit=limit,
        offset=offset
    )

    # Thin dispatch: queue missing drafts for posts on this page
    if queue_missing and feed and feed.posts:
        try:
            from app.tasks.tasks import generate_draft_for_post
            for p in feed.posts:
                # If no draft_meta, queue generation
                if not getattr(p, 'draft_meta', None):
                    post_data = {
                        "original_message_id": p.id,
                        "original_post_content": p.text,
                        "original_post_url": p.url,
                        "channel_telegram_id": p.channel_telegram_id,
                        "force_generate": True,
                    }
                    generate_draft_for_post.delay(user_id=current_user.id, post_data=post_data)
        except Exception:
            pass
    return APIResponse(success=True, data=feed, message="Feed retrieved successfully") 