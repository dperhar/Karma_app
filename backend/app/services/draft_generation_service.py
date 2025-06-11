"""Service for managing scheduled draft comment generation."""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from app.models.user import User
from app.services.base_service import BaseService
from app.services.karma_service import KarmaService
from app.services.telethon_service import TelethonService
from app.repositories.user_repository import UserRepository
from app.services.domain.websocket_service import WebSocketService


class DraftGenerationService(BaseService):
    """Service for automated draft comment generation."""

    def __init__(
        self,
        user_repository: UserRepository,
        karma_service: KarmaService,
        telethon_service: TelethonService,
        websocket_service: WebSocketService,
    ):
        super().__init__()
        self.user_repository = user_repository
        self.karma_service = karma_service
        self.telethon_service = telethon_service
        self.websocket_service = websocket_service

    async def check_for_new_posts(self):
        """
        Scheduled task to check for new posts and generate relevant drafts.
        Implements Task 2.2 from the vision document.
        """
        try:
            self.logger.info("Starting scheduled check for new posts")
            
            # Get all users with valid telegram connections and AI profiles
            users = await self._get_active_users()
            
            if not users:
                self.logger.info("No active users found for draft generation")
                return

            self.logger.info(f"Checking for new posts for {len(users)} active users")
            
            # Process each user
            for user in users:
                try:
                    await self._process_user_for_new_posts(user)
                except Exception as e:
                    self.logger.error(f"Error processing user {user.id}: {e}", exc_info=True)
                    continue

            self.logger.info("Completed scheduled check for new posts")

        except Exception as e:
            self.logger.error(f"Error in scheduled new posts check: {e}", exc_info=True)

    async def _get_active_users(self) -> List[User]:
        """Get users who are eligible for draft generation."""
        try:
            # Get users with:
            # 1. Valid telegram connection
            # 2. Completed AI profile analysis
            # 3. Recent activity (optional)
            
            # For now, get all users and filter in code
            # In production, this would be a more sophisticated query
            all_users = await self.user_repository.get_all_users()
            
            active_users = []
            for user in all_users:
                if (user.has_valid_tg_session() and 
                    user.ai_profile and 
                    user.ai_profile.analysis_status == "COMPLETED" and
                    user.ai_profile.vibe_profile_json):
                    active_users.append(user)
            
            return active_users
            
        except Exception as e:
            self.logger.error(f"Error getting active users: {e}", exc_info=True)
            return []

    async def _process_user_for_new_posts(self, user: User):
        """Process a single user to check for new relevant posts."""
        try:
            self.logger.debug(f"Processing user {user.id} for new posts")
            
            # Get user's Telegram client
            client = await self.telethon_service.get_client_for_user(user.id)
            if not client:
                self.logger.warning(f"No Telegram client available for user {user.id}")
                return

            # Get user's subscribed channels/chats
            user_chats = await self.telethon_service.sync_chats(client, user.id, limit=20)
            
            # Check each chat for new posts
            for chat in user_chats:
                if chat.is_channel:  # Focus on channels for now
                    await self._check_channel_for_new_posts(user, client, chat)

        except Exception as e:
            self.logger.error(f"Error processing user {user.id} for new posts: {e}", exc_info=True)

    async def _check_channel_for_new_posts(self, user: User, client: Any, chat: Any):
        """Check a specific channel for new posts relevant to the user."""
        try:
            # Get recent posts (last 10 posts, within last 24 hours)
            recent_posts = await self._get_recent_channel_posts(client, chat, hours=24, limit=10)
            
            if not recent_posts:
                return

            self.logger.debug(f"Found {len(recent_posts)} recent posts in {chat.title}")

            # Check each post for relevance and generate drafts
            for post in recent_posts:
                try:
                    # Check if we already have a draft for this post
                    if await self._has_existing_draft(user.id, post.get('message_id')):
                        continue

                    # Prepare post data
                    post_data = {
                        'text': post.get('text', ''),
                        'url': f"https://t.me/{chat.username}/{post.get('message_id')}" if chat.username else None,
                        'channel': {
                            'title': chat.title,
                            'id': chat.id
                        },
                        'message_id': post.get('message_id'),
                        'date': post.get('date')
                    }

                    # Check relevance using existing KarmaService logic
                    if self.karma_service._is_post_relevant(post_data, user):
                        # Generate draft comment
                        draft = await self.karma_service.generate_draft_comment(
                            original_message_id=str(post.get('message_id')),
                            user_id=user.id,
                            post_data=post_data
                        )

                        if draft:
                            # Send WebSocket notification
                            await self.websocket_service.send_to_user(
                                user.id,
                                {
                                    "type": "new_draft_ready",
                                    "data": draft.model_dump(mode='json'),
                                    "message": f"New draft generated for post in {chat.title}"
                                }
                            )
                            
                            self.logger.info(f"Generated draft {draft.id} for user {user.id} from {chat.title}")

                except Exception as e:
                    self.logger.error(f"Error processing post {post.get('message_id', 'unknown')} for user {user.id}: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Error checking channel {chat.title} for user {user.id}: {e}", exc_info=True)

    async def _get_recent_channel_posts(
        self, 
        client: Any, 
        chat: Any, 
        hours: int = 24, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent posts from a channel."""
        try:
            posts = []
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            # Get channel entity
            channel_entity = await client.get_entity(chat.id)
            
            # Fetch recent messages
            async for message in client.iter_messages(channel_entity, limit=limit):
                if message.date < cutoff_time:
                    break  # Stop if message is too old
                    
                if message.text:  # Only consider messages with text
                    posts.append({
                        'message_id': message.id,
                        'text': message.text,
                        'date': message.date,
                        'channel_id': chat.id
                    })
            
            return posts
            
        except Exception as e:
            self.logger.error(f"Error getting recent posts from {chat.title}: {e}", exc_info=True)
            return []

    async def _has_existing_draft(self, user_id: str, message_id: int) -> bool:
        """Check if we already have a draft for this message."""
        try:
            # Get user's drafts for this message
            drafts = await self.karma_service.draft_comment_repository.get_drafts_by_message(str(message_id))
            user_drafts = [d for d in drafts if d.user_id == user_id]
            return len(user_drafts) > 0
            
        except Exception as e:
            self.logger.error(f"Error checking existing drafts: {e}", exc_info=True)
            return False

    async def generate_draft_for_post(
        self,
        user_id: str,
        post_data: Dict[str, Any],
        original_message_id: str
    ) -> Optional[Any]:
        """Generate a draft comment for a specific post (can be called manually too)."""
        try:
            user = await self.user_repository.get_user(user_id)
            if not user:
                self.logger.error(f"User not found: {user_id}")
                return None

            # Generate draft using KarmaService
            draft = await self.karma_service.generate_draft_comment(
                original_message_id=original_message_id,
                user_id=user_id,
                post_data=post_data
            )

            if draft:
                self.logger.info(f"Generated draft {draft.id} for user {user_id}")

            return draft

        except Exception as e:
            self.logger.error(f"Error generating draft for post: {e}", exc_info=True)
            return None 