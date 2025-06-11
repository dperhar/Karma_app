"""Repository for managing AI profile operations."""

import logging
from typing import Optional
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.models.ai_profile import AIProfile, AnalysisStatus
from app.services.base_repository import BaseRepository


class AIProfileRepository(BaseRepository):
    """Repository for AI profile operations."""

    async def create_ai_profile(self, user_id: str, **kwargs) -> Optional[AIProfile]:
        """Create a new AI profile for a user."""
        async with self.get_session() as session:
            try:
                self.logger.info("Creating AI profile for user: %s", user_id)
                ai_profile = AIProfile(
                    user_id=user_id,
                    analysis_status=AnalysisStatus.PENDING,
                    **kwargs
                )

                session.add(ai_profile)
                await session.commit()
                await session.refresh(ai_profile)

                self.logger.info("AI profile created successfully with id: %s", ai_profile.id)
                return ai_profile
            except SQLAlchemyError as e:
                await session.rollback()
                self.logger.error("Error creating AI profile: %s", str(e), exc_info=True)
                raise

    async def get_ai_profile_by_user(self, user_id: str) -> Optional[AIProfile]:
        """Get AI profile by user ID."""
        async with self.get_session() as session:
            try:
                query = select(AIProfile).where(AIProfile.user_id == user_id)
                result = await session.execute(query)
                ai_profile = result.unique().scalar_one_or_none()
                if not ai_profile:
                    self.logger.info("AI profile not found for user: %s", user_id)
                return ai_profile
            except SQLAlchemyError as e:
                self.logger.error("Error getting AI profile by user %s: %s", user_id, str(e), exc_info=True)
                raise

    async def get_ai_profile(self, profile_id: str) -> Optional[AIProfile]:
        """Get AI profile by ID."""
        async with self.get_session() as session:
            try:
                query = select(AIProfile).where(AIProfile.id == profile_id)
                result = await session.execute(query)
                ai_profile = result.unique().scalar_one_or_none()
                if not ai_profile:
                    self.logger.info("AI profile not found with id: %s", profile_id)
                return ai_profile
            except SQLAlchemyError as e:
                self.logger.error("Error getting AI profile: %s", str(e), exc_info=True)
                raise

    async def update_ai_profile(self, profile_id: str, **update_data) -> Optional[AIProfile]:
        """Update AI profile data."""
        async with self.get_session() as session:
            try:
                query = select(AIProfile).where(AIProfile.id == profile_id)
                result = await session.execute(query)
                ai_profile = result.unique().scalar_one_or_none()

                if ai_profile:
                    for key, value in update_data.items():
                        setattr(ai_profile, key, value)
                    await session.commit()
                    await session.refresh(ai_profile)
                    self.logger.info("AI profile updated successfully: %s", profile_id)
                else:
                    self.logger.info("AI profile not found with id: %s", profile_id)

                return ai_profile
            except SQLAlchemyError as e:
                await session.rollback()
                self.logger.error("Error updating AI profile: %s", str(e), exc_info=True)
                raise

    async def delete_ai_profile(self, profile_id: str) -> bool:
        """Delete an AI profile."""
        async with self.get_session() as session:
            try:
                query = select(AIProfile).where(AIProfile.id == profile_id)
                result = await session.execute(query)
                ai_profile = result.unique().scalar_one_or_none()
                
                if ai_profile:
                    await session.delete(ai_profile)
                    await session.commit()
                    self.logger.info("AI profile deleted successfully: %s", profile_id)
                    return True
                else:
                    self.logger.info("AI profile not found with id: %s", profile_id)
                    return False
                    
            except SQLAlchemyError as e:
                await session.rollback()
                self.logger.error("Error deleting AI profile %s: %s", profile_id, str(e), exc_info=True)
                raise

    async def mark_analysis_started(self, profile_id: str, ai_model: str = "gemini-pro") -> Optional[AIProfile]:
        """Mark analysis as started."""
        return await self.update_ai_profile(
            profile_id,
            analysis_status=AnalysisStatus.ANALYZING,
            ai_model_used=ai_model
        )

    async def mark_analysis_completed(
        self, 
        profile_id: str, 
        vibe_profile: dict, 
        messages_count: int = 0
    ) -> Optional[AIProfile]:
        """Mark analysis as completed with results."""
        return await self.update_ai_profile(
            profile_id,
            analysis_status=AnalysisStatus.COMPLETED,
            vibe_profile_json=vibe_profile,
            last_analyzed_at=datetime.utcnow(),
            messages_analyzed_count=str(messages_count)
        )

    async def mark_analysis_failed(self, profile_id: str, error_message: str) -> Optional[AIProfile]:
        """Mark analysis as failed with error message."""
        return await self.update_ai_profile(
            profile_id,
            analysis_status=AnalysisStatus.FAILED,
            last_error_message=error_message
        ) 