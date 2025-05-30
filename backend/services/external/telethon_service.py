"""Service module for handling Telegram client operations."""

from datetime import datetime, timezone
from typing import Any, Optional, Union, Dict, Tuple
from uuid import uuid4
import asyncio

from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.tl.types import (
    Channel as TelethonChannel,
)
from telethon.tl.types import (
    Chat as TelethonChat,
)
from telethon.tl.types import (
    Message as TelethonMessage,
)
from telethon.tl.types import (
    MessageMediaDocument,
    MessageMediaPhoto,
    PeerChannel,
    PeerChat,
    PeerUser,
    MessageReactions,
)
from telethon.tl.types import (
    User as TelethonUser,
)

from models.telegram_messenger.chat import (
    TelegramMessengerChat,
    TelegramMessengerChatType,
)
from models.telegram_messenger.chat_user import TelegramMessengerChatUser
from services.base.base_service import BaseService


class TelethonService(BaseService):
    """Service for managing Telegram client operations."""

    def __init__(self):
        """Initialize TelethonService with dependencies."""
        super().__init__()
        self._flood_wait_state = {}  # Track flood wait state per client

    def set_container(self, container: Any):
        """Set container after initialization."""
        self.container = container

    # ===== Flood Control Methods =====

    async def _handle_flood_wait(self, client_key: str, error: FloodWaitError):
        """Handle FloodWaitError globally for a client."""
        wait_time = error.seconds
        self.logger.warning(f"FloodWaitError for client {client_key}: waiting {wait_time} seconds")
        
        # Mark client as in cooldown
        self._flood_wait_state[client_key] = {
            'cooldown_until': datetime.now().timestamp() + wait_time,
            'wait_seconds': wait_time
        }
        
        await asyncio.sleep(wait_time + 1)  # Add 1 second buffer
        
        # Clear cooldown state
        if client_key in self._flood_wait_state:
            del self._flood_wait_state[client_key]

    def _is_client_in_cooldown(self, client_key: str) -> bool:
        """Check if client is currently in cooldown."""
        if client_key not in self._flood_wait_state:
            return False
        
        cooldown_until = self._flood_wait_state[client_key]['cooldown_until']
        return datetime.now().timestamp() < cooldown_until

    async def _safe_api_call(self, client_key: str, api_call_func, *args, **kwargs):
        """Safely execute an API call with flood wait handling."""
        if self._is_client_in_cooldown(client_key):
            remaining = self._flood_wait_state[client_key]['cooldown_until'] - datetime.now().timestamp()
            self.logger.info(f"Client {client_key} still in cooldown for {remaining:.1f} seconds")
            await asyncio.sleep(remaining + 1)
        
        try:
            return await api_call_func(*args, **kwargs)
        except FloodWaitError as e:
            await self._handle_flood_wait(client_key, e)
            # Retry once after waiting
            return await api_call_func(*args, **kwargs)

    # ===== Public Methods =====

    async def sync_chats(
        self, 
        client: TelegramClient, 
        user_id: str, 
        limit: int = 20,
        offset_date: Optional[datetime] = None,
        offset_id: Optional[int] = None,
        offset_peer=None
    ) -> Tuple[list[TelegramMessengerChat], Optional[Dict[str, Any]]]:
        """Get user's Telegram chats data without storing, with pagination support.

        Args:
            client: Authenticated TelegramClient instance
            user_id: User ID
            limit: Maximum number of chats to retrieve (default: 20, max recommended: 50)
            offset_date: Date offset for pagination
            offset_id: Message ID offset for pagination
            offset_peer: Peer offset for pagination

        Returns:
            Tuple of (list of TelegramMessengerChat objects, next_pagination_info)
            next_pagination_info contains fields for next page or None if no more data
        """
        client_key = f"user_{user_id}"
        chats = []
        next_pagination_info = None
        
        try:
            # Safe API call with flood protection
            dialogs = await self._safe_api_call(
                client_key,
                client.get_dialogs,
                limit=limit,
                offset_date=offset_date,
                offset_id=offset_id,
                offset_peer=offset_peer
            )
            
            self.logger.info(f"Found {len(dialogs)} dialogs for user {user_id}")
            
            for dialog in dialogs:
                chat = await self._create_chat_from_entity(dialog.entity, user_id)
                if chat:
                    chats.append(chat)

            # Determine next pagination info if we got the full limit
            if len(dialogs) == limit and dialogs:
                last_dialog = dialogs[-1]
                next_pagination_info = {
                    'offset_date': last_dialog.date,
                    'offset_id': last_dialog.top_message,
                    'offset_peer': last_dialog.entity
                }

            return chats, next_pagination_info

        except Exception as e:
            self.logger.error(f"Error syncing chats for user {user_id}: {e!s}")
            raise

    async def sync_chat(
        self, client: TelegramClient, telegram_id: int, user_id: str
    ) -> Optional[TelegramMessengerChat]:
        """Get chat data from Telegram.

        Args:
            client: Authenticated TelegramClient instance
            telegram_id: Telegram chat ID
            user_id: User ID

        Returns:
            TelegramMessengerChat object or None if failed
        """
        try:
            chat_entity = await client.get_entity(telegram_id)
            return await self._create_chat_from_entity(chat_entity, user_id)

        except Exception as e:
            self.logger.error(f"Error syncing chat {telegram_id}: {e!s}")
            return None

    async def sync_chat_participants(
        self,
        client: TelegramClient,
        chat_id: str,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[list[TelegramMessengerChatUser], Optional[Dict[str, Any]]]:
        """Get participants from a chat with pagination support.

        Args:
            client: Authenticated TelegramClient instance
            chat_id: Chat ID
            user_id: User ID
            limit: Maximum number of participants to retrieve (default: 50, max recommended: 100)
            offset: Number of participants to skip

        Returns:
            Tuple of (list of TelegramMessengerChatUser objects, next_pagination_info)
            next_pagination_info contains offset for next page or None if no more data
        """
        client_key = f"user_{user_id}"
        participants = []
        next_pagination_info = None
        
        try:
            # Safe API call with flood protection
            chat_entity = await self._safe_api_call(
                client_key,
                client.get_entity,
                int(chat_id)
            )

            if isinstance(chat_entity, (TelethonChat, TelethonChannel)):
                # Use more efficient pagination with proper offset handling
                skipped = 0
                participant_count = 0
                
                # Add delay before starting to be gentle on API
                if offset > 0:
                    await asyncio.sleep(0.2)
                
                async for participant in client.iter_participants(chat_entity):
                    # Skip participants up to the offset
                    if skipped < offset:
                        skipped += 1
                        continue

                    if not isinstance(participant, TelethonUser):
                        continue

                    # Get join date and remove timezone info if present
                    join_date = getattr(participant.participant, "date", None)
                    if join_date and join_date.tzinfo:
                        join_date = join_date.replace(tzinfo=None)

                    # Create TelegramMessengerChatUser object
                    chat_user = TelegramMessengerChatUser(
                        id=uuid4().hex,
                        telegram_id=participant.id,
                        user_id=user_id,
                        chat_id=str(chat_id),
                        username=participant.username,
                        first_name=participant.first_name,
                        last_name=participant.last_name,
                        phone=participant.phone,
                        is_bot=participant.bot,
                        is_admin=hasattr(participant, "participant")
                        and (
                            getattr(participant.participant, "admin_rights", None)
                            is not None
                            or getattr(participant.participant, "role", "") == "admin"
                        ),
                        is_creator=hasattr(participant, "participant")
                        and getattr(participant.participant, "is_creator", False),
                        join_date=join_date,
                    )
                    participants.append(chat_user)
                    participant_count += 1

                    # Add small delay every 10 participants to be gentle on API
                    if participant_count % 10 == 0:
                        await asyncio.sleep(0.1)

                    # Stop if we've reached the limit
                    if len(participants) >= limit:
                        break

                # Determine next pagination info if we got the full limit
                if len(participants) == limit:
                    next_pagination_info = {
                        'offset': offset + limit
                    }

                self.logger.info(f"Fetched {len(participants)} participants for chat {chat_id}")
                return participants, next_pagination_info
            else:
                self.logger.warning(
                    f"Entity with ID {chat_id} is not a group or channel"
                )
                return [], None

        except FloodWaitError as e:
            await self._handle_flood_wait(client_key, e)
            raise
        except Exception as e:
            self.logger.error(f"Error getting participants for chat {chat_id}: {e!s}")
            raise

    async def sync_chat_messages(
        self,
        client: TelegramClient,
        chat_telegram_id: int,
        user_id: str,
        limit: int = 50,
        offset_id: Optional[int] = None,
        min_id: Optional[int] = None,
        max_id: Optional[int] = None,
        direction: str = "older"
    ) -> Tuple[list[dict], Optional[Dict[str, Any]]]:
        """Get messages from a specific chat without storing, with pagination support.

        Args:
            client: Authenticated TelegramClient instance
            chat_telegram_id: Chat ID
            user_id: User ID
            limit: Maximum number of messages to retrieve (default: 50, max recommended: 100)
            offset_id: Message ID to start from (for pagination)
            min_id: Minimum message ID (for getting newer messages)
            max_id: Maximum message ID (for getting older messages)
            direction: Direction to fetch ("older" or "newer")

        Returns:
            Tuple of (list of message data dictionaries, next_pagination_info)
            next_pagination_info contains fields for next page or None if no more data
        """
        client_key = f"user_{user_id}"
        messages_data = []
        next_pagination_info = None
        
        try:
            # Safe API call with flood protection
            chat_entity = await self._safe_api_call(
                client_key,
                client.get_entity,
                chat_telegram_id
            )

            # Set up pagination parameters based on direction
            iter_params = {
                'limit': limit,
                'reverse': direction == "newer"
            }
            
            if offset_id:
                iter_params['offset_id'] = offset_id
            if min_id:
                iter_params['min_id'] = min_id
            if max_id:
                iter_params['max_id'] = max_id

            self.logger.info(f"Fetching messages for chat {chat_telegram_id} with params: {iter_params}")

            # Use safe iteration with small delay between batches
            message_count = 0
            last_message_id = None
            
            async for message in client.iter_messages(chat_entity, **iter_params):
                if not isinstance(message, TelethonMessage):
                    continue

                message_data = await self.process_message(
                    message, chat_entity, chat_telegram_id
                )
                messages_data.append(message_data)
                last_message_id = message.id
                message_count += 1
                
                # Add small delay every 10 messages to be gentle on API
                if message_count % 10 == 0:
                    await asyncio.sleep(0.1)

            # Determine next pagination info if we got the full limit
            if len(messages_data) == limit and last_message_id:
                if direction == "older":
                    next_pagination_info = {
                        'offset_id': last_message_id,
                        'max_id': last_message_id - 1,
                        'direction': 'older'
                    }
                else:  # newer
                    next_pagination_info = {
                        'offset_id': last_message_id,
                        'min_id': last_message_id + 1,
                        'direction': 'newer'
                    }

            self.logger.info(f"Fetched {len(messages_data)} messages for chat {chat_telegram_id}")
            return messages_data, next_pagination_info

        except FloodWaitError as e:
            await self._handle_flood_wait(client_key, e)
            raise
        except Exception as e:
            self.logger.error(
                f"Error syncing messages for chat {chat_telegram_id}: {e!s}"
            )
            raise

    async def get_telegram_user(self, client: TelegramClient, telegram_id: int) -> dict:
        """Get Telegram user information by telegram_id.

        Args:
            client: Authenticated TelegramClient instance
            telegram_id: Telegram user ID

        Returns:
            dictionary with user information
        """
        try:
            user = await client.get_entity(telegram_id)
            if not isinstance(user, TelethonUser):
                raise ValueError("Entity is not a user")

            user_data = {
                "telegram_id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone": user.phone,
                "is_bot": user.bot,
                "language_code": getattr(user, "lang_code", None),
            }
            return user_data

        except Exception as e:
            self.logger.error(f"Error getting user {telegram_id}: {e!s}")
            raise

    async def get_user_posts(
        self, 
        client: TelegramClient, 
        user_id: str, 
        limit: int = 50, 
        offset: int = 0
    ) -> list[dict]:
        """Get recent posts from user's subscribed channels/chats with reactions.

        Args:
            client: Authenticated TelegramClient instance
            user_id: User ID
            limit: Maximum number of posts to retrieve (default: 50, max recommended: 100)
            offset: Number of posts to skip

        Returns:
            List of post data dictionaries with reactions
        """
        client_key = f"user_{user_id}"
        
        try:
            posts = []
            processed_count = 0
            skipped_count = 0

            # Get user's dialogs with safe pagination
            chats, _ = await self.sync_chats(
                client=client,
                user_id=user_id,
                limit=50  # Conservative limit for dialog fetching
            )
            
            for chat in chats:
                # Only process channels and groups
                if chat.type not in ['channel', 'supergroup', 'group']:
                    continue
                
                try:
                    # Get messages from this channel/chat with safe pagination
                    messages_data, _ = await self.sync_chat_messages(
                        client=client,
                        chat_telegram_id=chat.telegram_id,
                        user_id=user_id,
                        limit=20,  # Small batch per chat
                        direction="older"
                    )
                    
                    for message_data in messages_data:
                        if not message_data.get('text') and not message_data.get('media_type'):
                            continue
                            
                        if skipped_count < offset:
                            skipped_count += 1
                            continue
                        
                        # Convert message to post data
                        post_data = self._convert_message_data_to_post(message_data, chat)
                        if post_data:
                            posts.append(post_data)
                            processed_count += 1
                            
                        if processed_count >= limit:
                            break
                    
                    # Add delay between chats to be gentle on API
                    await asyncio.sleep(0.3)
                            
                except Exception as e:
                    self.logger.error(f"Error getting messages from chat {chat.telegram_id}: {e}")
                    continue
                    
                if processed_count >= limit:
                    break
            
            # Sort posts by date (newest first)
            posts.sort(key=lambda x: x.get('date', datetime.min), reverse=True)
            
            return posts[:limit]
            
        except Exception as e:
            self.logger.error(f"Error getting user posts: {e}")
            raise

    async def get_new_user_posts(
        self,
        client: TelegramClient,
        user_id: str,
        chat_last_message_ids: dict[int, int] = None,
        limit: int = 50
    ) -> dict:
        """Get new posts from user's subscribed channels/chats since last fetch with safe pagination.

        Args:
            client: Authenticated TelegramClient instance
            user_id: User ID
            chat_last_message_ids: Dict mapping chat telegram_id to last fetched message ID
            limit: Maximum number of posts to retrieve per chat (default: 50, max recommended: 100)

        Returns:
            Dict with 'posts' list and 'updated_last_message_ids' dict
        """
        client_key = f"user_{user_id}"
        
        try:
            all_new_posts = []
            updated_last_message_ids = {}
            
            if chat_last_message_ids is None:
                chat_last_message_ids = {}

            # Get user's dialogs with conservative limit
            chats, _ = await self.sync_chats(
                client=client,
                user_id=user_id,
                limit=50  # Conservative limit
            )
            
            for chat in chats:
                # Only process channels and groups
                if chat.type not in ['channel', 'supergroup', 'group']:
                    continue
                
                try:
                    chat_telegram_id = chat.telegram_id
                    last_message_id = chat_last_message_ids.get(chat_telegram_id, 0)
                    
                    # Determine if this is an initial fetch for this chat
                    is_initial_fetch = last_message_id == 0
                    actual_limit = min(20, limit) if is_initial_fetch else limit
                    
                    self.logger.info(f"Fetching {'initial' if is_initial_fetch else 'new'} messages for chat {chat_telegram_id}, limit: {actual_limit}")
                    
                    # Get new messages with pagination
                    messages_data, _ = await self.sync_chat_messages(
                        client=client,
                        chat_telegram_id=chat_telegram_id,
                        user_id=user_id,
                        limit=actual_limit,
                        min_id=last_message_id if last_message_id > 0 else None,
                        direction="newer" if last_message_id > 0 else "older"
                    )
                    
                    new_posts_for_chat = []
                    max_message_id = last_message_id
                    
                    for message_data in messages_data:
                        if not message_data.get('text') and not message_data.get('media_type'):
                            continue
                        
                        # Track the highest message ID we've seen
                        message_telegram_id = message_data.get('telegram_id', 0)
                        if message_telegram_id > max_message_id:
                            max_message_id = message_telegram_id
                            
                        # Convert message to post data
                        post_data = self._convert_message_data_to_post(message_data, chat)
                        if post_data:
                            new_posts_for_chat.append(post_data)
                    
                    if new_posts_for_chat:
                        self.logger.info(
                            f"Found {len(new_posts_for_chat)} new posts in {chat.title} "
                            f"(chat_id: {chat_telegram_id})"
                        )
                        all_new_posts.extend(new_posts_for_chat)
                        
                    # Update the last message ID even if no new posts (to track progress)
                    if max_message_id > last_message_id:
                        updated_last_message_ids[chat_telegram_id] = max_message_id
                    
                    # Add delay between chats to be gentle on API
                    await asyncio.sleep(0.5)
                        
                except Exception as e:
                    self.logger.error(f"Error getting new messages from chat {chat.telegram_id}: {e}")
                    continue
            
            # Sort all posts by date (newest first)
            all_new_posts.sort(key=lambda x: x.get('date', datetime.min), reverse=True)
            
            self.logger.info(f"Found total {len(all_new_posts)} new posts across all chats for user {user_id}")
            
            return {
                'posts': all_new_posts,
                'updated_last_message_ids': updated_last_message_ids
            }
            
        except Exception as e:
            self.logger.error(f"Error getting new user posts: {e}")
            raise

    def _convert_message_data_to_post(self, message_data: dict, chat) -> Optional[dict]:
        """Convert message data to post format.
        
        Args:
            message_data: Message data dictionary from sync_chat_messages
            chat: TelegramMessengerChat object
            
        Returns:
            Post data dictionary or None
        """
        try:
            return {
                'id': message_data.get('telegram_id'),
                'telegram_id': message_data.get('telegram_id'),
                'channel_telegram_id': chat.telegram_id,
                'text': message_data.get('text', ''),
                'date': message_data.get('date'),
                'sender_id': message_data.get('sender_id'),
                'media_type': message_data.get('media_type'),
                'media_url': message_data.get('media_url'),
                'views': message_data.get('views'),
                'reactions': message_data.get('reactions', {}),
                'channel': {
                    'id': chat.telegram_id,
                    'title': chat.title,
                    'type': chat.type
                }
            }
        except Exception as e:
            self.logger.error(f"Error converting message data to post: {e}")
            return None

    async def post_comment_to_telegram(
        self,
        client: TelegramClient,
        channel_telegram_id: int,
        post_telegram_id: int,
        comment_text: str
    ) -> dict:
        """Post a comment to a Telegram post.

        Args:
            client: Authenticated TelegramClient instance
            channel_telegram_id: Telegram channel ID
            post_telegram_id: Telegram post ID
            comment_text: Comment text to post

        Returns:
            Dictionary with success status and message data
        """
        try:
            # Get the channel entity
            channel_entity = await client.get_entity(channel_telegram_id)
            
            # Send the comment as a reply to the original post
            sent_message = await client.send_message(
                entity=channel_entity,
                message=comment_text,
                reply_to=post_telegram_id
            )
            
            return {
                'success': True,
                'message_id': sent_message.id,
                'date': sent_message.date.replace(tzinfo=None) if sent_message.date else None,
                'text': sent_message.text
            }
            
        except Exception as e:
            self.logger.error(f"Error posting comment to {channel_telegram_id}/{post_telegram_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    # ===== Internal Methods =====

    async def _create_chat_from_entity(
        self,
        chat_entity: Union[TelethonUser, TelethonChat, TelethonChannel],
        user_id: str,
    ) -> Optional[TelegramMessengerChat]:
        """Create TelegramMessengerChat from Telethon entity.

        Args:
            chat_entity: Telethon chat entity
            user_id: User ID

        Returns:
            TelegramMessengerChat object or None if entity type is not supported
        """
        try:
            if isinstance(chat_entity, TelethonUser):
                return TelegramMessengerChat(
                    id=uuid4().hex,
                    telegram_id=int(chat_entity.id),
                    user_id=user_id,
                    type=TelegramMessengerChatType.PRIVATE,
                    title=f"{chat_entity.first_name or ''} {chat_entity.last_name or ''}".strip(),
                    member_count=None,
                )

            elif isinstance(chat_entity, TelethonChat):
                return TelegramMessengerChat(
                    id=uuid4().hex,
                    telegram_id=int(chat_entity.id),
                    user_id=user_id,
                    type=TelegramMessengerChatType.GROUP,
                    title=chat_entity.title,
                    member_count=getattr(chat_entity, "participants_count", None),
                )

            elif isinstance(chat_entity, TelethonChannel):
                is_broadcast = getattr(chat_entity, "broadcast", False)
                return TelegramMessengerChat(
                    id=uuid4().hex,
                    telegram_id=int(chat_entity.id),
                    user_id=user_id,
                    type=(
                        TelegramMessengerChatType.CHANNEL
                        if is_broadcast
                        else TelegramMessengerChatType.SUPERGROUP
                    ),
                    title=chat_entity.title,
                    member_count=getattr(chat_entity, "participants_count", None),
                )

            return None
        except Exception as e:
            self.logger.error(f"Error creating chat from entity: {e!s}")
            return None

    async def _get_sender_telegram_id(
        self,
        message: TelethonMessage,
        chat_entity: Union[TelethonUser, TelethonChat, TelethonChannel],
    ) -> Optional[int]:
        """Extract sender telegram ID from message based on chat type."""
        sender_telegram_id = None

        if isinstance(chat_entity, TelethonUser):
            # Private chat
            sender_telegram_id = message.sender_id
            if isinstance(sender_telegram_id, PeerUser):
                sender_telegram_id = sender_telegram_id.user_id

        elif isinstance(chat_entity, TelethonChat):
            # Group chat
            if message.from_id:
                if isinstance(message.from_id, PeerUser):
                    sender_telegram_id = message.from_id.user_id
                elif isinstance(message.from_id, PeerChat):
                    sender_telegram_id = message.from_id.chat_id

        elif isinstance(chat_entity, TelethonChannel):
            # Channel or Supergroup
            if message.from_id:
                if isinstance(message.from_id, PeerUser):
                    sender_telegram_id = message.from_id.user_id
                elif isinstance(message.from_id, PeerChannel):
                    sender_telegram_id = message.from_id.channel_id
            # For anonymous admins or channel posts
            elif message.post:
                sender_telegram_id = chat_entity.id

        return sender_telegram_id

    async def _get_media_info(
        self, message: TelethonMessage
    ) -> tuple[Optional[str], Optional[str]]:
        """Extract media type and file ID from message."""
        media_type = None
        file_id = None

        if message.media:
            if isinstance(message.media, MessageMediaPhoto):
                media_type = "photo"
                file_id = str(message.media.photo.id)
            elif isinstance(message.media, MessageMediaDocument):
                media_type = "document"
                file_id = str(message.media.document.id)

        return media_type, file_id

    async def _get_reply_info(
        self,
        message: TelethonMessage,
        chat_entity: Union[TelethonUser, TelethonChat, TelethonChannel],
    ) -> Optional[int]:
        """Extract reply message ID based on chat type."""
        reply_to_msg_id = None
        if message.reply_to:
            if hasattr(message.reply_to, "reply_to_msg_id"):
                if isinstance(chat_entity, TelethonChannel):
                    # Channels use reply_to_msg_id
                    reply_to_msg_id = message.reply_to.reply_to_msg_id
                else:
                    # Groups and private chats use reply_to_msg_id
                    reply_to_msg_id = message.reply_to.reply_to_msg_id
        return reply_to_msg_id

    def _convert_to_naive_utc(self, dt: Optional[datetime]) -> Optional[datetime]:
        """Convert timezone-aware datetime to naive UTC datetime."""
        if dt and dt.tzinfo is not None:
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt

    async def process_message(
        self,
        message: TelethonMessage,
        chat_entity: Union[TelethonUser, TelethonChat, TelethonChannel],
        chat_telegram_id: int,
    ) -> dict:
        """Process a single message and return its data."""
        sender_telegram_id = await self._get_sender_telegram_id(message, chat_entity)
        media_type, file_id = await self._get_media_info(message)
        reply_to_msg_id = await self._get_reply_info(message, chat_entity)

        # Convert dates to naive UTC
        message_date = self._convert_to_naive_utc(message.date)
        edit_date = self._convert_to_naive_utc(message.edit_date)
        return {
            "message_telegram_id": message.id,
            "chat_telegram_id": chat_telegram_id,
            "sender_telegram_id": sender_telegram_id,
            "message_text": message.message or "",
            "message_date": message_date,
            "edit_date": edit_date,
            "media_type": media_type,
            "file_id": file_id,
            "reply_to_message_telegram_id": reply_to_msg_id,
        }
