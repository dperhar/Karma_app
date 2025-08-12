"""Service for constructing the user's feed."""

from typing import List, Optional
from datetime import datetime, timezone

from app.repositories.message_repository import MessageRepository
from app.schemas.draft_comment import DraftCommentResponse
from app.schemas.feed import FeedItem, FeedResponse, PostForFeed
from app.services.base_service import BaseService


class FeedService(BaseService):
    """Service for orchestrating the user feed."""

    def __init__(self, message_repo: MessageRepository):
        """Initialize the FeedService."""
        super().__init__()
        self.message_repo = message_repo

    async def get_user_feed(
        self, user_id: str, limit: int = 20, offset: int = 0, source: str = "channels"
    ) -> FeedResponse:
        """Orchestrates fetching the user's feed."""
        raw_feed_items = await self.message_repo.get_feed_posts(
            user_id=user_id, limit=limit, offset=offset, source=source
        )

        posts: List[PostForFeed] = []
        for item in raw_feed_items:
            post_obj = item["post"]

            def iso_utc(dt: Optional[datetime]) -> str:
                if not dt:
                    return ""
                # Treat stored datetimes as UTC and emit ISO with Z suffix
                try:
                    # If tz-aware, normalize to UTC; else assign UTC tzinfo
                    if dt.tzinfo is not None:
                        s = dt.astimezone(timezone.utc).isoformat()
                    else:
                        s = dt.replace(tzinfo=timezone.utc).isoformat()
                    return s.replace("+00:00", "Z")
                except Exception:
                    return dt.isoformat()
            post_data = PostForFeed(
                id=str(post_obj.id),
                telegram_id=post_obj.telegram_id,
                channel_telegram_id=item.get("channel_telegram_id", 0),
                text=post_obj.text,
                media_type=getattr(post_obj, 'media_type', None),
                media_url=getattr(post_obj, 'file_id', None),
                channel={
                    "id": item.get("channel_id", 0),
                    "title": item.get("channel_name", "Unknown Channel"),
                    "username": item.get("channel_username"),
                    "type": item.get("channel_type", "channel"),
                    "avatar_url": item.get("channel_avatar_url"),
                },
                date=iso_utc(post_obj.date),
                url=f"https://t.me/c/{item.get('channel_telegram_id', 0)}/{post_obj.telegram_id}",
                views=getattr(post_obj, 'views', None),
                forwards=getattr(post_obj, 'forwards', None),
                replies=getattr(post_obj, 'replies', None),
                created_at=iso_utc(getattr(post_obj, 'created_at', None) if hasattr(post_obj, 'created_at') else None),
                updated_at=iso_utc(getattr(post_obj, 'updated_at', None) if hasattr(post_obj, 'updated_at') else None),
            )
            # Convert local media path to public URL
            if post_data.media_url and not post_data.media_url.startswith('http'):
                # Ensure leading slash for StaticFiles mount
                u = post_data.media_url
                if not u.startswith('/'):
                    u = '/' + u
                post_data.media_url = u
            posts.append(post_data)

        # Calculate page number and total with accurate count
        page = (offset // limit) + 1 if limit > 0 else 1
        total = await self.message_repo.get_feed_posts_total(user_id, source=source)

        return FeedResponse(
            posts=posts,
            total=total,
            page=page,
            limit=limit
        ) 