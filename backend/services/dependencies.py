"""
Dependency injection module for the application.
Provides a container for managing dependencies and their lifecycle.
"""

from typing import Any, Callable, Union

from fastapi import Request

from services.domain.admin_service import AdminService
from services.domain.ai_dialog_service import AIDialogService
from services.domain.data_fetching_service import DataFetchingService
from services.domain.karma_service import KarmaService
from services.domain.menu_service import MenuService
from services.domain.message_service import MessageService
from services.domain.redis_service import RedisDataService
from services.domain.telegram_messenger.auth_service import TelegramMessengerAuthService
from services.domain.telegram_messenger.chat_service import TelegramMessengerChatService
from services.domain.telegram_messenger.chat_user_service import (
    TelegramMessengerChatUserService,
)
from services.domain.telegram_messenger.messages_service import (
    TelegramMessengerMessagesService,
)
from services.domain.user_context_analysis_service import UserContextAnalysisService
from services.domain.user_service import UserService
from services.external.gemini_service import GeminiService
from services.external.langchain_service import LangChainService
from services.external.s3_client import S3Client
from services.external.telegram_bot_service import TelegramBotService
from services.external.telethon_client import TelethonClient
from services.external.telethon_service import TelethonService
from services.external.transcribe_service import TranscribeService
from services.repositories import (
    AdminRepository,
    ChatRepository,
    MenuRepository,
    MessageRepository,
    UserRepository,
)
from services.repositories.ai_dialog_repository import AIDialogRepository
from services.repositories.ai_request_repository import AIRequestRepository
from services.repositories.draft_comment_repository import DraftCommentRepository
from services.repositories.management.person_repository import PersonRepository
from services.repositories.telegram.message_repository import (
    MessageRepository as TelegramMessageRepository,
)
from services.repositories.telegram.participant_repository import ParticipantRepository
from services.websocket_service import WebSocketService


class DependencyContainer:
    """Container for managing dependencies."""

    def __init__(self):
        self._instances: dict[type, Any] = {}
        self._factories: dict[type, Callable] = {}
        self._request_scoped_factories: dict[type, Callable] = {}

    def register(self, interface: type, implementation: Union[type, Callable]):
        """Register a concrete implementation for an interface."""
        if callable(implementation) and hasattr(implementation, "__annotations__") and "request" in implementation.__annotations__:
            self._request_scoped_factories[interface] = implementation
        else:
            self._factories[interface] = implementation

    def resolve(self, interface: type, request: Union[Request, None] = None) -> Any:
        """Resolve a dependency."""
        if interface in self._request_scoped_factories:
            if not request:
                # During initialization, skip request-scoped dependencies
                return None
            return self._request_scoped_factories[interface](request)

        if interface not in self._instances:
            if interface not in self._factories:
                raise ValueError(f"No implementation registered for {interface}")
            implementation = self._factories[interface]
            self._instances[interface] = implementation()
        return self._instances[interface]

    def get_registered_repositories(self) -> list[type]:
        """Get all registered repository types."""
        return list(self._factories.keys())

    def initialize(self):
        """Initialize all non-request-scoped dependencies."""
        for repository_class in self.get_registered_repositories():
            if repository_class not in self._request_scoped_factories:
                self.resolve(repository_class)

        # Initialize non-request-scoped services
        for service_class in [
            AdminService,
            MenuService,
            UserService,
            S3Client,
            AIDialogService,
        ]:
            if service_class not in self._request_scoped_factories:
                self.resolve(service_class)


# Create global container instance
container = DependencyContainer()

# Register repositories
container.register(UserRepository, UserRepository)
container.register(MessageRepository, MessageRepository)
container.register(MenuRepository, MenuRepository)
container.register(AdminRepository, AdminRepository)
container.register(ChatRepository, ChatRepository)
container.register(TelegramMessageRepository, TelegramMessageRepository)
container.register(ParticipantRepository, ParticipantRepository)
container.register(PersonRepository, PersonRepository)
container.register(AIDialogRepository, AIDialogRepository)
container.register(AIRequestRepository, AIRequestRepository)
container.register(DraftCommentRepository, DraftCommentRepository)

# Register external services
container.register(GeminiService, GeminiService)
container.register(LangChainService, LangChainService)

# Register Telethon services
container.register(TelethonClient, TelethonClient)
container.register(TelethonService, TelethonService)


# Service factory functions
def get_telegram_bot_service(request: Request) -> TelegramBotService:
    """Get TelegramBotService instance with dependencies."""
    if not hasattr(request.app.state, "telegram_bot_service"):
        raise RuntimeError("TelegramBotService not initialized in application state")
    return request.app.state.telegram_bot_service


def get_user_service() -> UserService:
    """Get UserService instance with dependencies."""
    user_repository = container.resolve(UserRepository)
    return UserService(user_repository)


def get_menu_service() -> MenuService:
    """Get MenuService instance with dependencies."""
    menu_repository = container.resolve(MenuRepository)
    return MenuService(menu_repository)


def get_admin_service() -> AdminService:
    """Get AdminService instance with dependencies."""
    admin_repository = container.resolve(AdminRepository)
    return AdminService(admin_repository)


def get_message_service() -> MessageService:
    """Get MessageService instance with dependencies."""
    message_repository = container.resolve(MessageRepository)
    user_service = container.resolve(UserService)
    return MessageService(
        message_repository=message_repository,
        user_service=user_service,
    )


def get_ai_dialog_service() -> AIDialogService:
    """Get AIDialogService instance with dependencies."""
    dialog_repository = container.resolve(AIDialogRepository)
    request_repository = container.resolve(AIRequestRepository)
    message_repository = container.resolve(TelegramMessageRepository)
    return AIDialogService(
        dialog_repository=dialog_repository,
        request_repository=request_repository,
        message_repository=message_repository,
    )


def get_s3_client() -> S3Client:
    """Get S3Client instance."""
    return S3Client()


def get_websocket_service() -> WebSocketService:
    """Get WebSocketService instance."""
    return WebSocketService()


def get_gemini_service() -> GeminiService:
    """Get GeminiService instance."""
    return GeminiService()


def get_langchain_service() -> LangChainService:
    """Get LangChainService instance."""
    return LangChainService()


def get_user_context_analysis_service() -> UserContextAnalysisService:
    """Get UserContextAnalysisService instance with dependencies."""
    user_repository = container.resolve(UserRepository)
    telethon_service = container.resolve(TelethonService)
    gemini_service = container.resolve(GeminiService)
    return UserContextAnalysisService(
        user_repository=user_repository,
        telethon_service=telethon_service,
        gemini_service=gemini_service,
    )


def get_karma_service() -> KarmaService:
    """Get KarmaService instance with dependencies."""
    draft_comment_repository = container.resolve(DraftCommentRepository)
    user_repository = container.resolve(UserRepository)
    gemini_service = container.resolve(GeminiService)
    langchain_service = container.resolve(LangChainService)
    telethon_service = container.resolve(TelethonService)
    websocket_service = container.resolve(WebSocketService)
    
    return KarmaService(
        draft_comment_repository=draft_comment_repository,
        user_repository=user_repository,
        gemini_service=gemini_service,
        langchain_service=langchain_service,
        telethon_service=telethon_service,
        websocket_service=websocket_service,
    )


def get_data_fetching_service() -> DataFetchingService:
    """Get DataFetchingService instance with dependencies."""
    user_repository = container.resolve(UserRepository)
    chat_repository = container.resolve(ChatRepository)
    message_repository = container.resolve(TelegramMessageRepository)
    telethon_client = container.resolve(TelethonClient)
    telethon_service = container.resolve(TelethonService)
    karma_service = container.resolve(KarmaService)
    user_context_analysis_service = container.resolve(UserContextAnalysisService)
    websocket_service = container.resolve(WebSocketService)
    
    return DataFetchingService(
        user_repository=user_repository,
        chat_repository=chat_repository,
        message_repository=message_repository,
        telethon_client=telethon_client,
        telethon_service=telethon_service,
        karma_service=karma_service,
        user_context_analysis_service=user_context_analysis_service,
        websocket_service=websocket_service,
    )


def get_telethon_client() -> TelethonClient:
    """Get TelethonClient instance with dependencies."""
    user_repository = container.resolve(UserRepository)
    return TelethonClient(user_repository=user_repository, container=container)


def get_telethon_service() -> TelethonService:
    """Get TelethonService instance with dependencies."""
    service = TelethonService()
    service.set_container(container)
    return service


def get_telegram_messenger_auth_service() -> TelegramMessengerAuthService:
    """Get TelegramMessengerAuthService instance with dependencies."""
    user_service = container.resolve(UserService)
    telethon_client = container.resolve(TelethonClient)
    redis_service = container.resolve(RedisDataService)
    return TelegramMessengerAuthService(
        user_service=user_service,
        telethon_client=telethon_client,
        redis_service=redis_service,
    )


def get_telegram_messenger_chat_service() -> TelegramMessengerChatService:
    """Get TelegramMessengerChatService instance with dependencies."""
    telethon_service = container.resolve(TelethonService)
    chat_repository = container.resolve(ChatRepository)
    return TelegramMessengerChatService(
        telethon_service=telethon_service,
        chat_repository=chat_repository,
    )


def get_telegram_messenger_messages_service() -> TelegramMessengerMessagesService:
    """Get TelegramMessengerMessagesService instance with dependencies."""
    telethon_service = container.resolve(TelethonService)
    chat_repository = container.resolve(ChatRepository)
    message_repository = container.resolve(TelegramMessageRepository)
    chat_user_service = container.resolve(TelegramMessengerChatUserService)
    person_repository = container.resolve(PersonRepository)
    return TelegramMessengerMessagesService(
        telethon_service=telethon_service,
        chat_repository=chat_repository,
        message_repository=message_repository,
        chat_user_service=chat_user_service,
        person_repository=person_repository,
    )


def get_telegram_messenger_chat_user_service() -> TelegramMessengerChatUserService:
    """Get TelegramMessengerChatUserService instance with dependencies."""
    telethon_service = container.resolve(TelethonService)
    chat_repository = container.resolve(ChatRepository)
    participant_repository = container.resolve(ParticipantRepository)
    person_repository = container.resolve(PersonRepository)
    return TelegramMessengerChatUserService(
        telethon_service=telethon_service,
        chat_repository=chat_repository,
        participant_repository=participant_repository,
        person_repository=person_repository,
    )


def get_redis_data_service() -> RedisDataService:
    """Get RedisDataService instance."""
    return RedisDataService()


def get_transcribe_service() -> TranscribeService:
    """Get TranscribeService instance."""
    return TranscribeService()


# Register services
container.register(WebSocketService, get_websocket_service)
container.register(TelegramBotService, get_telegram_bot_service)
container.register(UserService, get_user_service)
container.register(MenuService, get_menu_service)
container.register(AdminService, get_admin_service)
container.register(MessageService, get_message_service)
container.register(AIDialogService, get_ai_dialog_service)
container.register(S3Client, get_s3_client)
container.register(GeminiService, get_gemini_service)
container.register(LangChainService, get_langchain_service)
container.register(UserContextAnalysisService, get_user_context_analysis_service)
container.register(KarmaService, get_karma_service)
container.register(DataFetchingService, get_data_fetching_service)
container.register(TelethonClient, get_telethon_client)
container.register(TelethonService, get_telethon_service)
container.register(TelegramMessengerAuthService, get_telegram_messenger_auth_service)
container.register(TelegramMessengerChatService, get_telegram_messenger_chat_service)
container.register(
    TelegramMessengerMessagesService, get_telegram_messenger_messages_service
)
container.register(
    TelegramMessengerChatUserService, get_telegram_messenger_chat_user_service
)
container.register(RedisDataService, get_redis_data_service)
container.register(TranscribeService, get_transcribe_service)

# Initialize repositories and services
container.initialize()
