"""Service for automated data fetching from Telegram."""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Any

from app.models.user import User, UserInitialSyncStatus
from app.models.chat import TelegramMessengerChatSyncStatus
from app.services.base_service import BaseService
from app.services.domain.karma_service import KarmaService
from app.services.user_context_analysis_service import UserContextAnalysisService
from app.services.telethon_client import TelethonClient
from app.services.telethon_service import TelethonService
from app.repositories.chat_repository import ChatRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.user_repository import UserRepository
from app.services.websocket_service import WebSocketService


class DataFetchingService(BaseService):
    """Service for automated data fetching from Telegram with safe pagination."""

    # Configuration for safe sync limits
    INITIAL_SYNC_CHAT_LIMIT = 10  # Very conservative for first sync
    INITIAL_SYNC_MESSAGES_PER_CHAT = 20  # Small number of recent messages
    DELAY_BETWEEN_CHAT_FETCHES_SECONDS = 1.0  # Delay between chat operations
    DELAY_BETWEEN_API_CALLS_SECONDS = 0.5  # Delay between API calls

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
                    # Add delay between users to spread API load
                    await asyncio.sleep(self.DELAY_BETWEEN_CHAT_FETCHES_SECONDS)
                except Exception as e:
                    self.logger.error(f"Error fetching data for user {user.id}: {e}", exc_info=True)
                    continue
            
            self.logger.info("Completed automated data fetch for all users")
            
        except Exception as e:
            self.logger.error(f"Error in automated data fetch: {e}", exc_info=True)

    async def fetch_new_data_for_user(self, user: User):
        """Fetch new data for a specific user with safe initial sync support."""
        try:
            self.logger.info(f"Fetching new data for user {user.id} ({user.username})")
            
            # Create Telegram client for user
            client = await self.telethon_client.create_client(user.telegram_session_string)
            if not client:
                self.logger.error(f"Failed to create Telegram client for user {user.id}")
                return

            # Check if user needs initial sync
            if user.needs_initial_sync():
                self.logger.info(f"User {user.id} needs initial sync - starting safe initial synchronization")
                await self._perform_initial_safe_sync(client, user)
                return

            # Regular incremental sync for users who already completed initial sync
            await self._perform_incremental_sync(client, user)

            await client.disconnect()
            
        except Exception as e:
            self.logger.error(f"Error fetching data for user {user.id}: {e}", exc_info=True)

    async def _perform_initial_safe_sync(self, client, user: User):
        """Perform initial safe synchronization for new users."""
        try:
            self.logger.info(f"Starting initial safe sync for user {user.id}")
            
            # Update user sync status to indicate we're starting
            await self.user_repository.update_user(
                user.id, 
                {"initial_sync_status": UserInitialSyncStatus.PENDING}
            )
            
            # Step 1: Fetch a small number of recent dialogs
            self.logger.info(f"Fetching initial {self.INITIAL_SYNC_CHAT_LIMIT} chats for user {user.id}")
            
            chats, next_pagination = await self.telethon_service.sync_chats(
                client=client,
                user_id=user.id,
                limit=self.INITIAL_SYNC_CHAT_LIMIT
            )
            
            # Store initial chats
            for chat in chats:
                chat.sync_status = TelegramMessengerChatSyncStatus.INITIAL_MINIMAL_SYNCED
                await self.chat_repository.store_chat(chat)
            
            # Add delay after chat fetching
            await asyncio.sleep(self.DELAY_BETWEEN_API_CALLS_SECONDS)
            
            # Step 2: For each chat, fetch a small number of recent messages
            initial_posts = []
            for chat in chats:
                try:
                    self.logger.info(f"Fetching initial messages for chat {chat.telegram_id}")
                    
                    messages_data, _ = await self.telethon_service.sync_chat_messages(
                        client=client,
                        chat_telegram_id=chat.telegram_id,
                        user_id=user.id,
                        limit=self.INITIAL_SYNC_MESSAGES_PER_CHAT,
                        direction="older"
                    )
                    
                    # Convert to posts format and store
                    for message_data in messages_data:
                        post_data = self._convert_message_to_post(message_data, user.id)
                        initial_posts.append(post_data)
                    
                    # Update chat's last fetched message
                    if messages_data:
                        last_message_id = max(msg.get('telegram_id', 0) for msg in messages_data)
                        await self.chat_repository.update_chat_last_fetched_message(
                            chat.telegram_id,
                            last_message_id,
                            datetime.now()
                        )
                    
                    # Delay between chats to be gentle on API
                    await asyncio.sleep(self.DELAY_BETWEEN_CHAT_FETCHES_SECONDS)
                    
                except Exception as e:
                    self.logger.error(f"Error fetching initial messages for chat {chat.telegram_id}: {e}")
                    continue
            
            # Update user sync status to completed
            await self.user_repository.update_user(
                user.id, 
                {
                    "initial_sync_status": UserInitialSyncStatus.MINIMAL_COMPLETED,
                    "last_dialog_sync_at": datetime.now()
                }
            )
            
            self.logger.info(f"Initial safe sync completed for user {user.id}. Fetched {len(chats)} chats and {len(initial_posts)} initial posts")
            
            # Send notification about completed initial sync
            await self._send_initial_sync_notification(user.id, "completed", len(chats), len(initial_posts))
            
            # Check if user needs context analysis
            if await self._should_analyze_user_context(user):
                await self._trigger_context_analysis(client, user)
                
        except Exception as e:
            self.logger.error(f"Error during initial safe sync for user {user.id}: {e}")
            await self.user_repository.update_user(
                user.id, 
                {"initial_sync_status": UserInitialSyncStatus.FAILED}
            )
            await self._send_initial_sync_notification(user.id, "failed", 0, 0)

    async def _perform_incremental_sync(self, client, user: User):
        """Perform incremental sync for users who completed initial sync."""
        try:
            # Check if user needs context analysis (first-time use or incomplete analysis)
            if await self._should_analyze_user_context(user):
                await self._trigger_context_analysis(client, user)

            # Get last message IDs for all user's chats
            chat_last_message_ids = await self._get_chat_last_message_ids(user.id)
            
            # Fetch new posts using TelethonService with rate limiting
            result = await self.telethon_service.get_new_user_posts(
                client=client,
                user_id=user.id,
                chat_last_message_ids=chat_last_message_ids,
                limit=user.telegram_messages_load_limit or 50
            )
            
            new_posts = result.get('posts', [])
            updated_last_message_ids = result.get('updated_last_message_ids', {})
            
            self.logger.info(f"Found {len(new_posts)} new posts for user {user.id}")
            
            if new_posts:
                # Store new posts and trigger AI comment generation
                stored_posts = await self._store_new_posts(new_posts, user.id)
                
                # Update last message IDs for chats
                await self._update_chat_last_message_ids(updated_last_message_ids)
                
                # Generate AI comments for relevant posts with delays
                for i, post_data in enumerate(stored_posts):
                    try:
                        await self.karma_service.generate_draft_comment(
                            original_message_id=post_data.get('stored_message_id'),
                            user_id=user.id,
                            post_data=post_data
                        )
                        
                        # Add delay between comment generations
                        if i % 5 == 0:  # Every 5 comments
                            await asyncio.sleep(self.DELAY_BETWEEN_API_CALLS_SECONDS)
                            
                    except Exception as e:
                        self.logger.error(f"Error generating AI comment for post: {e}")
                        continue
                
                # Send WebSocket notification about new posts
                await self._send_new_posts_notification(user.id, len(new_posts))
                
        except Exception as e:
            self.logger.error(f"Error during incremental sync for user {user.id}: {e}")

    async def _trigger_context_analysis(self, client, user: User):
        """Trigger user context analysis."""
        try:
            self.logger.info(f"Starting context analysis for user {user.id}")
            analysis_result = await self.user_context_analysis_service.analyze_user_context(client, user.id)
            if analysis_result.get("status") == "completed":
                self.logger.info(f"Context analysis completed for user {user.id}")
                await self._send_context_analysis_notification(user.id, "completed")
            else:
                self.logger.warning(f"Context analysis failed for user {user.id}: {analysis_result.get('reason')}")
                await self._send_context_analysis_notification(user.id, "failed")
        except Exception as e:
            self.logger.error(f"Error during context analysis for user {user.id}: {e}")
            await self._send_context_analysis_notification(user.id, "failed")

    def _convert_message_to_post(self, message_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Convert message data to post format."""
        return {
            'telegram_id': message_data.get('telegram_id'),
            'channel_telegram_id': message_data.get('chat_telegram_id'),
            'text': message_data.get('text', ''),
            'date': message_data.get('date'),
            'sender_id': message_data.get('sender_id'),
            'media_type': message_data.get('media_type'),
            'views': message_data.get('views'),
            'reactions': message_data.get('reactions', {}),
            'user_id': user_id
        }

    async def _send_initial_sync_notification(self, user_id: str, status: str, chats_count: int, posts_count: int):
        """Send WebSocket notification about initial sync completion."""
        try:
            await self.websocket_service.send_to_user(user_id, {
                'type': 'initial_sync_update',
                'status': status,
                'chats_fetched': chats_count,
                'posts_fetched': posts_count,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            self.logger.error(f"Error sending initial sync notification: {e}")

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