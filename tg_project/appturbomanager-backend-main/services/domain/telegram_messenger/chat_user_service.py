"""Service for Telegram Messenger chat user operations."""

from typing import Any, Optional

from telethon.tl.types import Channel as TelethonChannel
from telethon.tl.types import Chat as TelethonChat
from telethon.tl.types import User as TelethonUser

from models.management.person import ManagementPerson
from models.telegram_messenger.chat import (
    TelegramMessengerChat,
    TelegramMessengerChatType,
)
from models.telegram_messenger.chat_user import TelegramMessengerChatUser
from services.base.base_service import BaseService
from services.external.telethon_service import TelethonService
from services.repositories.management.person_repository import PersonRepository
from services.repositories.telegram.chat_repository import ChatRepository
from services.repositories.telegram.participant_repository import ParticipantRepository


class TelegramMessengerChatUserService(BaseService):
    """Service class for Telegram Messenger chat user operations."""

    def __init__(
        self,
        telethon_service: TelethonService,
        chat_repository: ChatRepository,
        participant_repository: ParticipantRepository,
        person_repository: PersonRepository,
    ):
        """Initialize the service with required dependencies."""
        super().__init__()
        self.telethon_service = telethon_service
        self.chat_repository = chat_repository
        self.participant_repository = participant_repository
        self.person_repository = person_repository

    async def get_chat_participants(
        self,
        client: Any,
        chat: TelegramMessengerChat,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TelegramMessengerChatUser]:
        """Get chat participants.

        Args:
            client: Authenticated TelegramClient instance
            chat: TelegramMessengerChat object
            limit: Maximum number of participants to retrieve per request
            offset: Number of participants to skip

        Returns:
            list of TelegramMessengerChatUser objects
        """
        # First ensure the chat exists in our database
        self.logger.info(
            f"Getting chat by telegram_id: {chat.telegram_id}, user_id: {chat.user_id}"
        )
        existing_chat = await self.chat_repository.get_chat_by_telegram_id(
            chat.telegram_id, chat.user_id
        )
        self.logger.info(f"Existing chat: {existing_chat}")
        if not existing_chat:
            # If chat doesn't exist, create it
            existing_chat = await self.chat_repository.create_or_update_chats([chat])[0]
        self.logger.info(
            f"Existing chat: {existing_chat.user_id} {existing_chat.telegram_id}"
        )

        # Handle private chats differently
        if existing_chat.type == TelegramMessengerChatType.PRIVATE:
            self.logger.info(
                f"Handling private chat with ID: {existing_chat.telegram_id}"
            )
            # For private chats, create a participant with the chat's telegram_id
            # Check if participant already exists
            existing_participant = (
                await self.participant_repository.get_participant_by_telegram_id(
                    existing_chat.telegram_id, existing_chat.id
                )
            )

            if existing_participant:
                self.logger.info(
                    f"Existing participant found for private chat: {existing_participant}"
                )
                return [existing_participant]

            # Create a new participant for the private chat
            chat_entity = await client.get_entity(int(existing_chat.telegram_id))
            participant = TelegramMessengerChatUser(
                telegram_id=existing_chat.telegram_id,
                user_id=existing_chat.user_id,
                chat_id=existing_chat.id,
                username=getattr(chat_entity, "username", None),
                first_name=getattr(chat_entity, "first_name", None),
                last_name=getattr(chat_entity, "last_name", None),
                phone=None,
                is_bot=False,
                is_admin=False,
                is_creator=False,
            )

            processed_participant = await self.process_participant(
                participant, existing_chat.id
            )
            if processed_participant:
                self.logger.info(
                    f"Created participant for private chat: {processed_participant}"
                )
                return [processed_participant]
            return []

        # Get total member count
        total_members = existing_chat.member_count
        if not total_members:
            # If member count is not available, try to get it from Telegram
            chat_entity = await client.get_entity(int(existing_chat.telegram_id))
            if isinstance(chat_entity, (TelethonChat, TelethonChannel)):
                total_members = getattr(chat_entity, "participants_count", None)
                if total_members:
                    existing_chat.member_count = total_members
                    await self.chat_repository.create_or_update_chats([existing_chat])

        if not total_members:
            self.logger.warning("Could not determine total member count")
            return []

        all_participants = []
        current_offset = offset
        batch_size = min(limit, 100)  # Telegram API limit is 100 per request

        while current_offset < total_members:
            self.logger.info(
                f"Fetching participants batch: offset={current_offset}, limit={batch_size}"
            )
            participants = await self.telethon_service.sync_chat_participants(
                client=client,
                chat_id=existing_chat.telegram_id,
                user_id=existing_chat.user_id,
                limit=batch_size,
                offset=current_offset,
            )

            if not participants:
                break

            processed_participants = []
            for participant in participants:
                processed_participant = await self.process_participant(
                    participant, existing_chat.id
                )
                if processed_participant:
                    processed_participants.append(processed_participant)

            all_participants.extend(processed_participants)
            current_offset += len(participants)

            if len(participants) < batch_size:
                break

        return all_participants

    async def process_participant(
        self, participant: TelegramMessengerChatUser, chat_id: str
    ) -> TelegramMessengerChatUser:
        """Process a single participant and link it to a management person.

        Args:
            participant: TelegramMessengerChatUser object to process

        Returns:
            Processed TelegramMessengerChatUser object
        """
        self.logger.info(f"Processing participant: {participant}")
        if not participant.telegram_id:
            return participant

        self.logger.info(
            f"Processing participant: {participant.telegram_id} {participant.first_name} {participant.last_name}"
        )
        # Try to find existing person by telegram_id
        person = await self.person_repository.get_person_by_telegram_id(
            participant.telegram_id
        )
        self.logger.info(f"Person: {person}")
        if not person:
            # Create new person if not found
            person = ManagementPerson(
                first_name=participant.first_name or "",
                last_name=participant.last_name,
                phone=participant.phone,
                telegram_id=participant.telegram_id,
                user_id=participant.user_id,
            )
            self.logger.info(f"Creating person: {person}")
            person = await self.person_repository.create_person(person)
            self.logger.info(f"Created person: {person}")

        # Link participant to person
        participant.management_person_id = person.id
        participant.chat_id = chat_id
        participants = await self.participant_repository.create_or_update_participants(
            [participant]
        )
        self.logger.info(f"Participants: {participants}")
        return participants[0]

    async def get_chat_user_by_telegram_id(
        self, telegram_id: int, chat_id: str, user_id: str = None, client: Any = None
    ) -> TelegramMessengerChatUser:
        """Get chat user by telegram ID. If not found, creates a new one.

        Args:
            telegram_id: Telegram ID of the user
            chat_id: Chat ID
            user_id: User ID (required if participant needs to be created)
            client: Telethon client (required if participant needs to be created)

        Returns:
            TelegramMessengerChatUser object
        """
        # First try to get existing participant
        participant = await self.participant_repository.get_participant_by_telegram_id(
            telegram_id, chat_id
        )

        if participant:
            return participant

        # If participant not found and we have enough info to create one
        if not participant and user_id and client:
            self.logger.info(
                f"Participant not found, creating new one for telegram_id: {telegram_id}, chat_id: {chat_id}"
            )

            # Fetch user details from Telegram
            try:
                user_entity = await client.get_entity(telegram_id)

                # Create new participant
                new_participant = TelegramMessengerChatUser(
                    telegram_id=telegram_id,
                    user_id=user_id,
                    chat_id=chat_id,
                    username=getattr(user_entity, "username", None),
                    first_name=getattr(user_entity, "first_name", None),
                    last_name=getattr(user_entity, "last_name", None),
                    phone=getattr(user_entity, "phone", None),
                    is_bot=getattr(user_entity, "bot", False),
                    is_admin=False,
                    is_creator=False,
                )

                # Process the participant to link with a person
                processed_participant = await self.process_participant(
                    new_participant, chat_id
                )
                if processed_participant:
                    self.logger.info(
                        f"Created new participant: {processed_participant}"
                    )
                    return processed_participant

            except Exception as e:
                self.logger.error(f"Error creating participant: {e}")

        return participant

    async def create_participant_from_telegram_id(
        self, client: Any, telegram_id: int, chat_id: str, user_id: str
    ) -> Optional[TelegramMessengerChatUser]:
        """Create a new participant from telegram ID if it doesn't exist.

        Args:
            client: Authenticated TelegramClient instance
            telegram_id: Telegram ID of the user
            chat_id: Chat ID
            user_id: User ID

        Returns:
            Created TelegramMessengerChatUser object or None if creation failed
        """
        # Check if participant already exists
        existing_participant = (
            await self.participant_repository.get_participant_by_telegram_id(
                telegram_id, chat_id
            )
        )

        if existing_participant:
            self.logger.info(f"Participant already exists: {existing_participant}")
            return existing_participant

        try:
            # Get user entity from Telegram
            user_entity = await client.get_entity(telegram_id)
            if not isinstance(user_entity, TelethonUser):
                self.logger.warning(f"Entity with ID {telegram_id} is not a user")
                return None

            # Create new participant
            participant = TelegramMessengerChatUser(
                telegram_id=telegram_id,
                user_id=user_id,
                chat_id=chat_id,
                username=getattr(user_entity, "username", None),
                first_name=getattr(user_entity, "first_name", None),
                last_name=getattr(user_entity, "last_name", None),
                phone=getattr(user_entity, "phone", None),
                is_bot=getattr(user_entity, "bot", False),
                is_admin=False,
                is_creator=False,
            )

            # Process the participant to link with a person
            processed_participant = await self.process_participant(participant, chat_id)
            if processed_participant:
                self.logger.info(f"Created participant: {processed_participant}")
                return processed_participant

        except Exception as e:
            self.logger.error(f"Error creating participant from telegram_id: {e}")

        return None
