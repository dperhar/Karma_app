"""API routes for the user feed."""

from typing import Optional
from fastapi import APIRouter, Depends, Query, Request

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
    request: Request,
    current_user=Depends(get_current_user),
    feed_service: FeedService = Depends(get_feed_service),
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    limit: int = Query(20, ge=1, le=100, description="Number of posts per page"),
    source: str = Query(
        "channels",
        description="Source filter: 'channels' (default), 'groups', or 'both'",
    ),
) -> APIResponse[FeedResponse]:
    """Get the user's personalized feed of posts and drafts."""
    # Convert page to offset for the service
    offset = (page - 1) * limit
    
    # Normalize legacy values for backward compatibility
    source_norm = source.lower()
    if source_norm == "combined":
        source_norm = "both"
    elif source_norm == "channel":
        source_norm = "channels"
    elif source_norm == "supergroup":
        source_norm = "groups"

    feed = await feed_service.get_user_feed(
        user_id=current_user.id,
        limit=limit,
        offset=offset,
        source=source_norm,
    )
    # Prefix media_url with backend origin so frontend can load from port 8000
    try:
        base_origin = f"{request.url.scheme}://{request.headers.get('host')}"
        for p in getattr(feed, 'posts', []) or []:
            if getattr(p, 'media_url', None) and not str(p.media_url).startswith(('http://', 'https://')):
                url = str(p.media_url)
                if not url.startswith('/'):
                    url = '/' + url
                p.media_url = base_origin + url
    except Exception:
        pass
    return APIResponse(success=True, data=feed, message="Feed retrieved successfully") 