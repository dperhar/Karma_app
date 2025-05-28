"""Service for message management operations."""

import asyncio
import logging
from typing import Optional

from fastapi import Request

from models.base.message import MessageStatus
from models.base.schemas import (
    MessageCreate,
    MessageResponse,
    MessageStatusUpdate,
)
from services.base.base_service import BaseService
from services.domain.user_service import UserService
from services.external.telegram_bot_service import TelegramBotService
from services.repositories.message_repository import MessageRepository

logger = logging.getLogger(__name__)


class MessageService(BaseService):
    """Service class for message management."""

    def __init__(
        self,
        message_repository: MessageRepository,
        user_service: UserService,
    ):
        super().__init__()
        self.message_repository = message_repository
        self.user_service = user_service
        self.request = None

    def set_request(self, request: Request):
        """Set the current request context for accessing app state.

        Args:
            request: The current FastAPI request
        """
        self.request = request

    async def create_message(self, message_data: MessageCreate) -> MessageResponse:
        """Create a new message with the provided data."""
        message_dict = message_data.model_dump()
        db_message = await self.message_repository.create_message(**message_dict)
        return MessageResponse.model_validate(db_message)

    async def get_message(self, message_id: str) -> Optional[MessageResponse]:
        """Get message by ID."""
        message = await self.message_repository.get_message(message_id)
        return MessageResponse.model_validate(message) if message else None

    async def update_message(
        self, message_id: str, message_data: MessageCreate
    ) -> Optional[MessageResponse]:
        """Update message data."""
        message_dict = message_data.model_dump()
        db_message = await self.message_repository.update_message(
            message_id, **message_dict
        )
        return MessageResponse.model_validate(db_message) if db_message else None

    async def delete_message(self, message_id: str) -> None:
        """Delete message by ID."""
        await self.message_repository.delete_message(message_id)

    async def get_messages(self) -> list[MessageResponse]:
        """Get all messages."""
        messages = await self.message_repository.get_messages()
        return [MessageResponse.model_validate(message) for message in messages]

    async def update_message_status(
        self, message_id: str, status_data: MessageStatusUpdate
    ) -> Optional[MessageResponse]:
        """Update message status."""
        status_dict = status_data.model_dump()
        db_message = await self.message_repository.update_message_status(
            message_id, **status_dict
        )
        return MessageResponse.model_validate(db_message) if db_message else None

    async def publish_message(self, message_id: str, bot) -> Optional[MessageResponse]:
        """Publish message to Telegram."""
        message = await self.get_message(message_id)
        if not message:
            return None

        if not self.request or not hasattr(
            self.request.app.state, "telegram_bot_service"
        ):
            self.logger.warning(
                "Cannot send notification: No request context or TelegramBotService not available"
            )
            return message

        telegram_bot_service = self.request.app.state.telegram_bot_service
        if not telegram_bot_service:
            self.logger.warning(
                "Cannot send notification: TelegramBotService is None in app.state"
            )
            return message

        try:
            await telegram_bot_service.send_message(
                chat_id=message.chat_id,
                text=message.text,
                parse_mode=message.parse_mode,
            )
            await self.update_message_status(
                message_id,
                MessageStatusUpdate(status=MessageStatus.PUBLISHED),
            )
        except Exception as e:
            self.logger.error(f"Error publishing message: {e}")
            await self.update_message_status(
                message_id,
                MessageStatusUpdate(status=MessageStatus.ERROR),
            )
        return message

    async def notify_users_about_message(
        self,
        bot,
        message: str,
        batch_size: int = 30,
        delay_between_batches: float = 1.0,
    ) -> None:
        """Notify users about a new message."""
        if not self.request or not hasattr(
            self.request.app.state, "telegram_bot_service"
        ):
            self.logger.warning(
                "Cannot send notification: No request context or TelegramBotService not available"
            )
            return

        telegram_bot_service = self.request.app.state.telegram_bot_service
        if not telegram_bot_service:
            self.logger.warning(
                "Cannot send notification: TelegramBotService is None in app.state"
            )
            return

        users = await self.user_service.get_users()
        for i in range(0, len(users), batch_size):
            batch = users[i : i + batch_size]
            tasks = [
                self._send_message_to_user(telegram_bot_service, user, message)
                for user in batch
            ]
            await asyncio.gather(*tasks)
            if i + batch_size < len(users):
                await asyncio.sleep(delay_between_batches)

    async def _send_message_to_user(
        self, telegram_bot_service: TelegramBotService, user, message: str
    ) -> None:
        """Send message to a specific user."""
        try:
            await telegram_bot_service.send_message(
                chat_id=user.telegram_id,
                text=message,
            )
        except Exception as e:
            self.logger.error(f"Error sending message to user {user.id}: {e}")
