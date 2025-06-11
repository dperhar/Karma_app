import asyncio
import logging

from celery_config import celery_app
from app.core.dependencies import container
from app.repositories.user_repository import UserRepository
from app.services.telethon_client import TelethonClient
from app.services.user_context_analysis_service import UserContextAnalysisService
from app.services.domain.websocket_service import WebSocketService
from app.services.encryption_service import get_encryption_service

logger = logging.getLogger(__name__)

@celery_app.task(name="tasks.analyze_vibe_profile")
def analyze_vibe_profile(user_id: str):
    """Celery task to analyze a user's vibe profile asynchronously."""
    logger.info(f"Starting vibe profile analysis task for user_id: {user_id}")
    asyncio.run(async_analyze_vibe_profile(user_id))

async def async_analyze_vibe_profile(user_id: str):
    """The async implementation of the vibe profile analysis."""
    user_repo = container.resolve(UserRepository)
    telethon_client = container.resolve(TelethonClient)
    analysis_service = container.resolve(UserContextAnalysisService)
    websocket_service = container.resolve(WebSocketService)
    encryption_service = get_encryption_service()

    user = await user_repo.get_user(user_id)
    if not user or not user.telegram_connection or not user.telegram_connection.session_string_encrypted:
        logger.error(f"User {user_id} not found or has no valid session for analysis.")
        await websocket_service.send_user_notification(user_id, "vibe_profile_failed", {"error": "Invalid or missing Telegram session."})
        return

    decrypted_session = encryption_service.decrypt_session_string(user.telegram_connection.session_string_encrypted)
    client = await telethon_client.create_client(decrypted_session)
    if not client:
        logger.error(f"Failed to create Telegram client for user {user_id}.")
        await websocket_service.send_user_notification(user_id, "vibe_profile_failed", {"error": "Failed to create Telegram client."})
        return

    try:
        await websocket_service.send_user_notification(user_id, "vibe_profile_analyzing", {})
        result = await analysis_service.analyze_user_context(client, user_id)
        
        if result.get("status") == "completed":
            await websocket_service.send_user_notification(user_id, "vibe_profile_completed", {"profile": result.get("vibe_profile")})
            logger.info(f"Successfully completed vibe profile analysis for user {user_id}.")
        else:
            await websocket_service.send_user_notification(user_id, "vibe_profile_failed", {"error": result.get("reason")})
            logger.error(f"Vibe profile analysis failed for user {user_id}: {result.get('reason')}")
    finally:
        await client.disconnect() 