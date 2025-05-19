"""Repository for AI request management operations."""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from models.ai.ai_request import AIRequest
from services.base.base_repository import BaseRepository


class AIRequestRepository(BaseRepository):
    """Repository class for AI request management."""

    async def create_request(self, **request_data) -> Optional[AIRequest]:
        """Create a new AI request."""
        async with self.get_session() as session:
            try:
                self.logger.info("Creating AI request with data: %s", request_data)
                request = AIRequest(**request_data)

                session.add(request)
                await session.commit()
                await session.refresh(request)

                self.logger.info(
                    "AI request created successfully with id: %s", request.id
                )
                return request
            except SQLAlchemyError as e:
                await session.rollback()
                self.logger.error(
                    "Error creating AI request: %s", str(e), exc_info=True
                )
                raise

    async def get_request(self, request_id: str) -> Optional[AIRequest]:
        """Get AI request by ID."""
        async with self.get_session() as session:
            try:
                query = select(AIRequest).where(AIRequest.id == request_id)
                result = await session.execute(query)
                request = result.unique().scalar_one_or_none()
                if not request:
                    self.logger.info("AI request not found with id: %s", request_id)
                return request
            except SQLAlchemyError as e:
                self.logger.error("Error getting AI request: %s", str(e), exc_info=True)
                raise

    async def get_requests_by_dialog_id(self, dialog_id: str) -> List[AIRequest]:
        """Get all AI requests by dialog ID."""
        async with self.get_session() as session:
            try:
                query = select(AIRequest).where(AIRequest.dialog_id == dialog_id)
                result = await session.execute(query)
                requests = result.unique().scalars().all()
                return list(requests)
            except SQLAlchemyError as e:
                self.logger.error(
                    "Error getting AI requests: %s", str(e), exc_info=True
                )
                raise

    async def get_requests_by_user_id(self, user_id: str) -> List[AIRequest]:
        """Get all AI requests by user ID."""
        async with self.get_session() as session:
            try:
                query = select(AIRequest).where(AIRequest.user_id == user_id)
                result = await session.execute(query)
                requests = result.unique().scalars().all()
                return list(requests)
            except SQLAlchemyError as e:
                self.logger.error(
                    "Error getting AI requests: %s", str(e), exc_info=True
                )
                raise

    async def update_request(
        self, request_id: str, **update_data
    ) -> Optional[AIRequest]:
        """Update AI request data."""
        async with self.get_session() as session:
            try:
                query = select(AIRequest).where(AIRequest.id == request_id)
                result = await session.execute(query)
                request = result.unique().scalar_one_or_none()

                if request:
                    for key, value in update_data.items():
                        setattr(request, key, value)
                    await session.commit()
                    await session.refresh(request)
                    self.logger.info("AI request updated successfully: %s", request_id)
                else:
                    self.logger.info("AI request not found with id: %s", request_id)

                return request
            except SQLAlchemyError as e:
                await session.rollback()
                self.logger.error(
                    "Error updating AI request: %s", str(e), exc_info=True
                )
                raise
