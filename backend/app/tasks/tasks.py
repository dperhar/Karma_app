import asyncio
import json
import logging
import re
from typing import Any, Dict, Optional

from app.core.dependencies import container
from app.models.ai_profile import AnalysisStatus
from app.models.draft_comment import DraftStatus
from app.models.telegram_message import TelegramMessengerMessage
from app.repositories.ai_profile_repository import AIProfileRepository
from app.repositories.chat_repository import ChatRepository
from app.repositories.draft_comment_repository import DraftCommentRepository
from app.repositories.message_repository import \
    MessageRepository as TelegramMessageRepository
from app.repositories.negative_feedback_repository import \
    NegativeFeedbackRepository
from app.repositories.user_repository import UserRepository
from app.schemas.draft_comment import DraftCommentCreate
from app.services.domain.websocket_service import WebSocketService
from app.services.gemini_service import GeminiService
from app.services.telegram_service import TelegramService
from app.tasks.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.fetch_telegram_chats_task")
def fetch_telegram_chats_task(user_id: str, limit: int = 50, offset: int = 0):
    """
    Celery task to fetch user's Telegram chats.
    
    Following Principle 2: The Worker is the Intelligent, Stateful Engine.
    All Telegram API interactions must happen here in the Celery worker.
    """
    logger.info(f"Starting fetch chats task for user_id: {user_id}, limit: {limit}, offset: {offset}")
    asyncio.run(async_fetch_telegram_chats(user_id, limit, offset))


async def async_fetch_telegram_chats(user_id: str, limit: int, offset: int):
    """
    Async implementation of fetching Telegram chats.
    
    This task is self-contained and instantiates its own dependencies.
    """
    # GOOD: Task instantiates its own dependencies
    telegram_service = container.resolve(TelegramService)
    chat_repo = container.resolve(ChatRepository)
    websocket_service = container.resolve(WebSocketService)
    
    client = None
    try:
        # GOOD: All Telegram API interactions happen in the Celery worker
        client = await telegram_service.get_client(user_id)
        if not client:
            await websocket_service.send_user_notification(
                user_id, "chats_fetch_failed", {"error": "Failed to create Telegram client"}
            )
            return
            
        # Fetch chats from Telegram
        chats = await telegram_service.get_user_chats(user_id, limit=limit, offset=offset)
        
        # Store chats in database
        for chat_data in chats:
            await chat_repo.create_or_update_chat(
                user_id=user_id,
                chat_id=chat_data.get("id"),
                chat_type=chat_data.get("type"),
                title=chat_data.get("title"),
                username=chat_data.get("username"),
                participant_count=chat_data.get("participant_count")
            )
        
        # Notify frontend via WebSocket
        await websocket_service.send_user_notification(
            user_id, 
            "chats_fetch_completed", 
            {
                "chats_count": len(chats),
                "limit": limit,
                "offset": offset
            }
        )
        
        logger.info(f"Successfully fetched {len(chats)} chats for user {user_id}")
        
    except Exception as e:
        logger.error(f"Chat fetch for user {user_id} failed: {e}", exc_info=True)
        await websocket_service.send_user_notification(
            user_id, "chats_fetch_failed", {"error": str(e)}
        )
    finally:
        if client:
            await telegram_service.disconnect_client(user_id)


@celery_app.task(name="tasks.analyze_vibe_profile")
def analyze_vibe_profile(user_id: str):
    """Celery task to analyze a user's vibe profile asynchronously."""
    logger.info(f"Starting vibe profile analysis task for user_id: {user_id}")
    asyncio.run(async_analyze_vibe_profile(user_id))


async def async_analyze_vibe_profile(user_id: str):
    """The async implementation of the vibe profile analysis."""
    # Resolve dependencies from the container
    telegram_service = container.resolve(TelegramService)
    gemini_service = container.resolve(GeminiService)
    ai_profile_repo = container.resolve(AIProfileRepository)
    websocket_service = container.resolve(WebSocketService)

    await websocket_service.send_user_notification(
        user_id, "vibe_profile_analyzing", {}
    )

    client = None
    try:
        # Get user's telegram client
        client = await telegram_service.get_client(user_id)
        if not client:
            raise Exception("Failed to create Telegram client.")

        # Fetch user's sent messages
        user_sent_messages = await telegram_service.get_user_sent_messages(
            user_id, limit=200
        )
        if not user_sent_messages or len(user_sent_messages) < 20:
            raise Exception("Insufficient data for analysis.")

        # Use LLM to generate the vibe profile
        message_texts = [
            msg.get("text", "") for msg in user_sent_messages if msg.get("text")
        ]
        combined_text_sample = "\n".join(message_texts)[:15000]
        prompt = f"""
        Analyze the following collection of a user's sent Telegram messages to create a "Vibe Profile".
        The user wants to use this profile to generate comments that sound just like them.
        Based on the messages, determine the user's communication style.

        Return a single JSON object with the following keys:
        - "tone": (string) Describe the user's typical tone. Examples: "casual and friendly", "formal and professional", "sarcastic and witty", "enthusiastic and energetic", "direct and concise".
        - "verbosity": (string) Describe the user's typical message length. Examples: "brief" (short, to the point), "moderate" (a few sentences), "verbose" (detailed and long).
        - "emoji_usage": (string) Describe their emoji usage. Examples: "none", "light" (occasional), "heavy" (frequent).
        - "common_phrases": (array of strings) List up to 10 common phrases, slang, or recurring expressions the user uses.
        - "topics_of_interest": (array of strings) List up to 10 main topics or interests discussed in the messages.

        Here are the user's messages:
        ---
        {combined_text_sample}
        ---

        Respond ONLY with the JSON object. Do not include any other text or markdown formatting.
        """
        response = await gemini_service.generate_content(prompt)
        if not response or not response.get("success"):
            raise Exception("LLM analysis failed.")

        content = response.get("content", "")
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if not json_match:
            raise Exception("LLM did not return a valid JSON object.")

        vibe_profile = json.loads(json_match.group(0))

        # Save the profile
        ai_profile = await ai_profile_repo.get_ai_profile_by_user(user_id)
        if not ai_profile:
            ai_profile = await ai_profile_repo.create_ai_profile(user_id=user_id)

        await ai_profile_repo.mark_analysis_completed(
            profile_id=ai_profile.id,
            vibe_profile=vibe_profile,
            messages_count=len(user_sent_messages),
        )

        await websocket_service.send_user_notification(
            user_id, "vibe_profile_completed", {"profile": vibe_profile}
        )
        logger.info(f"Successfully completed vibe profile analysis for user {user_id}.")

    except Exception as e:
        logger.error(f"Vibe profile analysis for user {user_id} failed: {e}", exc_info=True)
        await websocket_service.send_user_notification(
            user_id, "vibe_profile_failed", {"error": str(e)}
        )
    finally:
        if client:
            await telegram_service.disconnect_client(user_id)


@celery_app.task(name="tasks.generate_draft_for_post")
def generate_draft_for_post(
    user_id: str,
    post_data: Dict[str, Any],
    rejected_draft_id: Optional[str] = None,
    rejection_reason: Optional[str] = None,
):
    """Celery task to generate a draft comment for a post."""
    logger.info(f"Starting draft generation task for user_id: {user_id}")
    asyncio.run(
        async_generate_draft_for_post(
            user_id, post_data, rejected_draft_id, rejection_reason
        )
    )


async def async_generate_draft_for_post(
    user_id: str,
    post_data: Dict[str, Any],
    rejected_draft_id: Optional[str] = None,
    rejection_reason: Optional[str] = None,
):
    """The async implementation of draft generation."""
    # Resolve dependencies
    user_repo = container.resolve(UserRepository)
    draft_repo = container.resolve(DraftCommentRepository)
    feedback_repo = container.resolve(NegativeFeedbackRepository)
    gemini_service = container.resolve(GeminiService)
    websocket_service = container.resolve(WebSocketService)

    try:
        user = await user_repo.get_user(user_id)
        if not user or not user.ai_profile or not user.ai_profile.vibe_profile_json:
            raise Exception("User or user's AI profile not found or incomplete.")

        # Handle regeneration case
        if rejected_draft_id:
            rejected_draft = await draft_repo.get_draft_comment(rejected_draft_id)
            if rejected_draft:
                await feedback_repo.create_negative_feedback(
                    user_id=user_id,
                    rejected_comment_text=rejected_draft.draft_text,
                    original_post_content=rejected_draft.original_post_content,
                    original_post_url=rejected_draft.original_post_url,
                    rejection_reason=rejection_reason,
                    ai_model_used=rejected_draft.ai_model_used,
                    draft_comment_id=rejected_draft_id,
                )
                await draft_repo.update_draft_comment(
                    rejected_draft_id, status=DraftStatus.REJECTED
                )

        # Check post relevance
        vibe_profile = user.ai_profile.vibe_profile_json
        topics_of_interest = vibe_profile.get("topics_of_interest", [])
        post_text = post_data.get("original_post_content", "").lower()
        is_relevant = any(topic.lower() in post_text for topic in topics_of_interest)
        if not topics_of_interest:
            is_relevant = True

        if not is_relevant:
            logger.info(f"Post not relevant for user {user_id}. Skipping draft generation.")
            return

        # Construct prompt
        negative_feedback = await feedback_repo.get_negative_feedback_by_user(
            user_id, limit=10
        )
        feedback_context = "\n".join(
            [
                f"- REJECTED: '{fb.rejected_comment_text}' because '{fb.rejection_reason}'"
                for fb in negative_feedback
            ]
        )

        prompt = f"""
        You are an AI assistant generating a Telegram comment for a user.
        USER VIBE PROFILE: {json.dumps(user.ai_profile.vibe_profile_json, indent=2)}
        POST TO COMMENT ON: {post_data.get('original_post_content')}
        
        USER'S PAST REJECTIONS (learn from these mistakes):
        {feedback_context if feedback_context else "None"}

        INSTRUCTIONS:
        1. Generate a comment that perfectly matches the user's vibe (tone, verbosity, emoji usage).
        2. The comment must be relevant to the post.
        3. Avoid making comments similar to the rejected ones.
        4. Generate ONLY the comment text.
        """

        # Generate comment
        response = await gemini_service.generate_content(prompt)
        if not response or not response.get("success"):
            raise Exception("LLM comment generation failed.")

        draft_text = response.get("content", "").strip()

        # Save draft
        draft_create_data = DraftCommentCreate(
            original_message_id=post_data.get("original_message_id", "unknown"),
            user_id=user_id,
            persona_name=user.ai_profile.persona_name,
            ai_model_used=user.preferred_ai_model.value
            if user.preferred_ai_model
            else "gemini-pro",
            original_post_text_preview=post_data.get("original_post_content", "")[:500],
            original_post_content=post_data.get("original_post_content"),
            original_post_url=post_data.get("original_post_url"),
            draft_text=draft_text,
        )
        new_draft = await draft_repo.create_draft_comment(
            **draft_create_data.model_dump()
        )

        # Notify user
        await websocket_service.send_user_notification(
            user_id, "new_ai_draft", {"draft": new_draft.model_dump(mode="json")}
        )
        logger.info(f"Successfully generated draft {new_draft.id} for user {user_id}.")

    except Exception as e:
        logger.error(f"Draft generation for user {user_id} failed: {e}", exc_info=True)
        await websocket_service.send_user_notification(
            user_id, "draft_generation_failed", {"error": str(e)}
        )


@celery_app.task(name="tasks.check_for_new_posts_and_generate_drafts")
def check_for_new_posts_and_generate_drafts():
    """Celery task to periodically check for new posts and generate drafts."""
    logger.info("Starting scheduled task: check_for_new_posts_and_generate_drafts")
    asyncio.run(async_check_for_new_posts())


async def async_check_for_new_posts():
    """The async implementation of the scheduled check."""
    user_repo = container.resolve(UserRepository)
    telegram_service = container.resolve(TelegramService)
    message_repo = container.resolve(TelegramMessageRepository)
    chat_repo = container.resolve(ChatRepository)

    active_users = await user_repo.get_users()
    for user in active_users:
        if not user.telegram_connection or not user.telegram_connection.is_session_valid():
            continue

        client = None
        try:
            client = await telegram_service.get_client(user.id)
            if not client:
                continue

            async for dialog in client.iter_dialogs(limit=20):
                if dialog.is_channel:
                    db_chat = await chat_repo.get_chat_by_telegram_id(dialog.id, user.id)
                    if not db_chat:
                        continue

                    async for message in client.iter_messages(dialog, limit=10):
                        # This is a simplified check. A real implementation would
                        # track last seen message IDs per channel.
                        db_messages = await message_repo.create_or_update_messages(
                            [
                                TelegramMessengerMessage(
                                    telegram_id=message.id,
                                    chat_id=db_chat.id,
                                    text=message.text,
                                    date=message.date,
                                )
                            ]
                        )
                        db_message_id = db_messages[0].id

                        post_data = {
                            "original_message_id": db_message_id,
                            "original_post_content": message.text,
                            "original_post_url": f"https://t.me/{dialog.entity.username}/{message.id}"
                            if hasattr(dialog.entity, "username")
                            and dialog.entity.username
                            else None,
                        }
                        generate_draft_for_post.delay(user_id=user.id, post_data=post_data)
        except Exception as e:
            logger.error(f"Failed to process user {user.id} in scheduled task: {e}")
        finally:
            if client:
                await telegram_service.disconnect_client(user.id) 