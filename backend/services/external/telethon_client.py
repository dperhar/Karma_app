"""Service for managing Telegram client connections."""

import logging
from typing import Any, Optional
from uuid import uuid4

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import PeerChannel, PeerUser

from config import TELETHON_API_HASH, TELETHON_API_ID
from models.telegram_messenger.chat_user import TelegramMessengerChatUser
from models.telegram_messenger.message import TelegramMessengerMessage
from services.domain.telegram_messenger.chat_service import TelegramMessengerChatService
from services.domain.telegram_messenger.chat_user_service import (
    TelegramMessengerChatUserService,
)
from services.domain.telegram_messenger.messages_service import (
    TelegramMessengerMessagesService,
)
from services.repositories.user_repository import UserRepository


class TelethonClient:
    """Global storage for Telegram clients."""

    def __init__(
        self,
        user_repository: UserRepository,
        container: Any,
    ):
        self.clients: dict[str, TelegramClient] = {}
        self.logger = logging.getLogger(__name__)
        self.user_repository = user_repository
        self.container = container

    async def has_client(self, user_id: str) -> Optional[TelegramClient]:
        """Get client if exists without creating a new one."""
        client = self.clients.get(user_id)
        if client:
            try:
                if not client.is_connected():
                    await client.connect()
                if await client.is_user_authorized():
                    return client
                else:
                    # Remove invalid client
                    del self.clients[user_id]
            except Exception as e:
                self.logger.error(f"Error checking client status: {e!s}")
                del self.clients[user_id]
        return None

    async def get_or_create_client(self, user_id: str) -> Optional[TelegramClient]:
        """Get existing client or create new one."""
        try:
            self.logger.info(f"TelethonClient.get_or_create_client called for user {user_id}")
            
            # Check if client exists and is connected
            client = await self.has_client(user_id)
            if client:
                self.logger.info(f"TelethonClient: Existing valid client found for user {user_id}")
                return client

            self.logger.info(f"TelethonClient: No existing client, creating new one for user {user_id}")
            
            # Get user from UserRepository
            user = await self.user_repository.get_user(user_id)
            if not user:
                self.logger.warning(f"TelethonClient: User {user_id} not found in repository")
                return None
                
            self.logger.info(f"TelethonClient: User {user_id} found, checking session validity")
            
            if not user.has_valid_tg_session():
                self.logger.warning(f"TelethonClient: User {user_id} has no valid Telegram session")
                self.logger.debug(f"TelethonClient: User {user_id} session_string exists: {bool(user.telegram_session_string)}")
                return None

            self.logger.info(f"TelethonClient: User {user_id} has valid session, creating client")
            
            # Create new client
            client = await self._create_client(user_id, user.telegram_session_string)
            if client:
                self.logger.info(f"TelethonClient: Successfully created client for user {user_id}")
                self.clients[user_id] = client
                return client
            else:
                self.logger.warning(f"TelethonClient: Failed to create client for user {user_id}")

            return None
        except Exception as e:
            self.logger.error(f"TelethonClient: Error getting or creating client for user {user_id}: {e!s}", exc_info=True)
            return None

    async def _create_client(
        self, user_id: str, session_string: str
    ) -> Optional[TelegramClient]:
        """Create and setup a new Telegram client."""
        try:
            # Create new client with session string
            client = TelegramClient(
                StringSession(session_string),
                int(TELETHON_API_ID),
                TELETHON_API_HASH,
            )

            # Connect and verify authorization
            await client.connect()
            if not await client.is_user_authorized():
                await client.disconnect()
                return None

            # Setup message handlers
            await self._setup_handlers(client, user_id)

            return client
        except Exception as e:
            self.logger.error(f"Error creating client: {e!s}")
            if client and client.is_connected():
                await client.disconnect()
            return None

    async def disconnect_client(self, user_id: str):
        """Disconnect and remove client."""
        if user_id in self.clients:
            try:
                client = self.clients[user_id]
                if client.is_connected():
                    await client.disconnect()
            except Exception as e:
                self.logger.error(f"Error disconnecting client: {e!s}")
            finally:
                del self.clients[user_id]

    async def disconnect_all(self):
        """Disconnect all clients."""
        for user_id in list(self.clients.keys()):
            await self.disconnect_client(user_id)

    async def _setup_handlers(self, client: TelegramClient, user_id: str):
        """Setup message handlers for client."""

        @client.on(events.NewMessage)
        async def handle_new_message(event):
            try:
                self.logger.info(f"Handling new message: {event}")
                # Get required services from container
                chat_service = self.container.resolve(TelegramMessengerChatService)
                chat_user_service = self.container.resolve(
                    TelegramMessengerChatUserService
                )
                messages_service = self.container.resolve(
                    TelegramMessengerMessagesService
                )

                # Get chat ID from event
                if isinstance(event.message.peer_id, PeerUser):
                    chat_telegram_id = event.message.peer_id.user_id
                elif isinstance(event.message.peer_id, PeerChannel):
                    chat_telegram_id = event.message.peer_id.channel_id
                else:
                    self.logger.error(
                        f"Unsupported peer type: {type(event.message.peer_id)}"
                    )
                    return

                # Get or create chat
                chat = await chat_service.get_chat(client, chat_telegram_id, user_id)
                if not chat:
                    self.logger.error(
                        f"Failed to get or create chat {chat_telegram_id}"
                    )
                    return

                # Get sender ID
                sender_telegram_id = None
                if event.message.from_id:
                    if isinstance(event.message.from_id, PeerUser):
                        sender_telegram_id = event.message.from_id.user_id
                    elif isinstance(event.message.from_id, PeerChannel):
                        sender_telegram_id = event.message.from_id.channel_id

                # For channel posts, use channel ID as sender
                if not sender_telegram_id and isinstance(
                    event.message.peer_id, PeerChannel
                ):
                    sender_telegram_id = chat_telegram_id

                if not sender_telegram_id:
                    self.logger.error("Could not determine sender ID")
                    return

                # Get or create participant
                participant = await chat_user_service.get_chat_user_by_telegram_id(
                    sender_telegram_id, chat.id
                )
                if not participant:
                    # Get sender info safely
                    sender = event.message.sender
                    if not sender:
                        # Try to fetch user information
                        try:
                            sender = await client.get_entity(sender_telegram_id)
                            self.logger.info(
                                f"Fetched user info for {sender_telegram_id}: {sender}"
                            )
                        except Exception as e:
                            self.logger.error(
                                f"Failed to fetch user info for {sender_telegram_id}: {e!s}"
                            )
                            return

                    # Create new participant
                    participant = TelegramMessengerChatUser(
                        id=str(uuid4()),
                        telegram_id=sender_telegram_id,
                        user_id=user_id,
                        chat_id=chat.id,
                        first_name=getattr(sender, "first_name", "") or "",
                        last_name=getattr(sender, "last_name", "") or "",
                        username=getattr(sender, "username", "") or "",
                        phone=getattr(sender, "phone", "") or "",
                        is_bot=getattr(sender, "bot", False),
                    )
                    participant = await chat_user_service.process_participant(
                        participant, chat.id
                    )
                    if not participant:
                        self.logger.error(
                            f"Failed to create participant {sender_telegram_id}"
                        )
                        return

                # Create message
                message = TelegramMessengerMessage(
                    id=str(uuid4()),
                    telegram_id=event.message.id,
                    chat_id=chat.id,
                    sender_id=participant.id,
                    text=event.message.message or "",
                    date=event.message.date.replace(
                        tzinfo=None
                    ),  # Convert to naive datetime
                    edit_date=(
                        event.message.edit_date.replace(tzinfo=None)
                        if event.message.edit_date
                        else None
                    ),
                    media_type=None,  # No media in this message
                    file_id=None,  # No media in this message
                )

                # Save message
                saved_messages = (
                    await messages_service.message_repository.create_or_update_messages(
                        [message]
                    )
                )
                if not saved_messages:
                    self.logger.error(f"Failed to save message {event.message.id}")
                    return

                self.logger.info(
                    f"Successfully processed new message {event.message.id}"
                )

            except Exception as e:
                self.logger.error(f"Error handling new message: {e!s}")
                return
