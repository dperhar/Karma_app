"""Service for AI dialog management operations."""

import logging
from typing import Any, Optional

from app.models.ai_dialog import AIDialog
from app.models.ai_request import AIRequestModel
from app.schemas.ai import (
    AIDialogCreate,
    AIDialogResponse,
    AIDialogWithMessages,
    AIRequestCreate,
    AIRequestResponse,
    LangChainMessageRequest,
)
from app.services.base_service import BaseService
from app.services.langchain_service import LangChainRequest, langchain_service
from app.repositories.ai_dialog_repository import AIDialogRepository
from app.repositories.ai_request_repository import AIRequestRepository
from app.repositories.message_repository import (
    MessageRepository as TelegramMessageRepository,
)

logger = logging.getLogger(__name__)


class AIDialogService(BaseService):
    """Service class for AI dialog management."""

    def __init__(
        self,
        dialog_repository: AIDialogRepository,
        request_repository: AIRequestRepository,
        message_repository: TelegramMessageRepository = None,
    ):
        super().__init__()
        self.dialog_repository = dialog_repository
        self.request_repository = request_repository
        self.message_repository = message_repository

    def _convert_db_model_to_dict(self, db_model) -> dict[str, Any]:
        """Convert a database model to a dictionary for Pydantic validation."""
        result = {}
        for column in db_model.__table__.columns:
            column_name = column.name
            value = getattr(db_model, column_name)
            # Convert datetime objects to string for proper serialization
            if hasattr(value, "isoformat"):
                value = value.isoformat()
            result[column_name] = value
        return result

    async def create_dialog(
        self, dialog_data: AIDialogCreate
    ) -> Optional[AIDialogResponse]:
        """Create a new AI dialog."""
        try:
            dialog_dict = dialog_data.model_dump()
            db_dialog = await self.dialog_repository.create_dialog(**dialog_dict)
            if not db_dialog:
                return None

            # Convert to dict first
            dialog_dict = self._convert_db_model_to_dict(db_dialog)
            return AIDialogResponse.model_validate(dialog_dict)
        except Exception as e:
            logger.error(f"Error creating AI dialog: {e!s}")
            raise

    async def create_dialog_with_user_id(
        self, chat_id: str, user_id: str
    ) -> Optional[AIDialogResponse]:
        """Create a new AI dialog with chat_id and user_id."""
        try:
            dialog_data = {
                "chat_id": chat_id,
                "user_id": user_id,
            }
            db_dialog = await self.dialog_repository.create_dialog(**dialog_data)
            if not db_dialog:
                return None

            # Convert to dict first
            dialog_dict = self._convert_db_model_to_dict(db_dialog)
            return AIDialogResponse.model_validate(dialog_dict)
        except Exception as e:
            logger.error(f"Error creating AI dialog: {e!s}")
            raise

    async def get_dialog(self, dialog_id: str) -> Optional[AIDialogResponse]:
        """Get AI dialog by ID."""
        try:
            dialog = await self.dialog_repository.get_dialog(dialog_id)
            if not dialog:
                return None

            # Convert to dict first
            dialog_dict = self._convert_db_model_to_dict(dialog)
            return AIDialogResponse.model_validate(dialog_dict)
        except Exception as e:
            logger.error(f"Error getting AI dialog: {e!s}")
            raise

    async def get_dialogs_by_chat_id(self, chat_id: str) -> list[AIDialogResponse]:
        """Get all AI dialogs by chat ID."""
        try:
            dialogs = await self.dialog_repository.get_dialogs_by_chat_id(chat_id)
            result = []
            for dialog in dialogs:
                # Convert to dict first
                dialog_dict = self._convert_db_model_to_dict(dialog)
                result.append(AIDialogResponse.model_validate(dialog_dict))
            return result
        except Exception as e:
            logger.error(f"Error getting AI dialogs by chat ID: {e!s}")
            raise

    async def get_dialogs_by_user_id(self, user_id: str) -> list[AIDialogResponse]:
        """Get all AI dialogs by user ID."""
        try:
            dialogs = await self.dialog_repository.get_dialogs_by_user_id(user_id)
            result = []
            for dialog in dialogs:
                # Convert to dict first
                dialog_dict = self._convert_db_model_to_dict(dialog)
                result.append(AIDialogResponse.model_validate(dialog_dict))
            return result
        except Exception as e:
            logger.error(f"Error getting AI dialogs by user ID: {e!s}")
            raise

    async def create_request(
        self, request_data: AIRequestCreate
    ) -> Optional[AIRequestResponse]:
        """Create a new AI request."""
        try:
            request_dict = request_data.model_dump()
            db_request = await self.request_repository.create_request(**request_dict)
            if not db_request:
                return None

            # Convert to dict first
            request_dict = self._convert_db_model_to_dict(db_request)
            return AIRequestResponse.model_validate(request_dict)
        except Exception as e:
            logger.error(f"Error creating AI request: {e!s}")
            raise

    async def get_requests_by_dialog_id(
        self, dialog_id: str
    ) -> list[AIRequestResponse]:
        """Get all AI requests by dialog ID."""
        try:
            requests = await self.request_repository.get_requests_by_dialog_id(
                dialog_id
            )
            result = []
            for request in requests:
                # Convert to dict first
                request_dict = self._convert_db_model_to_dict(request)
                result.append(AIRequestResponse.model_validate(request_dict))
            return result
        except Exception as e:
            logger.error(f"Error getting AI requests: {e!s}")
            raise

    async def get_dialog_with_requests(
        self, dialog_id: str
    ) -> Optional[AIDialogWithMessages]:
        """Get AI dialog with all requests."""
        try:
            dialog = await self.get_dialog(dialog_id)
            if not dialog:
                return None

            requests = await self.get_requests_by_dialog_id(dialog_id)
            return AIDialogWithMessages(dialog=dialog, messages=requests)
        except Exception as e:
            logger.error(f"Error getting AI dialog with requests: {e!s}")
            raise

    async def _get_dialog_or_none(self, dialog_id: str) -> Optional[AIDialog]:
        """Get dialog by ID or return None if it does not exist."""
        dialog = await self.dialog_repository.get_dialog(dialog_id)
        if not dialog:
            logger.error(f"Dialog not found: {dialog_id}")
        return dialog

    async def _get_previous_messages_context(self, dialog_id: str) -> list[dict]:
        """Get formatted message history from previous AI requests."""
        previous_requests = await self.request_repository.get_requests_by_dialog_id(
            dialog_id
        )

        formatted_messages = []
        for req in previous_requests:
            formatted_messages.append({"role": "user", "content": req.request_text})
            formatted_messages.append(
                {"role": "assistant", "content": req.response_text}
            )

        return formatted_messages

    async def _get_chat_context(
        self, chat_id: str, limit: int
    ) -> tuple[list, str, list]:
        """Get chat context from Telegram messages.

        Returns:
            tuple containing:
            - raw message objects
            - formatted chat context as string
            - formatted message list for variables
        """
        if not self.message_repository or not chat_id:
            return [], "", []

        # Get latest messages from chat
        chat_messages = await self.message_repository.get_chat_messages(
            chat_id=chat_id, limit=limit
        )

        if not chat_messages:
            return [], "", []

        # Create text representation of messages
        messages_text = []

        # Process messages and add to formatted_messages list
        for msg in chat_messages:
            # Format user info, including first_name, last_name and username if available
            user_info = ""
            if hasattr(msg, "sender_first_name") and msg.sender_first_name:
                user_info += msg.sender_first_name
                if hasattr(msg, "sender_last_name") and msg.sender_last_name:
                    user_info += f" {msg.sender_last_name}"
            elif hasattr(msg, "sender_username") and msg.sender_username:
                user_info = f"@{msg.sender_username}"
            else:
                user_info = f"User {msg.sender_id}"

            # Insert at the beginning of the list to reverse the order
            messages_text.insert(0, f"{user_info}: {msg.text}")

        chat_context = "Последние сообщения в чате:\n" + "\n".join(messages_text)

        return chat_context

    async def _create_langchain_request(
        self,
        request: LangChainMessageRequest,
        model_enum: AIRequestModel,
        formatted_messages: list[dict],
        chat_context: str,
        formatted_chat_messages: list[dict],
    ) -> LangChainRequest:
        """Create a LangChain request with all necessary parameters."""
        return LangChainRequest(
            model_name=model_enum,
            prompt_template=request.prompt_template,
            input_variables={
                "messages": formatted_messages,
                "chat_context": chat_context,
                "chat_messages": formatted_chat_messages,
            },
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

    async def _create_ai_request(
        self,
        dialog_id: str,
        user_id: str,
        request_text: str,
        response_text: str,
        model: AIRequestModel,
    ) -> Optional[AIRequestResponse]:
        """Create an AI request record in the database."""
        ai_request_data = AIRequestCreate(
            dialog_id=dialog_id,
            user_id=user_id,
            request_text=request_text,
            response_text=response_text,
            model=model,
        )
        return await self.create_request(ai_request_data)

    async def process_message(
        self, request: LangChainMessageRequest, current_user_name: str
    ) -> Optional[AIRequestResponse]:
        """Process a user message using LangChain and create a response."""
        try:
            # Get dialog and validate it exists
            dialog = await self._get_dialog_or_none(request.dialog_id)
            if not dialog:
                return None

            # Get conversation history and format it
            formatted_messages = await self._get_previous_messages_context(
                request.dialog_id
            )
            self.logger.info(f"Formatted messages: {formatted_messages}")

            # Get Telegram chat context if available
            chat_context = await self._get_chat_context(
                dialog.chat_id, request.dialog_context_length
            )
            self.logger.info(f"Chat context: {chat_context}")

            # Convert model name to AIRequestModel enum
            model_enum = self._get_model_enum(request.model_name)
            self.logger.info(f"Model enum: {model_enum}")
            # Create and send LangChain request

            langchain_request = LangChainRequest(
                model_name=model_enum,
                prompt_template=request.prompt_template,
                input_variables={
                    "author_name": current_user_name,
                    "messages_context": chat_context,
                    "user_request": request.content,
                },
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )

            # # Send request to LangChain service
            response = await langchain_service.process_request(langchain_request)

            # # Handle response and create AI request record
            if response.get("status") == "success":
                return await self._create_ai_request(
                    request.dialog_id,
                    dialog.user_id,
                    request.content,
                    response.get("result", ""),
                    model_enum,
                )
            else:
                logger.error(f"LangChain error: {response.get('error')}")
                error_message = f"Error processing message: {response.get('error', 'Unknown error')}"

                return await self._create_ai_request(
                    request.dialog_id,
                    dialog.user_id,
                    request.content,
                    error_message,
                    model_enum,
                )

        except Exception as e:
            logger.error(f"Error processing message: {e!s}")
            raise

    def _get_model_enum(self, model_name: str) -> AIRequestModel:
        """Convert string model name to AIRequestModel enum."""
        # Map common model names to our enum values
        model_map = {
            "gpt-4.1": AIRequestModel.GPT_4_1,
            "gpt-4.1-nano": AIRequestModel.GPT_4_1_NANO,
            "gpt-4.1-mini": AIRequestModel.GPT_4_1_MINI,
            "claude-3-7-sonnet": AIRequestModel.CLAUDE_3_7_SONNET,
            "claude-3-7-sonnet-20250219": AIRequestModel.CLAUDE_3_7_SONNET,
            "claude-3-5-haiku-20241022": AIRequestModel.CLAUDE_3_5_HAIKU,
        }

        # Return the mapped enum or default to GPT_4_1
        return model_map.get(model_name.lower(), AIRequestModel.GPT_4_1)
