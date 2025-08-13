"""Service for Telegram Messenger messages and participants operations."""

from typing import Any
from uuid import uuid4

from app.models.person import ManagementPerson
from app.models.chat import (
    TelegramMessengerChat,
    TelegramMessengerChatType,
)
from app.models.chat_user import TelegramMessengerChatUser
from app.models.telegram_message import TelegramMessengerMessage
from app.services.base_service import BaseService
from app.services.telegram_chat_user_service import (
    TelegramMessengerChatUserService,
)
from app.services.telegram_service import TelegramService
from app.repositories.chat_repository import ChatRepository
from app.repositories.message_repository import MessageRepository


class TelegramMessengerMessagesService(BaseService):
    """Service class for Telegram Messenger messages and participants operations."""

    def __init__(
        self,
        telegram_service: TelegramService,
        chat_user_service: TelegramMessengerChatUserService,
        chat_repository: ChatRepository,
        message_repository: MessageRepository,
        person_repository: Any,
    ):
        """Initialize the service with required dependencies."""
        super().__init__()
        self.telegram_service = telegram_service
        self.chat_repository = chat_repository
        self.message_repository = message_repository
        self.chat_user_service = chat_user_service
        self.person_repository = person_repository

    async def get_chat_messages(
        self,
        client: Any,
        chat: TelegramMessengerChat,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TelegramMessengerMessage]:
        """Get chat messages.

        Args:
            client: Authenticated TelegramClient instance
            chat: TelegramMessengerChat object
            limit: Maximum number of messages to retrieve
            offset: Number of messages to skip

        Returns:
            list of TelegramMessengerMessage objects
        """
        messages = await self.telethon_service.sync_chat_messages(
            client=client,
            chat_telegram_id=chat.telegram_id,
            limit=limit,
            offset=offset,
        )
        if messages:
            # Convert dictionary messages to TelegramMessengerMessage objects
            message_objects = []
            # Helpers for enrichment
            import re as _re
            def _detect_language_simple(text: str) -> str:
                cyr = sum(1 for ch in text if "\u0400" <= ch <= "\u04FF")
                lat = sum(1 for ch in text if ("a" <= ch.lower() <= "z"))
                if cyr and not lat:
                    return "ru"
                if lat and not cyr:
                    return "en"
                return "mixed" if cyr and lat else "unknown"
            def _extract_links(text: str) -> list[str]:
                return _re.findall(r"https?://\S+", text)
            def _extract_entities_simple(text: str) -> list[str]:
                return [
                    _re.sub(r"\s+", " ", m.group(0)).strip()
                    for m in _re.finditer(r"(?:\b[А-ЯЁ][а-яё]+\b(?:\s+|\-)){1,3}\b[А-ЯЁ][а-яё]+\b", text)
                ][:10]
            def _rhetoric(text: str) -> str:
                t = (text or "").strip()
                if t.endswith("?"):
                    return "question"
                if t.endswith("!"):
                    return "exclamation"
                return "statement"
            def _style_snapshot(text: str) -> dict:
                t = text or ""
                return {
                    "len": len(t),
                    "exclam": t.count("!"),
                    "quest": t.count("?"),
                    "dots3": t.count("..."),
                }
            def _env_quadrant_for_chat(chat_title: str) -> str:
                # Fallback map using chat.title and simple heuristics
                title = (chat_title or chat.title or "").lower()
                if any(k in title for k in ["club", "dev", "it", "data", "ai", "форум", "клуб"]):
                    return "HIGH_SAFE_HIGH_DEPTH"
                return "HIGH_SAFE_LOW_DEPTH"
            for message_data in messages:
                # Use enhanced method that creates user if not found
                sender = await self.chat_user_service.get_chat_user_by_telegram_id(
                    message_data["sender_telegram_id"],
                    chat.id,
                    user_id=chat.user_id,
                    client=client,
                )
                if not sender:
                    if chat.type == TelegramMessengerChatType.CHANNEL:
                        # Check if person already exists
                        person = await self.person_repository.get_person_by_telegram_id(
                            message_data["sender_telegram_id"]
                        )
                        if not person:
                            # Create a person for the channel
                            person = ManagementPerson(
                                id=uuid4().hex,
                                telegram_id=message_data["sender_telegram_id"],
                                first_name=chat.title or "Channel",
                                user_id=chat.user_id,
                            )
                            person = await self.person_repository.create_person(person)

                        # Create a chat user for the channel
                        sender = TelegramMessengerChatUser(
                            id=uuid4().hex,
                            telegram_id=message_data["sender_telegram_id"],
                            user_id=chat.user_id,
                            chat_id=chat.id,
                            management_person_id=person.id,
                            first_name=chat.title or "Channel",
                            is_bot=False,
                            is_admin=True,
                            is_creator=True,
                        )
                        sender = await self.chat_user_service.process_participant(
                            sender, chat.id
                        )
                    else:
                        # Instead of skipping, try to create a user for non-channel chats
                        sender = await self.chat_user_service.create_participant_from_telegram_id(
                            client=client,
                            telegram_id=message_data["sender_telegram_id"],
                            chat_id=chat.id,
                            user_id=chat.user_id,
                        )

                        if not sender:
                            self.logger.warning(
                                f"Could not create sender for telegram_id: {message_data['sender_telegram_id']}"
                            )
                            continue  # Skip messages where we couldn't create a sender

                text = message_data.get("message_text")
                message = TelegramMessengerMessage(
                    id=uuid4().hex,
                    telegram_id=message_data["message_telegram_id"],
                    chat_id=chat.id,
                    sender_id=sender.id,
                    reply_to_message_telegram_id=message_data.get(
                        "reply_to_message_telegram_id"
                    ),
                    text=text,
                    date=message_data["message_date"],
                    edit_date=message_data.get("edit_date"),
                    media_type=message_data.get("media_type"),
                    file_id=message_data.get("file_id"),
                    language=_detect_language_simple(text or ""),
                    link_urls=_extract_links(text or ""),
                    named_entities=_extract_entities_simple(text or ""),
                    tokens=(text or "").lower().split()[:32],
                    rhetorical_type=_rhetoric(text or ""),
                    env_quadrant=_env_quadrant_for_chat(chat.title),
                    style_snapshot=_style_snapshot(text or ""),
                )
                message_objects.append(message)
            return await self.message_repository.create_or_update_messages(
                message_objects
            )
        return []
