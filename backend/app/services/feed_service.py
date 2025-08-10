"""Service for constructing the user's feed."""

from typing import List, Optional

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
            post_data = PostForFeed(
                id=str(post_obj.id),
                telegram_id=post_obj.telegram_id,
                channel_telegram_id=item.get("channel_telegram_id", 0),
                text=post_obj.text,
                channel={
                    "id": item.get("channel_id", 0),
                    "title": item.get("channel_name", "Unknown Channel"),
                    "username": item.get("channel_username"),
                    "type": item.get("channel_type", "channel"),
                    "avatar_url": item.get("channel_avatar_url"),
                },
                date=post_obj.date.isoformat() if post_obj.date else "",
                url=f"https://t.me/c/{item.get('channel_telegram_id', 0)}/{post_obj.telegram_id}",
                views=getattr(post_obj, 'views', None),
                forwards=getattr(post_obj, 'forwards', None),
                replies=getattr(post_obj, 'replies', None),
                created_at=post_obj.created_at.isoformat() if hasattr(post_obj, 'created_at') and post_obj.created_at else "",
                updated_at=post_obj.updated_at.isoformat() if hasattr(post_obj, 'updated_at') and post_obj.updated_at else "",
            )
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