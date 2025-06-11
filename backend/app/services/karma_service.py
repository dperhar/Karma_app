"""Service for AI-powered comment generation and management."""

import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from app.models.draft_comment import DraftComment, DraftStatus
from app.models.ai_request import AIRequestModel
from app.models.user import User
from app.schemas.draft_comment import DraftCommentCreate, DraftCommentUpdate, DraftCommentResponse
from app.services.base_service import BaseService
from app.services.gemini_service import GeminiService
from app.services.langchain_service import LangChainService
from app.services.telethon_service import TelethonService
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
        telethon_service: TelethonService,
        websocket_service: WebSocketService,
    ):
        super().__init__()
        self.draft_comment_repository = draft_comment_repository
        self.user_repository = user_repository
        self.gemini_service = gemini_service
        self.langchain_service = langchain_service
        self.telethon_service = telethon_service
        self.websocket_service = websocket_service

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

            # Check if post is relevant to persona interests
            if not self._is_post_relevant(post_data, user):
                self.logger.info(f"Post not relevant to persona interests: {post_data.get('text', '')[:100]}")
                return None

            # Generate AI comment
            draft_text = await self._generate_ai_comment(post_data, user, context_data)
            if not draft_text:
                self.logger.error("Failed to generate AI comment")
                return None

            # Create draft comment
            draft_data = DraftCommentCreate(
                original_message_id=original_message_id,
                user_id=user_id,
                persona_name=user.ai_profile.persona_name if user.ai_profile else "Default User",
                ai_model_used=str(user.preferred_ai_model.value) if user.preferred_ai_model else "gemini-pro",
                original_post_text_preview=post_data.get('text', '')[:500],
                draft_text=draft_text,
                generation_params={
                    "model": str(user.preferred_ai_model.value) if user.preferred_ai_model else "gemini-pro",
                    "persona_name": user.persona_name,
                    "post_channel": post_data.get('channel', {}).get('title', 'Unknown'),
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
        client: Any  # TelegramClient
    ) -> Optional[DraftCommentResponse]:
        """Post an approved draft comment to Telegram."""
        try:
            draft = await self.draft_comment_repository.get_draft_comment(draft_id)
            if not draft:
                self.logger.error(f"Draft comment not found: {draft_id}")
                return None

            if draft.status != DraftStatus.APPROVED:
                self.logger.error(f"Draft comment not approved: {draft_id}")
                return None

            # Extract channel and post IDs from original message
            # This would need to be stored in the message model or passed separately
            # For now, we'll assume the original_message has this info
            
            text_to_post = draft.final_text_to_post or draft.edited_text or draft.draft_text
            
            # Post comment via Telethon
            # Note: This is a simplified implementation
            # Real implementation would need proper channel/post ID extraction
            result = await self.telethon_service.post_comment_to_telegram(
                client=client,
                channel_telegram_id=0,  # Would need proper extraction
                post_telegram_id=0,     # Would need proper extraction
                comment_text=text_to_post
            )

            if result.get('success'):
                # Update draft status
                updated_draft = await self.draft_comment_repository.update_draft_comment(
                    draft_id,
                    status=DraftStatus.POSTED,
                    posted_telegram_message_id=result.get('message_id'),
                    final_text_to_post=text_to_post
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
            if user.preferred_ai_model == AIRequestModel.GEMINI_PRO:
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
    ) -> Optional[str]:
        """Generate AI comment using configured AI service."""
        try:
            prompt = self._construct_prompt(post_data, user, context_data)
            
            # Use preferred AI model
            if user.preferred_ai_model and "gemini" in str(user.preferred_ai_model.value).lower():
                response = await self.gemini_service.generate_content(prompt)
                if response and response.get('content'):
                    return response.get('content', '')
                    
            # For testing/demo purposes, generate a mock response based on persona
            persona_name = user.persona_name or "Default User"
            post_text = post_data.get('text', '')[:100]
            
            # Mock AI response that matches the persona style
            if persona_name == "Mark Zuckerberg":
                mock_comments = [
                    f"This is exactly the kind of innovation that will shape the future of human connection. The convergence of AR/VR technologies is bringing us closer to the metaverse vision.",
                    f"Spatial computing represents a fundamental shift in how we'll interact with digital experiences. This is the foundation for the next computing platform.",
                    f"Really exciting to see this progress! These advances in immersive technology will unlock new ways for people to connect and collaborate.",
                    f"The AR/VR space is moving incredibly fast. Each breakthrough like this brings us closer to seamless digital-physical integration.",
                    f"This kind of technological advancement is what makes me optimistic about building the metaverse. The future of computing is spatial."
                ]
                import random
                return random.choice(mock_comments)
            else:
                # Generic tech-savvy comment for other personas
                return f"Interesting development! The technology landscape is evolving rapidly."

        except Exception as e:
            self.logger.error(f"Error generating AI comment: {e}", exc_info=True)
            return None

    def _construct_prompt(
        self,
        post_data: Dict[str, Any],
        user: User,
        context_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Construct AI prompt using user's vibe profile."""
        # Base system context
        prompt = "You are an AI assistant helping to generate authentic social media comments.\n\n"
        
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

        # Add post context
        prompt += f"\n## Post to Comment On\n"
        post_text = post_data.get('text', '')
        prompt += f"Post: {post_text}\n"
        
        if post_data.get('channel'):
            channel_info = post_data['channel']
            prompt += f"Channel: {channel_info.get('title', 'Unknown')}\n"
            
        # Add any additional context
        if context_data:
            prompt += f"\n## Additional Context\n"
            if context_data.get('recent_messages'):
                prompt += "Recent channel activity:\n"
                for msg in context_data['recent_messages'][-3:]:  # Last 3 messages
                    prompt += f"- {msg.get('text', '')[:100]}...\n"

        # Instructions
        prompt += f"\n## Instructions\n"
        prompt += "Generate a comment that:\n"
        prompt += "1. Matches the user's communication style and tone\n"
        prompt += "2. Is relevant and adds value to the conversation\n"
        prompt += "3. Feels authentic and natural\n"
        prompt += "4. Is appropriate for the platform and context\n"
        
        if user.ai_profile and user.ai_profile.vibe_profile_json:
            vibe_profile = user.ai_profile.vibe_profile_json
            tone = vibe_profile.get('tone', 'neutral')
            verbosity = vibe_profile.get('verbosity', 'moderate')
            emoji_usage = vibe_profile.get('emoji_usage', 'light')
            
            if tone == 'casual':
                prompt += "5. Use a casual, conversational tone\n"
            elif tone == 'formal':
                prompt += "5. Use a formal, professional tone\n"
            elif tone == 'enthusiastic':
                prompt += "5. Show enthusiasm and energy\n"
                
            if verbosity == 'brief':
                prompt += "6. Keep the comment concise and to the point\n"
            elif verbosity == 'verbose':
                prompt += "6. Provide detailed thoughts and explanations\n"
                
            if emoji_usage == 'heavy':
                prompt += "7. Use emojis liberally to express emotions\n"
            elif emoji_usage == 'light':
                prompt += "7. Use emojis sparingly but appropriately\n"
            elif emoji_usage == 'none':
                prompt += "7. Avoid using emojis\n"

        prompt += "\nGenerate only the comment text, nothing else:"
        
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