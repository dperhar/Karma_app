"""Service for automated data fetching from Telegram."""

from datetime import datetime
from typing import Dict, List, Optional, Any

from models.user.user import User
from services.base.base_service import BaseService
from services.domain.karma_service import KarmaService
from services.domain.user_context_analysis_service import UserContextAnalysisService
from services.external.telethon_client import TelethonClient
from services.external.telethon_service import TelethonService
from services.repositories.telegram.chat_repository import ChatRepository
from services.repositories.telegram.message_repository import MessageRepository
from services.repositories.user_repository import UserRepository
from services.websocket_service import WebSocketService


class DataFetchingService(BaseService):
    """Service for automated data fetching from Telegram."""

    def __init__(
        self,
        user_repository: UserRepository,
        chat_repository: ChatRepository,
        message_repository: MessageRepository,
        telethon_client: TelethonClient,
        telethon_service: TelethonService,
        karma_service: KarmaService,
        user_context_analysis_service: UserContextAnalysisService,
        websocket_service: WebSocketService,
    ):
        super().__init__()
        self.user_repository = user_repository
        self.chat_repository = chat_repository
        self.message_repository = message_repository
        self.telethon_client = telethon_client
        self.telethon_service = telethon_service
        self.karma_service = karma_service
        self.user_context_analysis_service = user_context_analysis_service
        self.websocket_service = websocket_service

    async def fetch_new_data_for_all_users(self):
        """Fetch new data for all users with valid Telegram sessions."""
        try:
            self.logger.info("Starting automated data fetch for all users")
            
            # Get all users with valid Telegram sessions
            users = await self.user_repository.get_users()
            valid_users = [user for user in users if user.has_valid_tg_session()]
            
            self.logger.info(f"Found {len(valid_users)} users with valid Telegram sessions")
            
            for user in valid_users:
                try:
                    await self.fetch_new_data_for_user(user)
                except Exception as e:
                    self.logger.error(f"Error fetching data for user {user.id}: {e}", exc_info=True)
                    continue
            
            self.logger.info("Completed automated data fetch for all users")
            
        except Exception as e:
            self.logger.error(f"Error in automated data fetch: {e}", exc_info=True)

    async def fetch_new_data_for_user(self, user: User):
        """Fetch new data for a specific user."""
        try:
            self.logger.info(f"Fetching new data for user {user.id} ({user.username})")
            
            # Create Telegram client for user
            client = await self.telethon_client.create_client(user.telegram_session_string)
            if not client:
                self.logger.error(f"Failed to create Telegram client for user {user.id}")
                return

            # Check if user needs context analysis (first-time use or incomplete analysis)
            if await self._should_analyze_user_context(user):
                try:
                    self.logger.info(f"Starting context analysis for user {user.id}")
                    analysis_result = await self.user_context_analysis_service.analyze_user_context(client, user.id)
                    if analysis_result.get("status") == "completed":
                        self.logger.info(f"Context analysis completed for user {user.id}")
                        # Send notification about completed analysis
                        await self._send_context_analysis_notification(user.id, "completed")
                    else:
                        self.logger.warning(f"Context analysis failed for user {user.id}: {analysis_result.get('reason')}")
                        await self._send_context_analysis_notification(user.id, "failed")
                except Exception as e:
                    self.logger.error(f"Error during context analysis for user {user.id}: {e}")
                    await self._send_context_analysis_notification(user.id, "failed")

            # Get last message IDs for all user's chats
            chat_last_message_ids = await self._get_chat_last_message_ids(user.id)
            
            # Fetch new posts using TelethonService
            result = await self.telethon_service.get_new_user_posts(
                client=client,
                user_id=user.id,
                chat_last_message_ids=chat_last_message_ids,
                limit=user.telegram_messages_load_limit or 100
            )
            
            new_posts = result.get('posts', [])
            updated_last_message_ids = result.get('updated_last_message_ids', {})
            
            self.logger.info(f"Found {len(new_posts)} new posts for user {user.id}")
            
            if new_posts:
                # Store new posts and trigger AI comment generation
                stored_posts = await self._store_new_posts(new_posts, user.id)
                
                # Update last message IDs for chats
                await self._update_chat_last_message_ids(updated_last_message_ids)
                
                # Generate AI comments for relevant posts
                for post_data in stored_posts:
                    try:
                        await self.karma_service.generate_draft_comment(
                            original_message_id=post_data.get('stored_message_id'),
                            user_id=user.id,
                            post_data=post_data
                        )
                    except Exception as e:
                        self.logger.error(f"Error generating AI comment for post: {e}")
                        continue
                
                # Send WebSocket notification about new posts
                await self._send_new_posts_notification(user.id, len(new_posts))
            
            await client.disconnect()
            
        except Exception as e:
            self.logger.error(f"Error fetching data for user {user.id}: {e}", exc_info=True)

    async def _get_chat_last_message_ids(self, user_id: str) -> Dict[int, int]:
        """Get last fetched message IDs for all user's chats."""
        try:
            chats = await self.chat_repository.get_user_chats(user_id)
            chat_last_message_ids = {}
            
            for chat in chats:
                if chat.last_fetched_message_telegram_id:
                    chat_last_message_ids[chat.telegram_id] = chat.last_fetched_message_telegram_id
            
            return chat_last_message_ids
            
        except Exception as e:
            self.logger.error(f"Error getting chat last message IDs: {e}")
            return {}

    async def _store_new_posts(self, posts: List[Dict[str, Any]], user_id: str) -> List[Dict[str, Any]]:
        """Store new posts as messages in the database."""
        try:
            stored_posts = []
            
            for post_data in posts:
                try:
                    # Convert post data to message format
                    message_data = self._convert_post_to_message(post_data, user_id)
                    
                    # Store message
                    # Note: This would need to be implemented properly with the message repository
                    # For now, we'll just add the post_data to stored_posts
                    message_data['stored_message_id'] = f"temp_{post_data['id']}"
                    stored_posts.append(message_data)
                    
                except Exception as e:
                    self.logger.error(f"Error storing post {post_data.get('id')}: {e}")
                    continue
            
            return stored_posts
            
        except Exception as e:
            self.logger.error(f"Error storing new posts: {e}")
            return []

    async def _update_chat_last_message_ids(self, updated_last_message_ids: Dict[int, int]):
        """Update last fetched message IDs for chats."""
        try:
            for chat_telegram_id, last_message_id in updated_last_message_ids.items():
                # Update chat with new last message ID
                await self.chat_repository.update_chat_last_fetched_message(
                    chat_telegram_id, 
                    last_message_id,
                    datetime.now()
                )
                
        except Exception as e:
            self.logger.error(f"Error updating chat last message IDs: {e}")

    def _convert_post_to_message(self, post_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Convert post data to message format."""
        return {
            'telegram_id': post_data.get('telegram_id'),
            'channel_telegram_id': post_data.get('channel_telegram_id'),
            'text': post_data.get('text', ''),
            'date': post_data.get('date'),
            'sender_id': post_data.get('sender_id'),
            'media_type': post_data.get('media_type'),
            'views': post_data.get('views'),
            'forwards': post_data.get('forwards'),
            'reactions': post_data.get('reactions', []),
            'channel': post_data.get('channel', {}),
            'user_id': user_id
        }

    async def _should_analyze_user_context(self, user: User) -> bool:
        """Check if user needs context analysis."""
        # If no analysis ever done
        if not user.last_context_analysis_at:
            return True
        
        # If analysis failed or is pending
        if user.context_analysis_status in ["FAILED", "PENDING"]:
            return True
            
        # If analysis completed but missing required fields
        if user.context_analysis_status == "COMPLETED":
            if not user.user_system_prompt or not user.persona_style_description:
                return True
        
        return False

    async def _send_context_analysis_notification(self, user_id: str, status: str):
        """Send WebSocket notification about context analysis status."""
        try:
            await self.websocket_service.send_user_notification(
                user_id=user_id,
                event="user_context_analysis",
                data={
                    "status": status,
                    "timestamp": datetime.now().isoformat()
                }
            )
        except Exception as e:
            self.logger.error(f"Error sending context analysis notification: {e}")

    async def _send_new_posts_notification(self, user_id: str, post_count: int):
        """Send WebSocket notification about new posts."""
        try:
            await self.websocket_service.send_user_notification(
                user_id=user_id,
                event="new_telegram_posts",
                data={
                    "count": post_count,
                    "timestamp": datetime.now().isoformat()
                }
            )
        except Exception as e:
            self.logger.error(f"Error sending new posts notification: {e}")
            # Don't raise the exception to prevent breaking the main flow 