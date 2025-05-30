"""Repository for Telegram chat user operations."""

from collections.abc import Sequence
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from models.telegram_messenger.chat import TelegramMessengerChat
from models.telegram_messenger.chat_user import TelegramMessengerChatUser
from services.base.base_repository import BaseRepository


class ParticipantRepository(BaseRepository):
    """Repository class for Telegram chat user operations."""

    async def create_or_update_participants(
        self, participants: Sequence[TelegramMessengerChatUser]
    ) -> list[TelegramMessengerChatUser]:
        """Create or update multiple chat users.

        Args:
            participants: List of TelegramMessengerChatUser objects to create or update

        Returns:
            List of created/updated TelegramMessengerChatUser objects
        """
        if not participants:
            self.logger.warning("No participants provided to create or update")
            return []

        async with self.get_session() as session:
            try:
                result_participants = []
                for participant in participants:
                    if not participant or not participant.chat_id:
                        self.logger.warning(
                            "Skipping invalid participant: missing chat_id"
                        )
                        continue

                    # Check if participant exists by telegram_id and chat_id
                    query = select(TelegramMessengerChatUser).where(
                        TelegramMessengerChatUser.telegram_id
                        == participant.telegram_id,
                        TelegramMessengerChatUser.chat_id == participant.chat_id,
                    )
                    result = await session.execute(query)
                    existing_participant = result.unique().scalar_one_or_none()

                    if existing_participant:
                        # Update existing participant
                        for key, value in participant.__dict__.items():
                            if key != "id" and not key.startswith("_"):
                                setattr(existing_participant, key, value)
                        result_participants.append(existing_participant)
                    else:
                        # Create new participant
                        session.add(participant)
                        result_participants.append(participant)

                if not result_participants:
                    self.logger.warning("No valid participants were processed")
                    return []

                await session.commit()
                for participant in result_participants:
                    await session.refresh(participant)

                self.logger.info(
                    f"Successfully processed {len(result_participants)} chat users"
                )
                return result_participants

            except SQLAlchemyError as e:
                await session.rollback()
                self.logger.error(
                    f"Error creating/updating chat users: {e!s}", exc_info=True
                )
                raise

    async def get_participant(
        self, participant_id: str
    ) -> Optional[TelegramMessengerChatUser]:
        """Get chat user by ID.

        Args:
            participant_id: Chat user ID

        Returns:
            TelegramMessengerChatUser object or None if not found
        """
        if not participant_id:
            self.logger.warning("No participant_id provided")
            return None

        async with self.get_session() as session:
            try:
                query = select(TelegramMessengerChatUser).where(
                    TelegramMessengerChatUser.id == participant_id
                )
                result = await session.execute(query)
                participant = result.unique().scalar_one_or_none()
                if not participant:
                    self.logger.info(f"Chat user not found with id: {participant_id}")
                return participant
            except SQLAlchemyError as e:
                self.logger.error(f"Error getting chat user: {e!s}", exc_info=True)
                raise

    async def get_chat_participants(
        self, chat_id: str, limit: int = 100, offset: int = 0
    ) -> list[TelegramMessengerChatUser]:
        """Get chat users for a chat.

        Args:
            chat_id: Chat ID
            limit: Maximum number of chat users to retrieve
            offset: Number of chat users to skip

        Returns:
            List of TelegramMessengerChatUser objects
        """
        if not chat_id:
            self.logger.warning("No chat_id provided")
            return []

        async with self.get_session() as session:
            try:
                # First verify that the chat exists
                chat_query = select(TelegramMessengerChat).where(
                    TelegramMessengerChat.id == chat_id
                )
                chat_result = await session.execute(chat_query)
                chat = chat_result.unique().scalar_one_or_none()

                if not chat:
                    self.logger.error(f"Chat not found with id: {chat_id}")
                    return []

                query = (
                    select(TelegramMessengerChatUser)
                    .where(TelegramMessengerChatUser.chat_id == chat_id)
                    .limit(limit)
                    .offset(offset)
                )
                result = await session.execute(query)
                participants = result.unique().scalars().all()
                return list(participants)
            except SQLAlchemyError as e:
                self.logger.error(f"Error getting chat users: {e!s}", exc_info=True)
                raise

    async def get_participant_by_telegram_id(
        self, telegram_id: int, chat_id: str
    ) -> Optional[TelegramMessengerChatUser]:
        """Get chat user by Telegram ID and chat ID.

        Args:
            telegram_id: Telegram user ID
            chat_id: Chat ID

        Returns:
            TelegramMessengerChatUser object or None if not found
        """
        if not telegram_id or not chat_id:
            self.logger.warning("Missing telegram_id or chat_id")
            return None

        async with self.get_session() as session:
            try:
                # First verify that the chat exists
                chat_query = select(TelegramMessengerChat).where(
                    TelegramMessengerChat.id == chat_id
                )
                chat_result = await session.execute(chat_query)
                chat = chat_result.unique().scalar_one_or_none()

                if not chat:
                    self.logger.error(f"Chat not found with id: {chat_id}")
                    return None

                query = select(TelegramMessengerChatUser).where(
                    TelegramMessengerChatUser.telegram_id == telegram_id,
                    TelegramMessengerChatUser.chat_id == chat_id,
                )
                result = await session.execute(query)

                # Instead of scalar_one_or_none(), use scalars().first() to prevent MultipleResultsFound error
                participant = result.unique().scalars().first()

                if not participant:
                    self.logger.info(
                        f"Chat user not found with telegram_id: {telegram_id}, chat_id: {chat_id}"
                    )
                return participant
            except SQLAlchemyError as e:
                self.logger.error(f"Error getting chat user: {e!s}", exc_info=True)
                raise
