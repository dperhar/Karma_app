"""API routes for the user feed."""

from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from app.dependencies import get_current_user
from app.schemas.base import APIResponse
from app.schemas.feed import FeedResponse
from app.services.feed_service import FeedService
from app.core.dependencies import container

router = APIRouter()
class SimpleMessage(BaseModel):
    message: str



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


@router.post("/generate-page", response_model=APIResponse[SimpleMessage])
async def generate_feed_page_drafts(
    current_user=Depends(get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    source: str = Query("channels"),
):
    """Queue generation of drafts for a specific feed page.

    Frontend should call this when user navigates to page > 1 or changes `source` away from default.
    Keeps API thin and defers work to Celery.
    """
    from app.tasks.tasks import generate_drafts_for_feed_page
    try:
        generate_drafts_for_feed_page.delay(user_id=current_user.id, page=page, limit=limit, source=source)
        return APIResponse(success=True, data=SimpleMessage(message="queued"), message="generation_queued")
    except Exception as e:
        return APIResponse(success=False, data=SimpleMessage(message="failed"), message=str(e))


# GET alias to avoid client preflight issues in dev and allow easy queueing from UI
@router.get("/generate-page", response_model=APIResponse[SimpleMessage])
async def generate_feed_page_drafts_get(
    current_user=Depends(get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    source: str = Query("channels"),
):
    from app.tasks.tasks import generate_drafts_for_feed_page
    try:
        generate_drafts_for_feed_page.delay(user_id=current_user.id, page=page, limit=limit, source=source)
        return APIResponse(success=True, data=SimpleMessage(message="queued"), message="generation_queued")
    except Exception as e:
        return APIResponse(success=False, data=SimpleMessage(message="failed"), message=str(e))