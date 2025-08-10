import logging
from typing import List, Optional

from app.models.draft_comment import DraftComment, DraftStatus
from app.repositories.draft_comment_repository import DraftCommentRepository
from app.repositories.negative_feedback_repository import NegativeFeedbackRepository
from app.schemas.draft_comment import (
    DraftCommentCreate,
    DraftCommentResponse,
    DraftCommentUpdate,
)
from app.services.base_service import BaseService

logger = logging.getLogger(__name__)


class DraftService(BaseService):
    """Service for managing draft comments."""

    def __init__(
        self,
        draft_repo: DraftCommentRepository,
        feedback_repo: NegativeFeedbackRepository,
    ):
        super().__init__()
        self.draft_repo = draft_repo
        self.feedback_repo = feedback_repo

    async def create_draft(self, draft_data: DraftCommentCreate) -> Optional[DraftCommentResponse]:
        draft = await self.draft_repo.create_draft_comment(**draft_data.model_dump())
        return DraftCommentResponse.from_orm(draft) if draft else None

    async def get_user_drafts(self, user_id: str, status: Optional[DraftStatus] = None) -> List[DraftCommentResponse]:
        drafts = await self.draft_repo.get_drafts_by_user(user_id, status)
        return [DraftCommentResponse.from_orm(d) for d in drafts]

    async def update_draft(self, draft_id: str, update_data: DraftCommentUpdate) -> Optional[DraftCommentResponse]:
        draft = await self.draft_repo.update_draft_comment(draft_id, **update_data.model_dump(exclude_unset=True))
        return DraftCommentResponse.from_orm(draft) if draft else None

    async def approve_draft(self, draft_id: str) -> Optional[DraftCommentResponse]:
        return await self.update_draft(draft_id, DraftCommentUpdate(status=DraftStatus.APPROVED)) 