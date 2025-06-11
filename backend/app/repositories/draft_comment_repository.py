"""Repository for draft comment management operations."""

from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.models.draft_comment import DraftComment, DraftStatus
from app.services.base_repository import BaseRepository


class DraftCommentRepository(BaseRepository):
    """Repository class for draft comment management."""

    async def create_draft_comment(self, **draft_data) -> Optional[DraftComment]:
        """Create a new draft comment."""
        async with self.get_session() as session:
            try:
                self.logger.info("Creating draft comment with data: %s", draft_data)
                draft = DraftComment(**draft_data)

                session.add(draft)
                await session.commit()
                await session.refresh(draft)

                self.logger.info("Draft comment created successfully with id: %s", draft.id)
                return draft
            except SQLAlchemyError as e:
                await session.rollback()
                self.logger.error("Error creating draft comment: %s", str(e), exc_info=True)
                raise

    async def get_draft_comment(self, draft_id: str) -> Optional[DraftComment]:
        """Get draft comment by ID."""
        async with self.get_session() as session:
            try:
                query = select(DraftComment).where(DraftComment.id == draft_id)
                result = await session.execute(query)
                draft = result.unique().scalar_one_or_none()
                if not draft:
                    self.logger.info("Draft comment not found with id: %s", draft_id)
                return draft
            except SQLAlchemyError as e:
                self.logger.error("Error getting draft comment: %s", str(e), exc_info=True)
                raise

    async def update_draft_comment(self, draft_id: str, **update_data) -> Optional[DraftComment]:
        """Update draft comment data."""
        async with self.get_session() as session:
            try:
                query = select(DraftComment).where(DraftComment.id == draft_id)
                result = await session.execute(query)
                draft = result.unique().scalar_one_or_none()

                if draft:
                    for key, value in update_data.items():
                        setattr(draft, key, value)
                    await session.commit()
                    await session.refresh(draft)
                    self.logger.info("Draft comment updated successfully: %s", draft_id)
                else:
                    self.logger.info("Draft comment not found with id: %s", draft_id)

                return draft
            except SQLAlchemyError as e:
                await session.rollback()
                self.logger.error("Error updating draft comment: %s", str(e), exc_info=True)
                raise

    async def get_drafts_by_message(self, original_message_id: str) -> List[DraftComment]:
        """Get all draft comments for a specific message."""
        async with self.get_session() as session:
            try:
                query = select(DraftComment).where(DraftComment.original_message_id == original_message_id)
                result = await session.execute(query)
                drafts = result.unique().scalars().all()
                return list(drafts)
            except SQLAlchemyError as e:
                self.logger.error("Error getting draft comments by message: %s", str(e), exc_info=True)
                raise

    async def get_drafts_by_user(self, user_id: str, status: Optional[DraftStatus] = None) -> List[DraftComment]:
        """Get all draft comments for a user, optionally filtered by status."""
        async with self.get_session() as session:
            try:
                query = select(DraftComment).where(DraftComment.user_id == user_id)
                if status:
                    query = query.where(DraftComment.status == status)
                result = await session.execute(query)
                drafts = result.unique().scalars().all()
                return list(drafts)
            except SQLAlchemyError as e:
                self.logger.error("Error getting draft comments by user: %s", str(e), exc_info=True)
                raise

    async def get_pending_drafts(self, user_id: str) -> List[DraftComment]:
        """Get all pending drafts (DRAFT, EDITED, APPROVED) for a user."""
        async with self.get_session() as session:
            try:
                query = select(DraftComment).where(
                    DraftComment.user_id == user_id,
                    DraftComment.status.in_([DraftStatus.DRAFT, DraftStatus.EDITED, DraftStatus.APPROVED])
                )
                result = await session.execute(query)
                drafts = result.unique().scalars().all()
                return list(drafts)
            except SQLAlchemyError as e:
                self.logger.error("Error getting pending drafts: %s", str(e), exc_info=True)
                raise 