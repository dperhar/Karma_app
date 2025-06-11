"""Dependency Injection container setup."""

from punq import Container, Scope

# Repositories
from app.repositories.admin_repository import AdminRepository
from app.repositories.ai_dialog_repository import AIDialogRepository
from app.repositories.ai_profile_repository import AIProfileRepository
from app.repositories.ai_request_repository import AIRequestRepository
from app.repositories.chat_repository import ChatRepository
from app.repositories.draft_comment_repository import DraftCommentRepository
from app.repositories.menu_repository import MenuRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.negative_feedback_repository import NegativeFeedbackRepository
from app.repositories.participant_repository import ParticipantRepository
from app.repositories.person_repository import PersonRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.telegram_connection_repository import TelegramConnectionRepository
from app.repositories.user_repository import UserRepository

# Services
from app.services.admin_service import AdminService
from app.services.ai_dialog_service import AIDialogService
from app.services.ai_service import AIService
from app.services.data_fetching_service import DataFetchingService
from app.services.draft_generation_service import DraftGenerationService
from app.services.draft_service import DraftService
from app.services.encryption_service import EncryptionService
from app.services.gemini_service import GeminiService
from app.services.jwt_service import JWTService
from app.services.karma_service import KarmaService
from app.services.langchain_service import LangChainService
from app.services.menu_service import MenuService
from app.services.message_service import MessageService
from app.services.redis_service import RedisService
from app.services.refactored_client_service import RefactoredTelethonClientService
from app.services.scheduler_service import SchedulerService
from app.services.telegram_auth_service import TelegramMessengerAuthService
from app.services.telegram_chat_service import TelegramMessengerChatService
from app.services.telegram_chat_user_service import TelegramMessengerChatUserService
from app.services.telegram_messages_service import TelegramMessengerMessagesService
from app.services.telegram_service import TelegramService
from app.services.telethon_client import TelethonClient
from app.services.telethon_service import TelethonService as OldTelethonService
from app.services.user_context_analysis_service import UserContextAnalysisService
from app.services.user_service import UserService
from app.services.domain.websocket_service import WebSocketService

# Create DI container
container = Container()

# Register repositories as singletons
container.register(AdminRepository, scope=Scope.singleton)
container.register(AIDialogRepository, scope=Scope.singleton)
container.register(AIProfileRepository, scope=Scope.singleton)
container.register(AIRequestRepository, scope=Scope.singleton)
container.register(ChatRepository, scope=Scope.singleton)
container.register(DraftCommentRepository, scope=Scope.singleton)
container.register(MenuRepository, scope=Scope.singleton)
container.register(MessageRepository, scope=Scope.singleton)
container.register(NegativeFeedbackRepository, scope=Scope.singleton)
container.register(ParticipantRepository, scope=Scope.singleton)
container.register(PersonRepository, scope=Scope.singleton)
container.register(RefreshTokenRepository, scope=Scope.singleton)
container.register(TelegramConnectionRepository, scope=Scope.singleton)
container.register(UserRepository, scope=Scope.singleton)

# Register services
container.register(AdminService)
container.register(AIDialogService)
container.register(AIService)
container.register(DataFetchingService)
container.register(DraftGenerationService)
container.register(DraftService)
container.register(EncryptionService, scope=Scope.singleton)
container.register(GeminiService, scope=Scope.singleton)
container.register(JWTService)
container.register(KarmaService)
container.register(LangChainService, scope=Scope.singleton)
container.register(MenuService)
container.register(MessageService)
container.register(RedisService, scope=Scope.singleton)
container.register(RefactoredTelethonClientService, scope=Scope.singleton)
container.register(SchedulerService, scope=Scope.singleton)
container.register(TelegramMessengerAuthService)
container.register(TelegramMessengerChatService)
container.register(TelegramMessengerChatUserService)
container.register(TelegramMessengerMessagesService)
container.register(TelegramService)
container.register(TelethonClient, scope=Scope.singleton)
container.register(OldTelethonService, scope=Scope.singleton)
container.register(UserContextAnalysisService)
container.register(UserService)
container.register(WebSocketService, scope=Scope.singleton) 