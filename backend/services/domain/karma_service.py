"""Service for AI-powered comment generation and management."""

import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from models.ai.draft_comment import DraftComment, DraftStatus
from models.ai.ai_request import AIRequestModel
from models.user.user import User
from schemas.draft_comment import DraftCommentCreate, DraftCommentUpdate, DraftCommentResponse
from services.base.base_service import BaseService
from services.external.gemini_service import GeminiService
from services.external.langchain_service import LangChainService
from services.external.telethon_service import TelethonService
from services.repositories.draft_comment_repository import DraftCommentRepository
from services.repositories.user_repository import UserRepository
from services.websocket_service import WebSocketService


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
                persona_name=user.persona_name or "Default User",
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
            self.logger.error(f"Error getting drafts for user: {e}", exc_info=True)
            return []

    def _is_post_relevant(self, post_data: Dict[str, Any], user: User) -> bool:
        """Check if post is relevant to user's persona interests."""
        if not user.persona_interests_json:
            return True  # If no interests specified, consider all posts relevant

        try:
            interests = json.loads(user.persona_interests_json) if isinstance(user.persona_interests_json, str) else user.persona_interests_json
            if not interests:
                return True

            post_text = post_data.get('text', '').lower()
            channel_title = post_data.get('channel', {}).get('title', '').lower()
            combined_text = post_text + ' ' + channel_title
            
            # Check for direct keyword matches
            for interest in interests:
                if isinstance(interest, str) and interest.lower() in combined_text:
                    return True
            
            # Check for related technology terms if user is interested in technology
            tech_interests = ['technology', 'artificial intelligence', 'programming', 'ai', 'machine learning']
            user_has_tech_interests = any(interest.lower() in [ti.lower() for ti in tech_interests] for interest in interests if isinstance(interest, str))
            
            if user_has_tech_interests:
                tech_keywords = [
                    'ai', 'artificial intelligence', 'machine learning', 'ml', 'deep learning',
                    'neural network', 'algorithm', 'programming', 'code', 'coding', 'software',
                    'tech', 'technology', 'computer', 'digital', 'innovation', 'startup',
                    'openai', 'gpt', 'llm', 'model', 'training', 'data science', 'python',
                    'development', 'breakthrough', 'advancement', 'computing', 'processor'
                ]
                
                for keyword in tech_keywords:
                    if keyword in combined_text:
                        return True
            
            # Check for business-related terms if user is interested in business/startups
            business_interests = ['business', 'startup', 'startups', 'entrepreneur', 'finance', 'investment']
            user_has_business_interests = any(interest.lower() in [bi.lower() for bi in business_interests] for interest in interests if isinstance(interest, str))
            
            if user_has_business_interests:
                business_keywords = [
                    'business', 'startup', 'company', 'entrepreneur', 'investment', 'funding',
                    'venture', 'market', 'industry', 'revenue', 'growth', 'scale', 'enterprise'
                ]
                
                for keyword in business_keywords:
                    if keyword in combined_text:
                        return True

            return False

        except Exception as e:
            self.logger.error(f"Error checking post relevance: {e}")
            return True  # Default to relevant if check fails

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
        """Construct AI prompt for comment generation using user's personalized context."""
        # Use user's system prompt if available, otherwise fallback
        if user.user_system_prompt:
            system_context = user.user_system_prompt
        else:
            # Fallback for users without analyzed context
            persona_name = user.persona_name or "a tech enthusiast"
            interests = []
            if user.persona_interests_json:
                try:
                    interests = json.loads(user.persona_interests_json) if isinstance(user.persona_interests_json, str) else user.persona_interests_json
                except:
                    interests = []  # Ensure interests is a list
            system_context = f"You are {persona_name}, knowledgeable about {', '.join(str(i) for i in interests[:5]) if interests else 'technology and innovation'}."
        
        # Use user's communication style if available
        style_instruction = ""
        if user.persona_style_description:
            style_instruction = f"\nYour communication style: {user.persona_style_description}"
        else:
            style_instruction = "\nYour communication style: concise and insightful"

        post_text = post_data.get('text', '')
        channel_name = post_data.get('channel', {}).get('title', 'a channel')
        
        # Enhanced prompt using user's digital twin data
        prompt = f"""{system_context}

You are writing a comment on a Telegram post.{style_instruction}

Original post from {channel_name}:
"{post_text}"

Write a thoughtful comment that:
1. Reflects your knowledge and perspective based on your interests
2. Matches your natural communication style
3. Adds value to the conversation
4. Is appropriate for a public Telegram channel
5. Is 1-3 sentences long
6. Sounds authentic to how you typically write

Comment:"""

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