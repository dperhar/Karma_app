"""Service for AI-powered comment generation and management."""

import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

from app.models.draft_comment import DraftComment, DraftStatus
from app.models.ai_request import AIRequestModel
from app.models.user import User
from app.schemas.draft_comment import DraftCommentCreate, DraftCommentUpdate, DraftCommentResponse
from app.services.base_service import BaseService
from app.services.gemini_service import GeminiService
from app.services.langchain_service import LangChainService
from app.services.telegram_service import TelegramService
from app.services.redis_service import RedisService
from app.repositories.draft_comment_repository import DraftCommentRepository
from app.repositories.user_repository import UserRepository
from app.services.domain.websocket_service import WebSocketService


class KarmaService(BaseService):
    """Service for AI comment generation and management."""

    def __init__(
        self,
        draft_comment_repository: DraftCommentRepository,
        user_repository: UserRepository,
        gemini_service: GeminiService,
        langchain_service: LangChainService,
        telegram_service: TelegramService,
        websocket_service: WebSocketService,
    ):
        super().__init__()
        self.draft_comment_repository = draft_comment_repository
        self.user_repository = user_repository
        self.gemini_service = gemini_service
        self.langchain_service = langchain_service
        self.telegram_service = telegram_service
        self.websocket_service = websocket_service
        self.redis_service = RedisService()

    async def generate_draft_comment(
        self,
        original_message_id: str,
        user_id: str,
        post_data: Dict[str, Any],
        context_data: Optional[Dict[str, Any]] = None
    ) -> Optional[DraftCommentResponse]:
        """Generate AI draft comment for a post.
        
        Args:
            original_message_id: ID of the original message/post
            user_id: User ID
            post_data: Dictionary with post content and metadata
            context_data: Optional context (chat info, recent messages, etc.)
            
        Returns:
            DraftCommentResponse or None if generation failed
        """
        try:
            # Get user and persona data
            user = await self.user_repository.get_user(user_id)
            if not user:
                self.logger.error(f"User not found: {user_id}")
                return None

            # Resolve model to use, but do not persist enum to avoid DB enum mismatch in dev
            try:
                preferred_value = str(getattr(getattr(user, "preferred_ai_model", None), "value", "") or "")
            except Exception:
                preferred_value = ""

            # Respect force_generate flag (feed-page or regeneration)
            if not post_data.get("force_generate"):
                # Check if post is relevant to persona interests
                if not self._is_post_relevant(post_data, user):
                    self.logger.info(f"Post not relevant to persona interests: {post_data.get('text', '')[:100]}")
                    return None

            # Generate AI comment
            draft_text, context_summary = await self._generate_ai_comment(post_data, user, context_data)
            if not draft_text:
                self.logger.error("Failed to generate AI comment")
                return None
            # Final guard to remove generic openers (defensive)
            try:
                from app.tasks.tasks import _strip_generic_openers
                dom_lang = "ru"
                try:
                    dom_lang = (getattr(user, "ai_profile", None).vibe_profile_json or {}).get("dominant_language", "ru")
                except Exception:
                    pass
                draft_text = _strip_generic_openers(
                    draft_text,
                    original_post=post_data.get("text") or post_data.get("original_post_content"),
                    lang=dom_lang,
                )
            except Exception:
                pass

            # Create draft comment
            # Resolve model used string for record; force-align to Gemini 2.5 Pro if user pref missing
            model_used = str(getattr(getattr(user, "preferred_ai_model", None), "value", "") or "")
            if not model_used or "gemini" not in model_used.lower():
                model_used = "gemini-2.5-pro"

            draft_data = DraftCommentCreate(
                original_message_id=original_message_id,
                user_id=user.id,
                status="draft",
                ai_model_used=model_used,
                original_post_text_preview=post_data.get('text', '')[:500],
                draft_text=draft_text,
                ai_context_summary=context_summary,
                generation_params={
                    "model": model_used,
                    "persona_name": user.persona_name,
                    "post_channel": post_data.get('channel', {}).get('title', 'Unknown'),
                    "channel_telegram_id": post_data.get('channel_telegram_id'),
                    "original_message_telegram_id": post_data.get('original_message_telegram_id'),
                    "generated_at": datetime.now().isoformat()
                }
            )

            draft = await self.draft_comment_repository.create_draft_comment(**draft_data.model_dump())
            if not draft:
                return None

            response = DraftCommentResponse.model_validate(draft)

            # Send WebSocket notification
            await self._send_draft_notification(user_id, "new_ai_draft", response.model_dump(mode='json'))

            self.logger.info(f"Generated draft comment {response.id} for user {user_id}")
            return response

        except Exception as e:
            self.logger.error(f"Error generating draft comment: {e}", exc_info=True)
            return None

    async def update_draft_comment(
        self,
        draft_id: str,
        update_data: DraftCommentUpdate
    ) -> Optional[DraftCommentResponse]:
        """Update a draft comment."""
        try:
            draft = await self.draft_comment_repository.update_draft_comment(
                draft_id, **update_data.model_dump(exclude_unset=True)
            )
            if not draft:
                return None

            response = DraftCommentResponse.model_validate(draft)
            
            # Send WebSocket notification
            await self._send_draft_notification(draft.user_id, "draft_update", response.model_dump(mode='json'))
            
            return response

        except Exception as e:
            self.logger.error(f"Error updating draft comment: {e}", exc_info=True)
            return None

    async def approve_draft_comment(self, draft_id: str) -> Optional[DraftCommentResponse]:
        """Approve a draft comment for posting."""
        return await self.update_draft_comment(
            draft_id, 
            DraftCommentUpdate(status=DraftStatus.APPROVED)
        )

    async def post_draft_comment(
        self,
        draft_id: str,
        user_id: str,
    ) -> Optional[DraftCommentResponse]:
        """Post a draft comment to Telegram and update its status.

        Args:
            draft_id: Draft identifier
            user_id: Owner user id (used for Telegram client)

        Returns:
            Updated DraftCommentResponse if posted, otherwise None
        """
        try:
            draft = await self.draft_comment_repository.get_draft_comment(draft_id)
            if not draft:
                self.logger.error(f"Draft comment not found: {draft_id}")
                return None

            # We allow posting directly from DRAFT/APPROVED states via single "Send" action

            # Attempt to post comment via TelegramService using stored generation params
            text_to_post = draft.final_text_to_post or draft.edited_text or draft.draft_text
            channel_id = None
            post_id = None
            try:
                # generation_params may include channel_telegram_id captured at generation time
                gp = draft.generation_params or {}
                channel_id = gp.get("channel_telegram_id")
                # Prefer explicit Telegram message id if present
                post_id = gp.get("post_telegram_id") or gp.get("original_message_telegram_id")
            except Exception:
                pass

            # Fallback: resolve missing ids from DB relations (original_message -> chat)
            if not channel_id or not post_id:
                try:
                    from app.core.dependencies import container as _container
                    from app.repositories.message_repository import MessageRepository as _MsgRepo
                    from app.repositories.chat_repository import ChatRepository as _ChatRepo

                    msg_repo = _container.resolve(_MsgRepo)
                    chat_repo = _container.resolve(_ChatRepo)

                    msg = None
                    try:
                        if getattr(draft, "original_message_id", None):
                            msg = await msg_repo.get_message(str(draft.original_message_id))
                    except Exception:
                        msg = None

                    # Recover post telegram id from message row
                    if msg and not post_id:
                        try:
                            post_id = int(getattr(msg, "telegram_id", 0) or 0) or None
                        except Exception:
                            post_id = None

                    # Recover channel telegram id from chat row
                    if msg and not channel_id:
                        try:
                            chat = await chat_repo.get_chat(str(getattr(msg, "chat_id", "")))
                            if chat:
                                channel_id = int(getattr(chat, "telegram_id", 0) or 0) or None
                        except Exception:
                            channel_id = None

                    # Persist recovered ids for next time
                    if channel_id or post_id:
                        try:
                            gp2 = dict(gp) if isinstance(gp, dict) else {}
                            if channel_id:
                                gp2["channel_telegram_id"] = int(channel_id)
                            if post_id:
                                gp2["post_telegram_id"] = int(post_id)
                            await self.draft_comment_repository.update_draft_comment(
                                draft_id,
                                generation_params=gp2 or None,
                            )
                            gp = gp2
                        except Exception:
                            pass
                except Exception:
                    # Ignore fallback errors and proceed with whatever we have
                    pass

            result = {"success": False, "error": "missing ids"}
            if channel_id and post_id:
                result = await self.telegram_service.post_comment_to_telegram(
                    user_id=user_id,
                    channel_telegram_id=int(channel_id),
                    post_telegram_id=int(post_id),
                    comment_text=text_to_post,
                )
            elif getattr(draft, "original_post_url", None):
                # Fallback: try URL-based posting if we have a t.me link
                result = await self.telegram_service.post_comment_by_url(
                    user_id=user_id,
                    post_url=str(draft.original_post_url),
                    comment_text=text_to_post,
                )
                # If successful, persist recovered ids into generation_params for future posts
                if result.get("success"):
                    try:
                        gp2 = dict(gp) if isinstance(gp, dict) else {}
                        if result.get("channel_id") and not gp2.get("channel_telegram_id"):
                            gp2["channel_telegram_id"] = int(result["channel_id"])  # type: ignore[arg-type]
                        await self.draft_comment_repository.update_draft_comment(
                            draft_id,
                            generation_params=gp2 or None,
                        )
                    except Exception:
                        pass

            if result.get('success'):
                # Update draft status and mark as a style example to enrich the user's profile
                try:
                    base_params = dict(draft.generation_params or {})
                except Exception:
                    base_params = {}
                base_params["is_style_example"] = True
                base_params["last_posted_at"] = datetime.now().isoformat()

                updated_draft = await self.draft_comment_repository.update_draft_comment(
                    draft_id,
                    status=DraftStatus.POSTED,
                    posted_telegram_message_id=result.get('message_id'),
                    final_text_to_post=text_to_post,
                    generation_params=base_params or None,
                )
                
                if updated_draft:
                    response = DraftCommentResponse.model_validate(updated_draft)
                    await self._send_draft_notification(draft.user_id, "draft_update", response.model_dump(mode='json'))
                    return response
            else:
                # Update with failure
                await self.draft_comment_repository.update_draft_comment(
                    draft_id,
                    status=DraftStatus.FAILED_TO_POST,
                    failure_reason=result.get('error', 'Unknown error')
                )

            return None

        except Exception as e:
            self.logger.error(f"Error posting draft comment: {e}", exc_info=True)
            # Update with failure
            await self.draft_comment_repository.update_draft_comment(
                draft_id,
                status=DraftStatus.FAILED_TO_POST,
                failure_reason=str(e)
            )
            return None

    async def get_drafts_by_user(
        self, 
        user_id: str, 
        status: Optional[DraftStatus] = None
    ) -> List[DraftCommentResponse]:
        """Get draft comments for a user."""
        try:
            drafts = await self.draft_comment_repository.get_drafts_by_user(user_id, status)
            return [DraftCommentResponse.model_validate(draft) for draft in drafts]
        except Exception as e:
            self.logger.error(f"Error getting drafts for user {user_id}: {e}", exc_info=True)
            return []

    async def regenerate_draft_with_feedback(
        self,
        draft_id: str,
        regenerate_request: Any  # RegenerateRequest
    ) -> Optional[DraftCommentResponse]:
        """Regenerate a draft comment incorporating negative feedback (Not My Vibe)."""
        try:
            # Get the original draft
            draft = await self.draft_comment_repository.get_draft_comment(draft_id)
            if not draft:
                self.logger.error(f"Draft comment not found: {draft_id}")
                return None

            # Save negative feedback
            await self._save_negative_feedback(draft, regenerate_request)

            # Get user and context
            user = await self.user_repository.get_user(draft.user_id)
            if not user:
                self.logger.error(f"User not found: {draft.user_id}")
                return None

            # Reconstruct post data from draft
            post_data = {
                'text': draft.original_post_content or draft.original_post_text_preview,
                'url': draft.original_post_url,
                'channel': {'title': 'Unknown'}  # Would need to be stored/retrieved
            }

            # Get negative feedback context for this user
            negative_feedback_context = await self._get_negative_feedback_context(draft.user_id)

            # Generate new AI comment with negative feedback incorporated
            new_draft_text = await self._generate_ai_comment_with_feedback(
                post_data, 
                user, 
                negative_feedback_context,
                regenerate_request
            )

            if not new_draft_text:
                self.logger.error("Failed to regenerate AI comment")
                return None

            # Update the draft with new text
            updated_draft = await self.draft_comment_repository.update_draft_comment(
                draft_id,
                draft_text=new_draft_text,
                status=DraftStatus.DRAFT,  # Reset to draft status
                generation_params={
                    **draft.generation_params,
                    "regenerated_at": datetime.now().isoformat(),
                    "negative_feedback_incorporated": True,
                    "rejection_reason": regenerate_request.rejection_reason
                }
            )

            if not updated_draft:
                return None

            response = DraftCommentResponse.model_validate(updated_draft)

            # Send WebSocket notification
            await self._send_draft_notification(
                draft.user_id, 
                "draft_regenerated", 
                response.model_dump(mode='json')
            )

            self.logger.info(f"Regenerated draft comment {draft_id} for user {draft.user_id}")
            return response

        except Exception as e:
            self.logger.error(f"Error regenerating draft comment: {e}", exc_info=True)
            return None

    async def _save_negative_feedback(self, draft: Any, regenerate_request: Any):
        """Save negative feedback to improve future generations."""
        try:
            from app.repositories.negative_feedback_repository import NegativeFeedbackRepository
            from app.services.dependencies import container
            
            feedback_repo = container.resolve(NegativeFeedbackRepository)
            
            await feedback_repo.create_negative_feedback(
                user_id=draft.user_id,
                rejected_comment_text=draft.draft_text,
                original_post_content=draft.original_post_content,
                original_post_url=draft.original_post_url,
                rejection_reason=regenerate_request.rejection_reason,
                ai_model_used=draft.ai_model_used,
                draft_comment_id=draft.id
            )
            
            self.logger.info(f"Saved negative feedback for draft {draft.id}")
            
        except Exception as e:
            self.logger.error(f"Error saving negative feedback: {e}", exc_info=True)

    async def _get_negative_feedback_context(self, user_id: str) -> List[Dict[str, Any]]:
        """Get negative feedback context for improving AI generation."""
        try:
            from app.repositories.negative_feedback_repository import NegativeFeedbackRepository
            from app.services.dependencies import container
            
            feedback_repo = container.resolve(NegativeFeedbackRepository)
            
            # Get recent negative feedback (last 10-20 examples)
            negative_feedback = await feedback_repo.get_negative_feedback_by_user(
                user_id, 
                limit=20
            )
            
            return [
                {
                    "rejected_comment": fb.rejected_comment_text,
                    "original_post": fb.original_post_content,
                    "reason": fb.rejection_reason
                }
                for fb in negative_feedback
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting negative feedback context: {e}", exc_info=True)
            return []

    async def _generate_ai_comment_with_feedback(
        self,
        post_data: Dict[str, Any],
        user: User,
        negative_feedback_context: List[Dict[str, Any]],
        regenerate_request: Any
    ) -> Optional[str]:
        """Generate AI comment incorporating negative feedback."""
        try:
            # Construct enhanced prompt with negative feedback
            prompt = self._construct_prompt_with_feedback(
                post_data, 
                user, 
                negative_feedback_context,
                regenerate_request
            )

            # Use preferred AI model
            if user.preferred_ai_model == AIRequestModel.GEMINI_2_5_PRO:
                result = await self.gemini_service.generate_text(prompt)
                return result.get('text') if result.get('success') else None
            else:
                # Fallback or other models
                result = await self.langchain_service.generate_response(prompt)
                return result.get('content') if result.get('success') else None

        except Exception as e:
            self.logger.error(f"Error generating AI comment with feedback: {e}", exc_info=True)
            return None

    def _construct_prompt_with_feedback(
        self,
        post_data: Dict[str, Any],
        user: User,
        negative_feedback_context: List[Dict[str, Any]],
        regenerate_request: Any
    ) -> str:
        """Construct AI prompt incorporating negative feedback."""
        base_prompt = self._construct_prompt(post_data, user)
        
        # Add negative feedback section
        if negative_feedback_context:
            feedback_section = "\n\n## IMPORTANT: Learn from Previous Rejections\n"
            feedback_section += "The user has rejected these types of responses in the past. DO NOT generate similar content:\n\n"
            
            for i, feedback in enumerate(negative_feedback_context[:10], 1):
                feedback_section += f"### Rejection Example {i}:\n"
                feedback_section += f"Original Post: {feedback['original_post'][:200]}...\n"
                feedback_section += f"REJECTED Response: {feedback['rejected_comment']}\n"
                if feedback['reason']:
                    feedback_section += f"Rejection Reason: {feedback['reason']}\n"
                feedback_section += "\n"
            
            feedback_section += "Based on these rejections, avoid similar tone, style, or approach.\n"
            base_prompt += feedback_section

        # Add specific regeneration instructions
        if regenerate_request.rejection_reason:
            base_prompt += f"\n\n## Specific Issue to Fix:\n{regenerate_request.rejection_reason}\n"
        
        if regenerate_request.custom_instructions:
            base_prompt += f"\n\n## Additional Instructions:\n{regenerate_request.custom_instructions}\n"

        base_prompt += "\n\nGenerate a NEW comment that addresses the feedback above and avoids the rejected patterns."
        
        return base_prompt

    def _is_post_relevant(self, post_data: Dict[str, Any], user: User) -> bool:
        """Check if post is relevant to user's vibe profile interests."""
        try:
            # Get post content
            post_text = post_data.get('text', '').lower()
            if not post_text or len(post_text) < 10:
                return False

            # Get user's AI profile
            if not user.ai_profile:
                self.logger.warning(f"User {user.id} has no AI profile for relevance check")
                # For users without AI profile, accept all posts (they need to build their profile)
                return True

            vibe_profile = user.ai_profile.vibe_profile_json
            if not vibe_profile:
                self.logger.warning(f"User {user.id} has AI profile but no vibe profile data")
                return True

            # Get topics of interest from vibe profile
            topics_of_interest = vibe_profile.get('topics_of_interest', [])
            if not topics_of_interest:
                # If no specific topics, accept the post (let user decide)
                return True

            # Check if post content matches any of the user's interests
            for topic in topics_of_interest:
                if topic.lower() in post_text:
                    self.logger.info(f"Post relevant to user {user.id}: matches topic '{topic}'")
                    return True

            # Check for keyword overlap (more sophisticated matching)
            post_keywords = set(post_text.split())
            interest_keywords = set()
            for topic in topics_of_interest:
                interest_keywords.update(topic.lower().split())

            # If there's some overlap, consider it relevant
            overlap = post_keywords.intersection(interest_keywords)
            if len(overlap) >= 2:  # At least 2 matching keywords
                self.logger.info(f"Post relevant to user {user.id}: keyword overlap {overlap}")
                return True

            # If channel is in user's preferred topics, consider it relevant
            channel_name = post_data.get('channel', {}).get('title', '').lower()
            for topic in topics_of_interest:
                if topic.lower() in channel_name:
                    self.logger.info(f"Post relevant to user {user.id}: channel '{channel_name}' matches topic '{topic}'")
                    return True

            self.logger.debug(f"Post not relevant to user {user.id} interests: {topics_of_interest}")
            return False

        except Exception as e:
            self.logger.error(f"Error checking post relevance: {e}", exc_info=True)
            # On error, default to accepting the post
            return True

    async def _generate_ai_comment(
        self,
        post_data: Dict[str, Any],
        user: User,
        context_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """Generate AI comment using configured AI service."""
        try:
            prompt = self._construct_prompt(post_data, user, context_data)
            
            # Use preferred AI model
            if user.preferred_ai_model and "gemini" in str(user.preferred_ai_model.value).lower():
                response = await self.gemini_service.generate_content(prompt)
                if response and response.get('content'):
                    try:
                        content_json = json.loads(response.get('content'))
                        draft_text = content_json.get('comment_text')
                        context_summary = content_json.get('context_summary')
                        return draft_text, context_summary
                    except (json.JSONDecodeError, TypeError):
                        # Strip code fences then retry
                        content = (response.get('content') or '').strip()
                        if content.startswith('```'):
                            fence_end = content.rfind('```')
                            if fence_end != -1:
                                content = content.split('\n', 1)[-1][:fence_end].strip()
                        try:
                            content_json = json.loads(content)
                            return content_json.get('comment_text'), content_json.get('context_summary')
                        except Exception:
                            # Fall through to rescue generation
                            pass

                # Rescue path: request plain text comment using style markers; avoid generic fillers
                try:
                    vp = (getattr(user, 'ai_profile', None).vibe_profile_json
                          if getattr(user, 'ai_profile', None) else {})
                    tone = vp.get('tone', 'по делу, лаконично')
                    endings = (vp.get('digital_comm', {}) or {}).get('typical_endings', [])
                    sig_phrases = [p.get('text') for p in (vp.get('signature_phrases') or []) if isinstance(p, dict) and p.get('text')]
                    top_bigrams = (vp.get('ngrams', {}) or {}).get('bigrams', [])
                    ban_starters = [
                        'Погнали', 'Давай сделаем', 'Подписываюсь на апдейт',
                        'Интересно,', 'Прикольно,', 'Ммм,'
                    ]
                    style_hint = f"Тон: {tone}. Избегай шаблонных фраз: {', '.join(ban_starters[:5])}. "
                    if endings:
                        style_hint += f"Предпочтительное окончание: {' / '.join(endings[:2])}. "
                    if sig_phrases:
                        style_hint += f"Можно использовать максимум 1 фирменную фразу, если органично: {', '.join(sig_phrases[:3])}. "
                    if top_bigrams:
                        style_hint += f"Характерные биграммы: {', '.join(top_bigrams[:3])}. "

                    rescue_prompt = (
                        "Сгенерируй короткий комментарий по-русски в моём стиле, конкретно к этому посту. "
                        "Без воды, без общих слов. Одна строка, без кавычек и без markdown.\n\n"
                        f"{style_hint}\n\nТЕКСТ ПОСТА:\n{post_data.get('text') or post_data.get('original_post_content') or ''}"
                    )
                    rescue_resp = await self.gemini_service.generate_text(rescue_prompt)
                    if rescue_resp and rescue_resp.get('success'):
                        text = (rescue_resp.get('text') or '').strip()
                        # Basic anti-duplication on starters
                        if any(text.startswith(s) for s in ban_starters):
                            rescue_prompt += "\n\nНе используй эти начала: " + ", ".join(ban_starters)
                            rescue_resp2 = await self.gemini_service.generate_text(rescue_prompt)
                            text = (rescue_resp2.get('text') or text).strip()
                        return text, None
                except Exception:
                    pass
                    
            # For testing/demo purposes, generate a mock response based on persona
            persona_name = user.persona_name or "Default User"
            if persona_name == "Mark Zuckerberg":
                mock_comments = [
                    "This is a great step forward for connecting people. The metaverse will enable even richer experiences.",
                    "Fascinating technology. I'm excited to see how this evolves and what it means for the future of social interaction.",
                    f"This kind of technological advancement is what makes me optimistic about building the metaverse. The future of computing is spatial."
                ]
                import random
                return random.choice(mock_comments), "This post is about the future of technology and the metaverse."
            else:
                # Generic minimal fallback
                return "Коротко и по делу.", ""

        except Exception as e:
            self.logger.error(f"Error generating AI comment: {e}", exc_info=True)
            return None, None

    def _construct_prompt(
        self,
        post_data: Dict[str, Any],
        user: User,
        context_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Construct AI prompt using user's vibe profile."""
        # Base system context
        prompt = "You are an AI assistant helping to generate authentic social media comments.\n"
        
        # Add vibe profile context if available
        if user.ai_profile and user.ai_profile.vibe_profile_json:
            vibe_profile = user.ai_profile.vibe_profile_json
            
            prompt += "## User Vibe Profile\n"
            prompt += f"Tone: {vibe_profile.get('tone', 'neutral')}\n"
            prompt += f"Verbosity: {vibe_profile.get('verbosity', 'moderate')}\n"
            prompt += f"Emoji Usage: {vibe_profile.get('emoji_usage', 'light')}\n"
            
            topics = vibe_profile.get('topics_of_interest', [])
            if topics:
                prompt += f"Topics of Interest: {', '.join(topics[:5])}\n"
                
            phrases = vibe_profile.get('common_phrases', [])
            if phrases:
                prompt += f"Common Phrases: {', '.join(phrases[:3])}\n"
                
            # Communication patterns
            comm_patterns = vibe_profile.get('communication_patterns', {})
            if comm_patterns:
                avg_length = comm_patterns.get('avg_message_length', 50)
                formality = comm_patterns.get('formality_score', 0.5)
                prompt += f"Typical message length: {int(avg_length)} characters\n"
                prompt += f"Formality level: {'formal' if formality > 0.7 else 'casual' if formality < 0.3 else 'balanced'}\n"
        else:
            # Fallback to basic persona if no vibe profile
            prompt += f"## User Persona\n"
            prompt += f"Name: {user.persona_name or 'Default User'}\n"
            if user.persona_style_description:
                prompt += f"Style: {user.persona_style_description}\n"

        # Add post context (prefer full original content if provided)
        prompt += f"\n## Post to Comment On\n"
        post_text = (
            post_data.get('original_post_content')
            or post_data.get('text')
            or post_data.get('original_post_text_preview')
            or ''
        )
        prompt += f"Post: {post_text}\n"
        
        if post_data.get('channel'):
            channel_info = post_data['channel']
            prompt += f"Channel: {channel_info.get('title', 'Unknown')}\n"
            
        # Add any additional context
        if context_data:
            prompt += f"\n## Additional Context\n"
            if context_data.get('recent_messages'):
                # Expand to richer channel context but cap total size
                prompt += "Recent channel activity (most recent first):\n"
                lines = []
                for msg in list(context_data['recent_messages'])[-12:][::-1]:
                    t = (msg.get('text', '') or '')
                    if not t:
                        continue
                    lines.append(f"- {t[:180]}")
                # Cap to ~1500 tokens ≈ ~6000 chars
                channel_blob = "\n".join(lines)
                if len(channel_blob) > 6000:
                    channel_blob = channel_blob[-6000:]
                prompt += channel_blob + "\n"

        # Post-specific anchors (force non-generic linkage)
        import re as _re_local
        anchors: list[str] = []
        try:
            numbers = list(set(_re_local.findall(r"\b\d+[\d\s.,]*\b", post_text)))[:3]
            urls = list(set(_re_local.findall(r"https?://\S+", post_text)))[:2]
            mentions = list(set(_re_local.findall(r"@[A-Za-z0-9_]+", post_text)))[:3]
            # Key tokens (3-20 chars, letters only), frequency-based sample
            toks = [t.lower() for t in _re_local.findall(r"[A-Za-zА-Яа-яЁё]{3,20}", post_text)]
            from collections import Counter as _Ctr
            common = [w for w, _ in _Ctr(toks).most_common(10) if w not in {"это","такой","также","очень","просто","снова","себя","если"}]
            anchors = numbers + urls + mentions + common[:5]
        except Exception:
            anchors = []
        if anchors:
            prompt += f"\nAnchors from post (use at least one naturally): {', '.join(anchors[:6])}\n"

        # Instructions
        prompt += "\n## Instructions\n"
        # Style guardrails from vibe profile
        sig_phrases = []
        endings = []
        if user.ai_profile and user.ai_profile.vibe_profile_json:
            vp = user.ai_profile.vibe_profile_json
            try:
                sig_phrases = [p.get('text') for p in (vp.get('signature_phrases') or []) if isinstance(p, dict) and p.get('text')]
            except Exception:
                sig_phrases = []
            try:
                # Respect user preference: no greetings/farewells used anywhere
                dc = (vp.get('digital_comm') or {})
                endings = dc.get('typical_endings') or []
                if 'greetings' in dc:
                    dc.pop('greetings', None)
                if 'farewells' in dc:
                    dc.pop('farewells', None)
            except Exception:
                endings = []

        lang_pref = 'ru' if (user.ai_profile and (user.ai_profile.vibe_profile_json or {}).get('language_distribution', {}).get('ru_cyrillic', 0) > 0.5) else 'en'

        prompt += (
            "Write a single short comment that matches the user's vibe and is specific to THIS post. "
            "Avoid generic fillers. Use the user's signature phrasing sparingly (only if natural). "
            "Prefer the user's typical ending if provided. Keep it concise.\n"
        )
        if sig_phrases:
            prompt += f"Potential signature phrases (use at most 1 and only if natural): {', '.join(sig_phrases[:5])}\n"
        if endings:
            prompt += f"Preferred endings: {', '.join(endings[:2])}\n"
        if lang_pref == 'ru':
            prompt += "Language: respond in Russian.\n"

        # Anti-generic constraints
        ban_starters = [
            'Погнали', 'Давай сделаем', 'Подписываюсь на апдейт', 'Интересно,',
            'Прикольно,', 'Ммм,', 'Круто.'
        ]
        prompt += "Avoid generic openings: " + ", ".join(ban_starters) + "\n"
        prompt += "Keep length close to my average sentence length; prefer a single sentence.\n"

        prompt += "Respond ONLY with a valid JSON object with two keys:\n"
        prompt += '1. "comment_text": string — the final comment text.\n'
        prompt += '2. "context_summary": string — one-sentence neutral summary of the post.\n\n'
        prompt += "No code fences, no markdown.\n\n"
        prompt += "Example Response Format:\n"
        prompt += '{\n  "comment_text": "Коротко по делу — классная мысль про фокус.",\n  "context_summary": "Пост о личном опыте и выводах из него."\n}'
        
        if user.ai_profile and user.ai_profile.vibe_profile_json:
            vibe_profile = user.ai_profile.vibe_profile_json
            tone = vibe_profile.get('tone', 'neutral')
            verbosity = vibe_profile.get('verbosity', 'moderate')
            emoji_usage = vibe_profile.get('emoji_usage', 'light')
            
            prompt += f"\nEnsure the 'comment_text' reflects these style guides: Tone: {tone}. Verbosity: {verbosity}. Emoji Usage: {emoji_usage}."

        prompt += "\n\nBegin JSON response now:"
        
        return prompt

    async def _send_draft_notification(self, user_id: str, event: str, data: Dict[str, Any]):
        """Send WebSocket notification about draft changes."""
        try:
            await self.websocket_service.send_user_notification(
                user_id=user_id,
                event=event,
                data=data
            )
        except Exception as e:
            self.logger.error(f"Error sending draft notification: {e}")
            # Don't raise the exception to prevent breaking the main flow 