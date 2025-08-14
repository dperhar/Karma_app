"""Repository for managing negative feedback operations."""

import logging
from typing import List, Optional

from sqlalchemy import select, desc, func
from sqlalchemy.exc import SQLAlchemyError

from app.models.negative_feedback import NegativeFeedback
from app.services.base_repository import BaseRepository


class NegativeFeedbackRepository(BaseRepository):
    """Repository for negative feedback operations."""

    async def create_negative_feedback(
        self,
        user_id: str,
        rejected_comment_text: str,
        original_post_content: Optional[str] = None,
        original_post_url: Optional[str] = None,
        rejection_reason: Optional[str] = None,
        ai_model_used: Optional[str] = None,
        draft_comment_id: Optional[str] = None,
    ) -> Optional[NegativeFeedback]:
        """Create a new negative feedback entry."""
        async with self.get_session() as session:
            try:
                self.logger.info("Creating negative feedback for user: %s", user_id)
                feedback = NegativeFeedback(
                    user_id=user_id,
                    rejected_comment_text=rejected_comment_text,
                    original_post_content=original_post_content,
                    original_post_url=original_post_url,
                    rejection_reason=rejection_reason,
                    ai_model_used=ai_model_used,
                    draft_comment_id=draft_comment_id,
                )

                session.add(feedback)
                await session.commit()
                await session.refresh(feedback)

                self.logger.info("Negative feedback created successfully with id: %s", feedback.id)
                return feedback
            except SQLAlchemyError as e:
                await session.rollback()
                self.logger.error("Error creating negative feedback: %s", str(e), exc_info=True)
                raise

    async def get_negative_feedback_by_user(
        self, 
        user_id: str,
        limit: int = 20
    ) -> List[NegativeFeedback]:
        """Get negative feedback entries for a user, ordered by most recent."""
        async with self.get_session() as session:
            try:
                query = (
                    select(NegativeFeedback)
                    .where(NegativeFeedback.user_id == user_id)
                    .order_by(desc(NegativeFeedback.created_at))
                    .limit(limit)
                )
                
                result = await session.execute(query)
                return list(result.unique().scalars().all())
                
            except SQLAlchemyError as e:
                self.logger.error("Error getting negative feedback for user %s: %s", user_id, str(e), exc_info=True)
                raise

    async def get_negative_feedback_by_draft(
        self, 
        draft_comment_id: str
    ) -> List[NegativeFeedback]:
        """Get negative feedback entries for a specific draft comment."""
        async with self.get_session() as session:
            try:
                query = (
                    select(NegativeFeedback)
                    .where(NegativeFeedback.draft_comment_id == draft_comment_id)
                    .order_by(desc(NegativeFeedback.created_at))
                )
                
                result = await session.execute(query)
                return list(result.unique().scalars().all())
                
            except SQLAlchemyError as e:
                self.logger.error("Error getting negative feedback for draft %s: %s", draft_comment_id, str(e), exc_info=True)
                raise

    async def count_negative_feedback_by_user(self, user_id: str) -> int:
        """Count total negative feedback entries for a user."""
        async with self.get_session() as session:
            try:
                query = select(func.count(NegativeFeedback.id)).where(NegativeFeedback.user_id == user_id)
                result = await session.execute(query)
                return result.scalar() or 0
                
            except SQLAlchemyError as e:
                self.logger.error("Error counting negative feedback for user %s: %s", user_id, str(e), exc_info=True)
                raise

    async def delete_negative_feedback(self, feedback_id: str) -> bool:
        """Delete a negative feedback entry."""
        async with self.get_session() as session:
            try:
                query = select(NegativeFeedback).where(NegativeFeedback.id == feedback_id)
                result = await session.execute(query)
                feedback = result.unique().scalar_one_or_none()
                
                if feedback:
                    await session.delete(feedback)
                    await session.commit()
                    self.logger.info("Negative feedback deleted successfully: %s", feedback_id)
                    return True
                else:
                    self.logger.info("Negative feedback not found with id: %s", feedback_id)
                    return False
                    
            except SQLAlchemyError as e:
                await session.rollback()
                self.logger.error("Error deleting negative feedback %s: %s", feedback_id, str(e), exc_info=True)
                raise 

    async def delete_all_for_user(self, user_id: str) -> int:
        """Delete all negative feedback rows for a user. Returns number deleted."""
        from sqlalchemy import delete
        async with self.get_session() as session:
            try:
                stmt = delete(NegativeFeedback).where(NegativeFeedback.user_id == user_id)
                result = await session.execute(stmt)
                await session.commit()
                return int(getattr(result, "rowcount", 0) or 0)
            except SQLAlchemyError as e:
                await session.rollback()
                self.logger.error("Error deleting negative feedback for user %s: %s", user_id, str(e), exc_info=True)
                raise