import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4

from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from telethon.sessions import StringSession
from telethon.tl.types import Channel as TelethonChannel
from telethon.tl.types import Chat as TelethonChat
from telethon.tl.types import Message as TelethonMessage
from telethon.tl.types import (
    MessageMediaDocument,
    MessageMediaPhoto,
    PeerChannel,
    PeerChat,
    PeerUser,
)
from telethon.tl.types import User as TelethonUser

from app.core.config import settings
from app.core.security import get_encryption_service
from app.models.chat import TelegramMessengerChat, TelegramMessengerChatType
from app.repositories.telegram_connection_repository import (
    TelegramConnectionRepository,
)
from app.services.base_service import BaseService


class TelegramService(BaseService):
    """
    Production-ready Telegram service with proper client lifecycle management.
    
    This service follows the proven pattern from the working project:
    - Proper connection pooling and lifecycle management
    - Event-driven message handling
    - Real-time streaming capabilities
    - Scalable client management
    """

    def __init__(self, connection_repo: TelegramConnectionRepository, container=None):
        super().__init__()
        self.connection_repo = connection_repo
        self.encryption_service = get_encryption_service()
        self.container = container
        
        # Production-ready client management
        self._clients: Dict[str, TelegramClient] = {}
        self._client_locks: Dict[str, asyncio.Lock] = {}
        self._flood_wait_state: Dict[str, Dict] = {}
        self._event_handlers_setup: Dict[str, bool] = {}

    # --- Production Client Management ---

    async def has_client(self, user_id: str) -> Optional[TelegramClient]:
        """Check if client exists and is valid without creating a new one."""
        client = self._clients.get(user_id)
        if client:
            try:
                if not client.is_connected():
                    await client.connect()
                if await client.is_user_authorized():
                    return client
                else:
                    # Remove invalid client
                    await self._remove_client(user_id)
            except Exception as e:
                self.logger.error(f"Error checking client status for user {user_id}: {e}")
                await self._remove_client(user_id)
        return None

    async def get_or_create_client(self, user_id: str) -> Optional[TelegramClient]:
        """
        Get existing client or create new one with proper lifecycle management.
        This is the main method for production client access.
        """
        lock = await self._get_client_lock(user_id)
        async with lock:
            # Check if client exists and is connected
            client = await self.has_client(user_id)
            if client:
                return client

            # Get user connection from database
            connection = await self.connection_repo.get_by_user_id(user_id)
            if not connection or not connection.session_string_encrypted:
                self.logger.warning(f"No valid Telegram connection found for user {user_id}")
                return None

            # Create new client
            client = await self._create_client(user_id, connection.session_string_encrypted)
            if client:
                self._clients[user_id] = client
                # Set up event handlers for real-time processing
                await self._setup_event_handlers(client, user_id)
                return client

            return None

    async def _create_client(self, user_id: str, encrypted_session: str) -> Optional[TelegramClient]:
        """Create and setup a new Telegram client."""
        try:
            # Decrypt session string
            session_string = self.encryption_service.decrypt_session_string(encrypted_session)

            # Create new client with session string
            client = TelegramClient(
                StringSession(session_string),
                int(settings.TELETHON_API_ID),
                settings.TELETHON_API_HASH,
                device_model="Karma App",
                system_version="1.0",
                app_version="1.0",
            )

            # Connect and verify authorization
            await client.connect()
            if not await client.is_user_authorized():
                self.logger.error(f"Session for user {user_id} is invalid or expired")
                await client.disconnect()
                return None

            self.logger.info(f"Successfully created Telethon client for user {user_id}")
            return client

        except Exception as e:
            self.logger.error(f"Error creating client for user {user_id}: {e}", exc_info=True)
            if 'client' in locals() and client.is_connected():
                await client.disconnect()
            return None

    async def _setup_event_handlers(self, client: TelegramClient, user_id: str):
        """
        Setup real-time event handlers for incoming messages.
        This enables real-time streaming of new messages.
        """
        if self._event_handlers_setup.get(user_id):
            return  # Already setup

        @client.on(events.NewMessage)
        async def handle_new_message(event):
            try:
                self.logger.info(f"📨 New message received for user {user_id}")
                # TODO: Process new message and send WebSocket notification
                # This will be implemented when we add WebSocket service
                
                # For now, just log the message
                if event.message.text:
                    self.logger.info(f"Message text: {event.message.text[:100]}...")
                    
            except Exception as e:
                self.logger.error(f"Error handling new message for user {user_id}: {e}")

        self._event_handlers_setup[user_id] = True
        self.logger.info(f"✅ Event handlers setup for user {user_id}")

    async def disconnect_client(self, user_id: str):
        """Disconnect and remove client from pool."""
        await self._remove_client(user_id)

    async def _remove_client(self, user_id: str):
        """Remove client from pool and clean up."""
        if user_id in self._clients:
            try:
                client = self._clients[user_id]
                if client.is_connected():
                    await client.disconnect()
                self.logger.info(f"Disconnected client for user {user_id}")
            except Exception as e:
                self.logger.error(f"Error disconnecting client for user {user_id}: {e}")
            finally:
                self._clients.pop(user_id, None)
                self._event_handlers_setup.pop(user_id, None)

    async def disconnect_all_clients(self):
        """Disconnect all clients - called during application shutdown."""
        for user_id in list(self._clients.keys()):
            await self._remove_client(user_id)
        self.logger.info("🔌 All Telegram clients disconnected")

    async def _get_client_lock(self, user_id: str) -> asyncio.Lock:
        """Get or create a lock for client operations."""
        if user_id not in self._client_locks:
            self._client_locks[user_id] = asyncio.Lock()
        return self._client_locks[user_id]

    # --- Flood Control (Production Ready) ---

    async def _handle_flood_wait(self, client_key: str, error: FloodWaitError):
        """Handle FloodWaitError with exponential backoff."""
        wait_time = error.seconds
        self.logger.warning(f"⚠️ FloodWaitError for client {client_key}: waiting {wait_time} seconds")

        # Mark client as in cooldown
        self._flood_wait_state[client_key] = {
            "cooldown_until": datetime.now().timestamp() + wait_time,
            "wait_seconds": wait_time,
        }

        await asyncio.sleep(wait_time + 1)  # Add 1 second buffer

        # Clear cooldown state
        self._flood_wait_state.pop(client_key, None)

    def _is_client_in_cooldown(self, client_key: str) -> bool:
        """Check if client is currently in cooldown."""
        if client_key not in self._flood_wait_state:
            return False
        cooldown_until = self._flood_wait_state[client_key]["cooldown_until"]
        return datetime.now().timestamp() < cooldown_until

    async def _safe_api_call(self, client_key: str, api_call_func, *args, **kwargs):
        """Execute API call with flood wait handling."""
        if self._is_client_in_cooldown(client_key):
            remaining = (
                self._flood_wait_state[client_key]["cooldown_until"]
                - datetime.now().timestamp()
            )
            self.logger.info(f"Client {client_key} in cooldown for {remaining:.1f}s")
            await asyncio.sleep(remaining + 1)

        try:
            return await api_call_func(*args, **kwargs)
        except FloodWaitError as e:
            await self._handle_flood_wait(client_key, e)
            # Retry once after waiting
            return await api_call_func(*args, **kwargs)

    # --- High-level API methods (Production Ready) ---

    async def get_user_chats(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get user's Telegram chats with production-ready error handling.
        
        Returns a list of chat dictionaries suitable for API responses.
        """
        client = await self.get_or_create_client(user_id)
        if not client:
            self.logger.warning(f"Could not get Telegram client for user {user_id}")
            return []

        try:
            # Use get_dialogs for efficient chat fetching (not iter_dialogs)
            dialogs = await self._safe_api_call(
                user_id, 
                client.get_dialogs,
                limit=limit
            )
            
            self.logger.info(f"📋 Found {len(dialogs)} dialogs for user {user_id}")
            
            chats = []
            for dialog in dialogs:
                try:
                    chat_data = await self._create_chat_dict_from_entity(dialog.entity, user_id)
                    if chat_data:
                        chats.append(chat_data)
                except Exception as e:
                    self.logger.error(f"Error processing dialog entity: {e}")
                    continue
                    
            self.logger.info(f"✅ Processed {len(chats)} valid chats for user {user_id}")
            return chats
            
        except Exception as e:
            self.logger.error(f"❌ Error fetching chats for user {user_id}: {e}", exc_info=True)
            return []

    async def _create_chat_dict_from_entity(
        self,
        chat_entity: Union[TelethonUser, TelethonChat, TelethonChannel],
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Create chat dictionary from Telethon entity.
        Returns structure compatible with frontend expectations.
        """
        try:
            chat_data = {
                "telegram_id": int(chat_entity.id),
                "user_id": user_id,
                "title": "",
                "type": "",
                "member_count": None,
                "username": getattr(chat_entity, "username", None),
            }
            
            if isinstance(chat_entity, TelethonUser):
                full_name = f"{chat_entity.first_name or ''} {chat_entity.last_name or ''}".strip()
                chat_data.update({
                    "type": "private",
                    "title": full_name or "Unknown User",
                })
                
            elif isinstance(chat_entity, TelethonChat):
                chat_data.update({
                    "type": "group", 
                    "title": chat_entity.title or "Unnamed Group",
                    "member_count": getattr(chat_entity, "participants_count", None),
                })
                
            elif isinstance(chat_entity, TelethonChannel):
                is_broadcast = getattr(chat_entity, "broadcast", False)
                chat_data.update({
                    "type": "channel" if is_broadcast else "supergroup",
                    "title": chat_entity.title or "Unnamed Channel",
                    "member_count": getattr(chat_entity, "participants_count", None),
                })
            else:
                self.logger.warning(f"Unknown entity type: {type(chat_entity)}")
                return None
                
            return chat_data
            
        except Exception as e:
            self.logger.error(f"Error creating chat dict from entity: {e}")
            return None

    async def post_comment_to_telegram(
        self,
        user_id: str,
        channel_telegram_id: int,
        post_telegram_id: int,
        comment_text: str,
    ) -> dict:
        """Post a comment to a Telegram channel/supergroup post.

        Note: For channels, commenting is implemented as sending a reply in the linked discussion group.
        For groups/supergroups, it's a simple reply to the message.
        This implementation assumes messages are available to reply to via telethon.
        """
        client = await self.get_or_create_client(user_id)
        if not client:
            return {"success": False, "error": "No Telegram client"}

        try:
            # Resolve channel entity
            entity = await client.get_entity(channel_telegram_id)

            # Try to find linked discussion group and post into that thread
            try:
                from telethon.tl import functions, types
                full = await client(functions.channels.GetFullChannelRequest(channel=entity))
                linked_chat_id = getattr(full.full_chat, "linked_chat_id", None)
                if linked_chat_id:
                    # Map channel post id -> discussion message id inside linked chat
                    try:
                        dm = await client(functions.messages.GetDiscussionMessageRequest(peer=entity, msg_id=post_telegram_id))
                        # messages array contains the root discussion message in linked chat
                        discussion_msg = None
                        try:
                            discussion_msg = (dm.messages or [None])[0]
                        except Exception:
                            discussion_msg = None
                        if discussion_msg is not None:
                            discussion_msg_id = int(getattr(discussion_msg, 'id', post_telegram_id))
                        else:
                            discussion_msg_id = int(post_telegram_id)
                    except Exception as map_e:
                        self.logger.info("Mapping to discussion id failed, will use original id: %s", str(map_e)[:160])
                        discussion_msg_id = int(post_telegram_id)

                    linked_peer = types.PeerChannel(linked_chat_id)
                    linked_entity = await client.get_entity(linked_peer)
                    try:
                        sent = await client.send_message(linked_entity, comment_text, reply_to=discussion_msg_id)
                    except Exception:
                        # Try to join and retry once if not a participant
                        try:
                            await client(functions.channels.JoinChannelRequest(linked_entity))
                            sent = await client.send_message(linked_entity, comment_text, reply_to=discussion_msg_id)
                        except Exception as e_join:
                            self.logger.warning("Join+send in linked discussion failed: %s", str(e_join))
                            raise
                    self.logger.info(
                        "Posted comment via linked discussion: channel=%s linked=%s post=%s msg_id=%s",
                        channel_telegram_id,
                        linked_chat_id,
                        post_telegram_id,
                        int(getattr(sent, "id", 0)),
                    )
                    return {"success": True, "message_id": int(getattr(sent, "id", 0))}
            except Exception as e_disc:
                self.logger.info("No linked discussion or failed to use it: %s", str(e_disc)[:160])

            # Fallback: if it's a group/supergroup, reply directly
            sent = await client.send_message(entity, comment_text, reply_to=post_telegram_id)
            self.logger.info(
                "Posted comment via direct reply: channel=%s post=%s msg_id=%s",
                channel_telegram_id,
                post_telegram_id,
                int(getattr(sent, "id", 0)),
            )
            return {"success": True, "message_id": int(getattr(sent, "id", 0))}
        except Exception as e:
            self.logger.error(f"Error posting comment for user {user_id}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def post_comment_by_url(self, user_id: str, post_url: str, comment_text: str) -> dict:
        """Post a comment using a Telegram post URL like https://t.me/<username>/<message_id>.

        Only supports username-based URLs for now. Returns {success, message_id, channel_id} on success.
        """
        client = await self.get_or_create_client(user_id)
        if not client:
            return {"success": False, "error": "No Telegram client"}

        try:
            import re as _re
            m = _re.search(r"https?://t\.me/([A-Za-z0-9_]+)/([0-9]+)", str(post_url))
            if not m:
                return {"success": False, "error": "Unsupported URL format"}
            username = m.group(1)
            message_id = int(m.group(2))

            entity = await client.get_entity(username)

            # Prefer linked discussion group if exists
            try:
                from telethon.tl import functions, types
                full = await client(functions.channels.GetFullChannelRequest(channel=entity))
                linked_chat_id = getattr(full.full_chat, "linked_chat_id", None)
                if linked_chat_id:
                    # Map channel post id -> discussion message id
                    try:
                        dm = await client(functions.messages.GetDiscussionMessageRequest(peer=entity, msg_id=message_id))
                        discussion_msg = None
                        try:
                            discussion_msg = (dm.messages or [None])[0]
                        except Exception:
                            discussion_msg = None
                        if discussion_msg is not None:
                            discussion_msg_id = int(getattr(discussion_msg, 'id', message_id))
                        else:
                            discussion_msg_id = int(message_id)
                    except Exception as map_e:
                        self.logger.info(f"URL mapping to discussion id failed, using original: {str(map_e)[:160]}")
                        discussion_msg_id = int(message_id)

                    linked_peer = types.PeerChannel(linked_chat_id)
                    linked_entity = await client.get_entity(linked_peer)
                    try:
                        sent = await client.send_message(linked_entity, comment_text, reply_to=discussion_msg_id)
                    except Exception:
                        try:
                            await client(functions.channels.JoinChannelRequest(linked_entity))
                            sent = await client.send_message(linked_entity, comment_text, reply_to=discussion_msg_id)
                        except Exception as e_join:
                            self.logger.warning("Join+send by URL failed: %s", str(e_join))
                            raise
                    chan_id = int(getattr(entity, 'id', 0)) if hasattr(entity, 'id') else None
                    return {
                        "success": True,
                        "message_id": int(getattr(sent, "id", 0)),
                        "channel_id": chan_id,
                    }
            except Exception as _e_disc:
                self.logger.info(f"URL post: no linked discussion: {str(_e_disc)[:160]}")

            # Fallback: direct reply (will fail for non-admin in channels)
            sent = await client.send_message(entity, comment_text, reply_to=message_id)
            chan_id = int(getattr(entity, 'id', 0)) if hasattr(entity, 'id') else None
            return {
                "success": True,
                "message_id": int(getattr(sent, "id", 0)),
                "channel_id": chan_id,
            }
        except Exception as e:
            self.logger.error(f"Error posting by URL for user {user_id}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # --- Legacy methods (keeping for backward compatibility) ---

    async def get_client(self, user_id: str) -> Optional[TelegramClient]:
        """Legacy method - use get_or_create_client instead."""
        return await self.get_or_create_client(user_id)

    async def get_user_sent_messages(
        self,
        user_id: str,
        limit: int = 200,
        *,
        min_date: Optional[datetime] = None,
        only_replies: bool = False,
        include_personal: bool = True,
    ) -> list[dict]:
        """Fetch user's own sent messages across dialogs.

        Args:
            user_id: App user id.
            limit: Hard cap on total messages to return (<= 10000).
            min_date: If provided, include only messages on/after this UTC datetime.
            only_replies: If True, include only messages that are replies.
            include_personal: If False, exclude private DMs entirely.

        Returns:
            A list of dictionaries with at least: text, date, chat_id, chat_title, chat_type, is_reply, reply_to_msg_id
        """
        client = await self.get_or_create_client(user_id)
        if not client:
            return []

        # Safety caps
        max_dialogs = 300
        per_dialog_limit = 200
        hard_cap = min(int(limit or 0) or 200, 10000)

        messages = []
        try:
            scanned_dialogs = 0
            async for dialog in client.iter_dialogs(limit=max_dialogs):
                # Determine chat type and inclusion
                entity = dialog.entity
                chat_type = "unknown"
                is_private = False
                is_group = False
                is_supergroup = False
                is_channel = False

                try:
                    if isinstance(entity, TelethonUser):
                        chat_type = "user"
                        is_private = True
                    elif isinstance(entity, TelethonChat):
                        chat_type = "group"
                        is_group = True
                    elif isinstance(entity, TelethonChannel):
                        # Channels can be broadcast or megagroups
                        if getattr(entity, "broadcast", False):
                            chat_type = "channel"
                            is_channel = True
                        else:
                            chat_type = "supergroup"
                            is_supergroup = True
                    else:
                        chat_type = getattr(dialog, "is_group", False) and "group" or "unknown"
                except Exception:
                    pass

                if is_private and not include_personal:
                    continue
                # We do not analyze pure broadcast channels for user's messages (cannot post there)
                if is_channel:
                    continue

                # Respect cooldown if needed
                if self._is_client_in_cooldown(user_id):
                    remaining = self._flood_wait_state[user_id]["cooldown_until"] - datetime.now().timestamp()
                    if remaining > 0:
                        await asyncio.sleep(remaining + 1)

                async for message in client.iter_messages(
                    dialog,
                    from_user="me",
                    limit=per_dialog_limit,
                ):
                    if message and message.text:
                        # In-code date filter to avoid Telethon param incompatibilities
                        try:
                            if min_date and message.date and message.date.replace(tzinfo=None) < min_date:
                                continue
                        except Exception:
                            pass
                        # Only replies if requested
                        reply_id = (
                            getattr(message, "reply_to_msg_id", None)
                            or getattr(getattr(message, "reply_to", None), "reply_to_msg_id", None)
                        )
                        is_reply = bool(reply_id)
                        if only_replies and not is_reply:
                            continue
                        # Build chat metadata
                        chat_title = None
                        try:
                            if isinstance(entity, TelethonUser):
                                full_name = f"{getattr(entity, 'first_name', '')} {getattr(entity, 'last_name', '')}".strip()
                                chat_title = full_name or "Unknown User"
                            else:
                                chat_title = getattr(entity, "title", None)
                        except Exception:
                            chat_title = None

                        messages.append(
                            {
                                "text": message.text,
                                "date": self._convert_to_naive_utc(message.date),
                                "chat_id": int(getattr(entity, "id", 0)) if hasattr(entity, "id") else None,
                                "chat_title": chat_title,
                                "chat_type": chat_type,
                                "is_reply": is_reply,
                                "reply_to_msg_id": int(reply_id) if reply_id else None,
                            }
                        )
                    if len(messages) >= hard_cap:
                        break
                scanned_dialogs += 1
                if len(messages) >= hard_cap:
                    break
                # Small delay between dialogs to be gentle on API
                await asyncio.sleep(0.2)
        except Exception as e:
            self.logger.error(
                f"Error fetching user sent messages for user {user_id}: {e}",
                exc_info=True,
            )

        # Sort by date descending to get the most recent messages
        messages.sort(key=lambda x: x.get("date", datetime.min), reverse=True)
        return messages[:hard_cap]

    def _convert_to_naive_utc(self, dt: Optional[datetime]) -> Optional[datetime]:
        """Convert timezone-aware datetime to naive UTC datetime."""
        if dt and dt.tzinfo is not None:
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt 

    # --- Avatars ---
    async def download_chat_avatar(self, user_id: str, chat_telegram_id: int) -> Optional[str]:
        """Download and cache chat/channel avatar locally, return file path if saved.

        The file is stored under static/avatars/{user_id}_{chat_telegram_id}.jpg
        """
        client = await self.get_or_create_client(user_id)
        if not client:
            return None
        try:
            import os
            from telethon.tl import types
            # Ensure directory exists
            base_dir = os.path.join("static", "avatars")
            os.makedirs(base_dir, exist_ok=True)
            filepath = os.path.join(base_dir, f"{user_id}_{int(chat_telegram_id)}.jpg")

            entity = await client.get_entity(types.PeerChannel(int(chat_telegram_id)))
            # Telethon will choose best available size; overwrite file
            await client.download_profile_photo(entity, file=filepath)
            return filepath
        except Exception as e:
            self.logger.debug(f"Avatar download skipped for {chat_telegram_id}: {e}")
            return None

    async def download_message_photo(self, user_id: str, chat_telegram_id: int, message_id: int) -> Optional[str]:
        """Download a message photo under logs/media and return a public URL path (/media/...).

        Using logs/media ensures write permissions inside the container.
        """
        client = await self.get_or_create_client(user_id)
        if not client:
            return None
        from telethon.tl import types
        try:
            import os
            base_dir = os.path.join("logs", "media")
            os.makedirs(base_dir, exist_ok=True)
            local_file = f"{user_id}_{chat_telegram_id}_{message_id}.jpg"
            filename = os.path.join(base_dir, local_file)
            entity = types.PeerChannel(int(chat_telegram_id))
            msg = await client.get_messages(entity, ids=message_id)
            if not msg or not getattr(msg, 'photo', None):
                return None
            await client.download_media(msg.photo, file=filename)
            # Return a public URL path to be served via FastAPI StaticFiles mounted at /media
            return f"/media/{local_file}"
        except Exception as e:
            self.logger.debug(f"Photo download skipped for {chat_telegram_id}/{message_id}: {e}")
            return None