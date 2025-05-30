"""Repository for AI dialog management operations."""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from models.ai.ai_dialog import AIDialog
from services.base.base_repository import BaseRepository


class AIDialogRepository(BaseRepository):
    """Repository class for AI dialog management."""

    async def create_dialog(self, **dialog_data) -> Optional[AIDialog]:
        """Create a new AI dialog."""
        async with self.get_session() as session:
            try:
                self.logger.info("Creating AI dialog with data: %s", dialog_data)
                dialog = AIDialog(**dialog_data)

                session.add(dialog)
                await session.commit()
                await session.refresh(dialog)

                self.logger.info(
                    "AI dialog created successfully with id: %s", dialog.id
                )
                return dialog
            except SQLAlchemyError as e:
                await session.rollback()
                self.logger.error("Error creating AI dialog: %s", str(e), exc_info=True)
                raise

    async def get_dialog(self, dialog_id: str) -> Optional[AIDialog]:
        """Get AI dialog by ID."""
        async with self.get_session() as session:
            try:
                query = select(AIDialog).where(AIDialog.id == dialog_id)
                result = await session.execute(query)
                dialog = result.unique().scalar_one_or_none()
                if not dialog:
                    self.logger.info("AI dialog not found with id: %s", dialog_id)
                return dialog
            except SQLAlchemyError as e:
                self.logger.error("Error getting AI dialog: %s", str(e), exc_info=True)
                raise

    async def get_dialogs_by_chat_id(self, chat_id: str) -> List[AIDialog]:
        """Get all AI dialogs by chat ID."""
        async with self.get_session() as session:
            try:
                query = select(AIDialog).where(AIDialog.chat_id == chat_id)
                result = await session.execute(query)
                dialogs = result.unique().scalars().all()
                return list(dialogs)
            except SQLAlchemyError as e:
                self.logger.error("Error getting AI dialogs: %s", str(e), exc_info=True)
                raise

    async def get_dialogs_by_user_id(self, user_id: str) -> List[AIDialog]:
        """Get all AI dialogs by user ID."""
        async with self.get_session() as session:
            try:
                query = select(AIDialog).where(AIDialog.user_id == user_id)
                result = await session.execute(query)
                dialogs = result.unique().scalars().all()
                return list(dialogs)
            except SQLAlchemyError as e:
                self.logger.error("Error getting AI dialogs: %s", str(e), exc_info=True)
                raise

    async def update_dialog(self, dialog_id: str, **update_data) -> Optional[AIDialog]:
        """Update AI dialog data."""
        async with self.get_session() as session:
            try:
                query = select(AIDialog).where(AIDialog.id == dialog_id)
                result = await session.execute(query)
                dialog = result.unique().scalar_one_or_none()

                if dialog:
                    for key, value in update_data.items():
                        setattr(dialog, key, value)
                    await session.commit()
                    await session.refresh(dialog)
                    self.logger.info("AI dialog updated successfully: %s", dialog_id)
                else:
                    self.logger.info("AI dialog not found with id: %s", dialog_id)

                return dialog
            except SQLAlchemyError as e:
                await session.rollback()
                self.logger.error("Error updating AI dialog: %s", str(e), exc_info=True)
                raise

    async def get_all_dialogs(self) -> List[AIDialog]:
        """Get all AI dialogs."""
        async with self.get_session() as session:
            try:
                query = select(AIDialog)
                result = await session.execute(query)
                dialogs = result.unique().scalars().all()
                return list(dialogs)
            except SQLAlchemyError as e:
                self.logger.error("Error getting AI dialogs: %s", str(e), exc_info=True)
                raise
