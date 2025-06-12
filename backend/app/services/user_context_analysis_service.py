"""Service for analyzing user's Telegram activity to build personalized AI context."""

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.models.ai_profile import AnalysisStatus
from app.services.base_service import BaseService
from app.services.gemini_service import GeminiService
from app.services.telegram_service import TelegramService
from app.repositories.user_repository import UserRepository


class UserContextAnalysisService(BaseService):
    """Service for analyzing user's Telegram data to create personalized AI context."""

    def __init__(
        self,
        user_repository: UserRepository,
        telegram_service: TelegramService,
        gemini_service: GeminiService,
    ):
        super().__init__()
        self.user_repository = user_repository
        self.telegram_service = telegram_service
        self.gemini_service = gemini_service

    async def analyze_user_context(self, client: Any, user_id: str) -> Dict[str, Any]:
        """Analyzes user's Telegram activity to build their vibe profile using an LLM.

        This is the main orchestration method for vibe profile generation.

        Args:
            client: TelegramClient instance
            user_id: User ID

        Returns:
            Dict with analysis results and status
        """
        # Import here to avoid circular imports
        from app.services.dependencies import container
        from app.repositories.ai_profile_repository import AIProfileRepository

        ai_profile_repo = container.resolve(AIProfileRepository)

        ai_profile = None
        try:
            ai_profile = await ai_profile_repo.get_ai_profile_by_user(user_id)
            if not ai_profile:
                ai_profile = await ai_profile_repo.create_ai_profile(user_id=user_id)

            await ai_profile_repo.update_ai_profile(
                ai_profile.id,
                analysis_status=AnalysisStatus.ANALYZING,
                ai_model_used="gemini-pro",
            )
            self.logger.info(f"Starting vibe profile analysis for user {user_id}")

            # Step 1: Fetch user's own sent messages for style analysis
            user_sent_messages = await self.telethon_service.get_user_sent_messages(
                client, limit=200
            )

            if not user_sent_messages or len(user_sent_messages) < 20:
                self.logger.warning(
                    f"Insufficient data for user {user_id} for analysis."
                )
                await ai_profile_repo.update_ai_profile(
                    ai_profile.id,
                    analysis_status=AnalysisStatus.FAILED,
                    last_error_message="Insufficient data for analysis",
                )
                return {"status": "failed", "reason": "Insufficient data for analysis"}

            # Step 2: Use LLM to generate the entire vibe profile from messages
            vibe_profile = await self._create_vibe_from_messages_llm(
                user_sent_messages
            )

            if not vibe_profile:
                self.logger.error(f"LLM analysis failed for user {user_id}")
                await ai_profile_repo.update_ai_profile(
                    ai_profile.id,
                    analysis_status=AnalysisStatus.FAILED,
                    last_error_message="LLM analysis failed",
                )
                return {"status": "failed", "reason": "LLM analysis failed"}

            # Step 3: Update AI profile with the generated vibe profile
            await ai_profile_repo.update_ai_profile(
                ai_profile.id,
                vibe_profile_json=vibe_profile,
                analysis_status=AnalysisStatus.COMPLETED,
                messages_analyzed_count=str(len(user_sent_messages)),
                last_analyzed_at=datetime.utcnow(),
            )

            self.logger.info(f"Vibe profile analysis completed for user {user_id}")

            return {
                "status": "completed",
                "vibe_profile": vibe_profile,
                "messages_analyzed": len(user_sent_messages),
            }

        except Exception as e:
            self.logger.error(f"Error analyzing user vibe profile: {e}", exc_info=True)
            if "ai_profile_repo" in locals() and ai_profile:
                await ai_profile_repo.update_ai_profile(
                    ai_profile.id,
                    analysis_status=AnalysisStatus.FAILED,
                    last_error_message=str(e),
                )
            return {"status": "failed", "reason": str(e)}

    async def _create_vibe_from_messages_llm(
        self, messages: List[Dict]
    ) -> Optional[Dict[str, Any]]:
        """Uses an LLM to analyze messages and create a structured Vibe Profile."""
        if not self.gemini_service:
            self.logger.error(
                "Gemini service is not available for vibe profile generation."
            )
            return None

        try:
            # Prepare a sample of messages for the prompt
            message_texts = [msg.get("text", "") for msg in messages if msg.get("text")]
            combined_text_sample = "\n".join(message_texts)

            # Ensure the sample is not too large for the prompt
            if len(combined_text_sample) > 15000:  # Limit to ~15k chars
                combined_text_sample = combined_text_sample[:15000]

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

            response = await self.gemini_service.generate_content(prompt)

            if response and response.get("success") and response.get("content"):
                content = response.get("content")
                # Clean up the response to get only the JSON part
                json_match = re.search(r"\{.*\}", content, re.DOTALL)
                if json_match:
                    json_string = json_match.group(0)
                    vibe_profile = json.loads(json_string)
                    self.logger.info(
                        f"Successfully generated vibe profile via LLM: {vibe_profile}"
                    )
                    return vibe_profile
                else:
                    self.logger.error(
                        f"LLM did not return a valid JSON object. Response: {content}"
                    )
                    return None
            else:
                self.logger.error(
                    f"LLM generation failed or returned empty content. Response: {response}"
                )
                return None

        except Exception as e:
            self.logger.error(
                f"Error during LLM vibe profile generation: {e}", exc_info=True
            )
            return None 